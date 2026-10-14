"""Loads settings from the environment (and .env, if present)."""
import os
import re

from dotenv import load_dotenv

# override=True: Flask's reloader passes the old values down; .env must win.
load_dotenv(override=True)

E164 = re.compile(r"^\+\d{10,15}$")

PLIVO_AUTH_ID = os.getenv("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.getenv("PLIVO_AUTH_TOKEN", "")
PLIVO_FROM_NUMBER = os.getenv("PLIVO_FROM_NUMBER", "+918035454161")
ASSOCIATE_NUMBER = os.getenv("ASSOCIATE_NUMBER", "+912264236412")
DEFAULT_TO_NUMBER = os.getenv("DEFAULT_TO_NUMBER", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
PLIVO_APP_ID = os.getenv("PLIVO_APP_ID", "")
VALIDATE_SIGNATURE = os.getenv("VALIDATE_SIGNATURE", "false").lower() == "true"

# Hardcoded OTP: birthdate in DDMM. The env var only overrides it for convenience.
OTP_CODE = os.getenv("OTP_CODE", "1503")

AUDIO_URL = os.getenv("AUDIO_URL", "https://s3.amazonaws.com/plivocloud/music.mp3")


def require(*names):
    """Exit with a clear message if any of the named settings is empty."""
    missing = [n for n in names if not globals().get(n)]
    if missing:
        raise SystemExit(f"Missing required settings in .env: {', '.join(missing)}")


def is_e164(number):
    return bool(E164.match(number or ""))
