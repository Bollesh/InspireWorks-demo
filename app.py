"""Flask app: outbound-call trigger, simple UI, and the Plivo IVR webhooks."""
import logging

import plivo
from flask import Flask, Response, abort, jsonify, render_template, request

import calls
import config
import ivr

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ivr")

IVR_METHODS = ["GET", "POST"]


def base_url():
    return config.PUBLIC_BASE_URL or request.url_root.rstrip("/")


def xml(body):
    return Response(body, mimetype="application/xml")


def param(name, default=""):
    return request.values.get(name, default)


def log_step(step, **extra):
    fields = " ".join(f"{k}={v}" for k, v in extra.items())
    log.info("call=%s step=%s %s", param("CallUUID", "-"), step, fields)


@app.before_request
def check_plivo_signature():
    """Reject spoofed webhooks when VALIDATE_SIGNATURE=true."""
    if not config.VALIDATE_SIGNATURE or request.endpoint in (None, "index", "make_call", "static"):
        return
    # Plivo signs the public URL it called, not the localhost URL Flask sees behind ngrok.
    uri = base_url() + request.full_path.rstrip("?")
    valid = plivo.utils.validate_v3_signature(
        request.method,
        uri,
        request.headers.get("X-Plivo-Signature-V3-Nonce", ""),
        config.PLIVO_AUTH_TOKEN,
        request.headers.get("X-Plivo-Signature-V3", ""),
        request.form.to_dict() if request.method == "POST" else None,
    )
    if not valid:
        log.warning("Rejected request with invalid Plivo signature: %s", uri)
        abort(403)


# --- Outbound trigger ---------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html", default_to=config.DEFAULT_TO_NUMBER, from_number=config.PLIVO_FROM_NUMBER)


@app.post("/call")
def make_call():
    data = request.get_json(silent=True) or request.form
    to_number = (data.get("to") or config.DEFAULT_TO_NUMBER).strip()
    if not config.is_e164(to_number):
        return jsonify(error="Enter the number in E.164 format, e.g. +919876543210"), 400
    if not (config.PLIVO_AUTH_ID and config.PLIVO_AUTH_TOKEN and config.PUBLIC_BASE_URL):
        return jsonify(error="Set PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN and PUBLIC_BASE_URL in .env"), 500

    try:
        resp = calls.place_call(to_number)
    except plivo.exceptions.PlivoRestError as e:
        log.error("Plivo call failed: %s", e)
        return jsonify(error=str(e)), 502
    log.info("Outbound call requested to %s: %s", to_number, resp)
    return jsonify(message=resp["message"], request_uuid=resp["request_uuid"])


# --- IVR webhooks -------------------------------------------------------------

@app.route("/answer", methods=IVR_METHODS)
def answer():
    log_step("answer", frm=param("From"), to=param("To"))
    return xml(ivr.answer(base_url()))


@app.route("/otp", methods=IVR_METHODS)
def otp():
    log_step("otp-prompt")
    return xml(ivr.otp_prompt(base_url()))


@app.route("/verify-otp", methods=IVR_METHODS)
def verify_otp():
    digits = param("Digits")
    ok = digits == config.OTP_CODE
    log_step("verify-otp", result="ok" if ok else "wrong", entered=len(digits))
    return xml(ivr.otp_result(base_url(), digits, config.OTP_CODE))


@app.route("/language", methods=IVR_METHODS)
def language():
    log_step("language-prompt")
    return xml(ivr.language_prompt(base_url()))


@app.route("/language-select", methods=IVR_METHODS)
def language_select():
    log_step("language-select", digits=param("Digits"))
    return xml(ivr.language_result(base_url(), param("Digits")))


@app.route("/menu", methods=IVR_METHODS)
def menu():
    log_step("menu-prompt", lang=request.args.get("lang"))
    return xml(ivr.menu_prompt(base_url(), request.args.get("lang")))


@app.route("/menu-select", methods=IVR_METHODS)
def menu_select():
    lang = request.args.get("lang")
    log_step("menu-select", lang=lang, digits=param("Digits"))
    return xml(ivr.menu_result(
        base_url(), lang, param("Digits"),
        audio_url=config.AUDIO_URL,
        associate_number=config.ASSOCIATE_NUMBER,
        caller_id=config.PLIVO_FROM_NUMBER,
    ))


@app.route("/dial-status", methods=IVR_METHODS)
def dial_status():
    lang = request.args.get("lang")
    log_step("dial-status", lang=lang, status=param("DialStatus"))
    return xml(ivr.dial_status(base_url(), lang, param("DialStatus")))


@app.route("/hangup", methods=IVR_METHODS)
def hangup():
    log_step("hangup", cause=param("HangupCause"), duration=param("Duration"))
    return "", 204


if __name__ == "__main__":
    # Reload on .env edits too, so a new ngrok URL takes effect without a manual restart.
    app.run(host="0.0.0.0", port=5000, debug=True, extra_files=[".env"])
