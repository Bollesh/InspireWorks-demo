"""CLI: place the outbound demo call.

Usage: python make_call.py [+91XXXXXXXXXX]   (defaults to DEFAULT_TO_NUMBER)
The Flask app must already be running and reachable at PUBLIC_BASE_URL.
"""
import sys

import plivo

import calls
import config


def main():
    config.require("PLIVO_AUTH_ID", "PLIVO_AUTH_TOKEN", "PLIVO_FROM_NUMBER", "PUBLIC_BASE_URL")
    to_number = sys.argv[1] if len(sys.argv) > 1 else config.DEFAULT_TO_NUMBER
    if not config.is_e164(to_number):
        sys.exit(f"Invalid number {to_number!r}; use E.164 format, e.g. +919876543210")

    try:
        resp = calls.place_call(to_number)
    except plivo.exceptions.PlivoRestError as e:
        sys.exit(f"Plivo error: {e}")
    print(f"{resp['message']} — request_uuid={resp['request_uuid']}")


if __name__ == "__main__":
    main()
