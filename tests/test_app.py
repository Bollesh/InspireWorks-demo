import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

import app as app_module
import config

BASE = "https://example.ngrok-free.app"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", BASE)
    monkeypatch.setattr(config, "OTP_CODE", "1503")
    monkeypatch.setattr(config, "VALIDATE_SIGNATURE", False)
    return app_module.app.test_client()


def post_xml(client, path, **form):
    resp = client.post(path, data=form)
    assert resp.status_code == 200
    assert resp.mimetype == "application/xml"
    return ET.fromstring(resp.data)


def test_full_flow_wrong_then_right_otp_to_associate(client):
    """Walks the same path the demo video shows."""
    root = post_xml(client, "/answer", Direction="outbound", CallUUID="c1")
    assert root.find("Redirect").text == f"{BASE}/otp"
    assert post_xml(client, "/otp").find("GetInput") is not None
    assert post_xml(client, "/verify-otp", Digits="0000").find("Redirect").text == f"{BASE}/otp"
    assert post_xml(client, "/verify-otp", Digits="1503").find("Redirect").text == f"{BASE}/language"
    assert post_xml(client, "/language-select", Digits="2").find("Redirect").text == f"{BASE}/menu?lang=es"
    assert post_xml(client, "/menu?lang=es").find("GetInput") is not None
    assert post_xml(client, "/menu-select?lang=es", Digits="1").find("Play") is not None
    assert post_xml(client, "/menu-select?lang=es", Digits="2").find("Dial") is not None


def test_call_rejects_non_e164_number(client):
    resp = client.post("/call", json={"to": "98765"})
    assert resp.status_code == 400


def test_call_places_outbound_call(client, monkeypatch):
    monkeypatch.setattr(config, "PLIVO_AUTH_ID", "id")
    monkeypatch.setattr(config, "PLIVO_AUTH_TOKEN", "token")
    fake = {"message": "call fired", "request_uuid": "abc"}
    with patch("calls.place_call", return_value=fake) as place:
        resp = client.post("/call", json={"to": "+919876543210"})
    assert resp.status_code == 200
    assert resp.get_json()["request_uuid"] == "abc"
    place.assert_called_once_with("+919876543210")


def test_signature_check_rejects_unsigned_webhook(client, monkeypatch):
    monkeypatch.setattr(config, "VALIDATE_SIGNATURE", True)
    monkeypatch.setattr(config, "PLIVO_AUTH_TOKEN", "token")
    assert client.post("/answer", data={"Direction": "outbound"}).status_code == 403
    assert client.get("/").status_code == 200  # UI is not a webhook


def test_signature_check_accepts_correctly_signed_webhook(client, monkeypatch):
    from plivo.utils.signature_v3 import construct_post_url, get_signature_v3

    monkeypatch.setattr(config, "VALIDATE_SIGNATURE", True)
    monkeypatch.setattr(config, "PLIVO_AUTH_TOKEN", "token")
    form = {"Direction": "outbound", "CallUUID": "c1"}
    signed_url = construct_post_url(f"{BASE}/answer", form).decode()
    signature = get_signature_v3(b"token", signed_url, b"nonce123").decode()
    resp = client.post("/answer", data=form, headers={
        "X-Plivo-Signature-V3": signature,
        "X-Plivo-Signature-V3-Nonce": "nonce123",
    })
    assert resp.status_code == 200
