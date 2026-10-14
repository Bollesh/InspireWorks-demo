"""Route inbound calls on the Plivo number to this app, and undo it afterwards.

    python setup_inbound.py            # point the number at this app
    python setup_inbound.py --restore  # give the number back to its previous app

Setup creates (or, if it already exists, updates) a Plivo Application named
InspireWorks-IVR whose answer_url is PUBLIC_BASE_URL/answer, then links PLIVO_FROM_NUMBER to it. The
app the number was linked to before is saved to .inbound_restore so --restore
can put it back; the number is shared, so restore as soon as you're done.
Re-run setup after every ngrok restart, since the public URL changes.
"""
import sys
from pathlib import Path

import plivo

import config

APP_NAME = "InspireWorks-IVR"  # Plivo allows only letters, numbers, - and _
RESTORE_FILE = Path(__file__).with_name(".inbound_restore")


def linked_app_id(client, number):
    """App ID the number is linked to now, or '' if none."""
    app_uri = client.numbers.get(number)["application"] or ""
    # e.g. /v1/Account/<auth_id>/Application/<app_id>/
    return app_uri.rstrip("/").rsplit("/", 1)[-1] if "/Application/" in app_uri else ""


def find_app_id(client, name):
    """ID of this account's application called `name`, or '' if there is none."""
    for app in client.applications.list(limit=20):
        if app["app_name"] == name:
            return app["app_id"]
    return ""


def setup(client, number):
    urls = dict(
        answer_url=f"{config.PUBLIC_BASE_URL}/answer",
        answer_method="POST",
        hangup_url=f"{config.PUBLIC_BASE_URL}/hangup",
        hangup_method="POST",
    )
    app_id = find_app_id(client, APP_NAME)
    if app_id:
        client.applications.update(app_id, **urls)
        print(f"Updated application {APP_NAME} ({app_id})")
    else:
        app_id = client.applications.create(app_name=APP_NAME, **urls)["app_id"]
        print(f"Created application {APP_NAME} ({app_id})")

    previous = linked_app_id(client, number)
    # Don't overwrite the saved link with our own app on a re-run.
    if previous != app_id and not RESTORE_FILE.exists():
        RESTORE_FILE.write_text(previous)
        print(f"Saved previous link ({previous or 'none'}) to {RESTORE_FILE.name}")

    client.numbers.update(number, app_id=app_id)
    print(f"Linked +{number} → {urls['answer_url']}")
    print("Run `python setup_inbound.py --restore` when you're done testing.")


def restore(client, number):
    if not RESTORE_FILE.exists():
        sys.exit("Nothing to restore: no .inbound_restore file.")
    previous = RESTORE_FILE.read_text().strip()
    if not previous:
        sys.exit(f"The number had no app before; unlink it in the Plivo console. Saved file: {RESTORE_FILE.name}")
    client.numbers.update(number, app_id=previous)
    RESTORE_FILE.unlink()
    print(f"Restored +{number} → application {previous}")


def main():
    config.require("PLIVO_AUTH_ID", "PLIVO_AUTH_TOKEN", "PLIVO_FROM_NUMBER", "PUBLIC_BASE_URL")
    client = plivo.RestClient(config.PLIVO_AUTH_ID, config.PLIVO_AUTH_TOKEN)
    # Plivo's Number resource identifies numbers without the leading '+'.
    number = config.PLIVO_FROM_NUMBER.lstrip("+")
    if "--restore" in sys.argv[1:]:
        restore(client, number)
    else:
        setup(client, number)


if __name__ == "__main__":
    main()
