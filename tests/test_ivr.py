import xml.etree.ElementTree as ET

import pytest

import ivr

BASE = "https://example.ngrok-free.app"


def parse(body):
    return ET.fromstring(body)


def redirect_target(root):
    return root.find("Redirect").text


def test_answer_greets_then_goes_to_otp():
    root = parse(ivr.answer(BASE))
    assert "InspireWorks" in root.find("Speak").text
    assert redirect_target(root) == f"{BASE}/otp"


def test_otp_prompt_collects_four_dtmf_digits_without_logging():
    root = parse(ivr.otp_prompt(BASE))
    gi = root.find("GetInput")
    assert gi.get("action") == f"{BASE}/verify-otp"
    assert gi.get("inputType") == "dtmf"
    assert gi.get("numDigits") == "4"
    assert gi.get("log") == "false"
    assert redirect_target(root) == f"{BASE}/otp"  # no input -> re-prompt


def test_correct_otp_goes_to_language_menu():
    assert redirect_target(parse(ivr.otp_result(BASE, "1503", "1503"))) == f"{BASE}/language"


@pytest.mark.parametrize("digits", ["0000", "150", "", "15031"])
def test_wrong_or_empty_otp_reprompts(digits):
    root = parse(ivr.otp_result(BASE, digits, "1503"))
    assert redirect_target(root) == f"{BASE}/otp"


def test_language_prompt_speaks_both_languages():
    speaks = parse(ivr.language_prompt(BASE)).find("GetInput").findall("Speak")
    assert [s.get("language") for s in speaks] == ["en-US", "es-US"]


@pytest.mark.parametrize("digits,target", [
    ("1", f"{BASE}/menu?lang=en"),
    ("2", f"{BASE}/menu?lang=es"),
    ("5", f"{BASE}/language"),
    ("", f"{BASE}/language"),
])
def test_language_selection(digits, target):
    assert redirect_target(parse(ivr.language_result(BASE, digits))) == target


def test_menu_prompt_is_in_chosen_language():
    gi = parse(ivr.menu_prompt(BASE, "es")).find("GetInput")
    assert gi.get("action") == f"{BASE}/menu-select?lang=es"
    assert gi.find("Speak").get("language") == "es-US"
    assert "Oprima" in gi.find("Speak").text


def test_unknown_lang_falls_back_to_english():
    gi = parse(ivr.menu_prompt(BASE, "fr")).find("GetInput")
    assert gi.get("action") == f"{BASE}/menu-select?lang=en"


def menu(lang, digits):
    return parse(ivr.menu_result(BASE, lang, digits, "https://x/a.mp3", "+912264236412", "+918035454161"))


def test_menu_option_1_plays_audio_then_returns_to_menu():
    root = menu("en", "1")
    assert root.find("Play").text == "https://x/a.mp3"
    assert redirect_target(root) == f"{BASE}/menu?lang=en"


def test_menu_option_2_dials_associate_with_plivo_caller_id():
    root = menu("es", "2")
    dial = root.find("Dial")
    assert dial.get("callerId") == "+918035454161"
    assert dial.get("action") == f"{BASE}/dial-status?lang=es"
    assert dial.find("Number").text == "+912264236412"
    assert root.find("Speak").get("language") == "es-US"


def test_menu_invalid_option_reprompts_in_same_language():
    root = menu("es", "9")
    assert redirect_target(root) == f"{BASE}/menu?lang=es"
    assert root.find("Dial") is None and root.find("Play") is None


def test_dial_status_completed_hangs_up():
    assert parse(ivr.dial_status(BASE, "en", "completed")).find("Hangup") is not None


def test_dial_status_failed_returns_to_menu():
    assert redirect_target(parse(ivr.dial_status(BASE, "en", "no-answer"))) == f"{BASE}/menu?lang=en"
