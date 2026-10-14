"""Pure functions that build the Plivo XML for each step of the IVR.

Every function takes `base` (the public URL of this app, no trailing slash) so
the action/redirect URLs it emits are absolute. Nothing here talks to Plivo or
Flask, which keeps the call flow unit-testable.
"""
from plivo import plivoxml

from prompts import normalize_lang, t, voice


def _dtmf_input(action, num_digits, log=True):
    return plivoxml.GetInputElement(
        action=action,
        method="POST",
        input_type="dtmf",
        num_digits=num_digits,
        execution_timeout=15,
        digit_end_timeout=5,
        finish_on_key="#",
        redirect=True,
        log=log,
    )


def _say(response, lang, key):
    response.add_speak(t(lang, key), language=voice(lang))


# --- Entry point -------------------------------------------------------------

def answer(base):
    """Greet the caller once, then hand off to the OTP prompt."""
    r = plivoxml.ResponseElement()
    _say(r, "en", "greeting")
    r.add_redirect(f"{base}/otp", method="POST")
    return r.to_string()


# --- Level 0: OTP ------------------------------------------------------------

def otp_prompt(base):
    r = plivoxml.ResponseElement()
    gi = _dtmf_input(f"{base}/verify-otp", num_digits=4, log=False)
    gi.add_speak(t("en", "otp"), language=voice("en"))
    r.add(gi)
    _say(r, "en", "no_input")
    r.add_redirect(f"{base}/otp", method="POST")
    return r.to_string()


def otp_result(base, digits, expected):
    r = plivoxml.ResponseElement()
    if digits == expected:
        _say(r, "en", "otp_ok")
        r.add_redirect(f"{base}/language", method="POST")
    else:
        _say(r, "en", "otp_wrong" if digits else "no_input")
        r.add_redirect(f"{base}/otp", method="POST")
    return r.to_string()


# --- Level 1: language -------------------------------------------------------

def language_prompt(base):
    r = plivoxml.ResponseElement()
    gi = _dtmf_input(f"{base}/language-select", num_digits=1)
    gi.add_speak(t("en", "language"), language=voice("en"))
    gi.add_speak(t("es", "language"), language=voice("es"))
    r.add(gi)
    _say(r, "en", "no_input")
    r.add_redirect(f"{base}/language", method="POST")
    return r.to_string()


def language_result(base, digits):
    r = plivoxml.ResponseElement()
    lang = {"1": "en", "2": "es"}.get(digits)
    if lang:
        r.add_redirect(f"{base}/menu?lang={lang}", method="POST")
    else:
        _say(r, "en", "invalid")
        r.add_redirect(f"{base}/language", method="POST")
    return r.to_string()


# --- Level 2: action menu ----------------------------------------------------

def menu_prompt(base, lang):
    lang = normalize_lang(lang)
    r = plivoxml.ResponseElement()
    gi = _dtmf_input(f"{base}/menu-select?lang={lang}", num_digits=1)
    gi.add_speak(t(lang, "menu"), language=voice(lang))
    r.add(gi)
    _say(r, lang, "no_input")
    r.add_redirect(f"{base}/menu?lang={lang}", method="POST")
    return r.to_string()


def menu_result(base, lang, digits, audio_url, associate_number, caller_id):
    lang = normalize_lang(lang)
    r = plivoxml.ResponseElement()
    if digits == "1":
        _say(r, lang, "playing")
        r.add_play(audio_url)
        _say(r, lang, "after_audio")
        r.add_redirect(f"{base}/menu?lang={lang}", method="POST")
    elif digits == "2":
        _say(r, lang, "connecting")
        dial = plivoxml.DialElement(
            action=f"{base}/dial-status?lang={lang}",
            method="POST",
            caller_id=caller_id,  # must be the Plivo-rented number in India
            timeout=30,
        )
        dial.add_number(associate_number)
        r.add(dial)
    else:
        _say(r, lang, "invalid")
        r.add_redirect(f"{base}/menu?lang={lang}", method="POST")
    return r.to_string()


def dial_status(base, lang, status):
    """Runs after the associate leg ends: hang up if it connected, else go back to the menu."""
    lang = normalize_lang(lang)
    r = plivoxml.ResponseElement()
    if status == "completed":
        _say(r, lang, "goodbye")
        r.add_hangup()
    else:
        _say(r, lang, "associate_unavailable")
        r.add_redirect(f"{base}/menu?lang={lang}", method="POST")
    return r.to_string()
