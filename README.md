# InspireWorks IVR Demo (Plivo)

An IVR built on Plivo's Voice API. It calls your phone, or you call it, and then:

1. **OTP authentication.** You enter a 4-digit OTP (a birthdate in `DDMM`, hardcoded). A wrong code re-prompts until the correct one is entered.
2. **Level 1: language.** Press `1` for English or `2` for Spanish.
3. **Level 2: action.** Press `1` to hear a short audio message or `2` to be connected to a live associate.

Invalid input or no input at any level repeats the current prompt.

## How it works

Plivo runs the phone side of the call. Whenever it needs the next instruction, it sends a webhook to this Flask app, which replies with Plivo XML (`<GetInput>`, `<Speak>`, `<Play>`, `<Dial>`, `<Redirect>`).

```
/answer → /otp ⇄ /verify-otp → /language ⇄ /language-select → /menu?lang=xx ⇄ /menu-select
                                                                        ├─ 1: <Play> MP3, back to menu
                                                                        └─ 2: <Dial> associate → /dial-status
```

- **State without a database.** The chosen language travels in the URL (`?lang=es`), and the OTP is a constant.
- **Outbound calls.** `POST /call` (web UI) or `make_call.py` (CLI) calls Plivo's REST API with `answer_url=/answer`.
- **Inbound calls.** `setup_inbound.py` links the Plivo number to an Application whose `answer_url` is the same `/answer`. Inbound and outbound calls share the whole flow; only the greeting differs.

| File | Purpose |
|---|---|
| `app.py` | Flask routes: UI, `/call`, IVR webhooks, optional signature check |
| `ivr.py` | Pure functions that build the XML for each step (unit-tested) |
| `prompts.py` | English and Spanish prompt text, plus TTS language codes |
| `calls.py` | Places the outbound call |
| `config.py` | Loads settings from `.env` |
| `make_call.py` | CLI trigger |
| `setup_inbound.py` | Creates or updates the Plivo Application and links the number for inbound calls |

## Requirements

- Python 3.11+
- A Plivo account. You need the **Auth ID** and **Auth Token** (Plivo console → Overview) and a Plivo voice number.
- A public HTTPS URL that forwards to this app, e.g. [ngrok](https://ngrok.com/download)
- A phone to receive the call. The Plivo number is Indian (`+91`), so use an Indian phone number.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env
```

Settings in `.env`:

| Variable | Meaning |
|---|---|
| `PLIVO_AUTH_ID`, `PLIVO_AUTH_TOKEN` | Plivo API credentials |
| `PLIVO_FROM_NUMBER` | Plivo number used as the caller ID (`+918035454161`) |
| `ASSOCIATE_NUMBER` | Live associate number (`+912264236412`) |
| `DEFAULT_TO_NUMBER` | Your phone, in E.164 format (`+91…`) |
| `PUBLIC_BASE_URL` | Your ngrok HTTPS URL, with no trailing slash |
| `OTP_CODE` | Birthdate in `DDMM` (e.g. March 15 → `1503`) |
| `AUDIO_URL` | Public HTTPS MP3 for option 1 (Plivo accepts MP3/WAV up to 10 MB) |
| `PLIVO_APP_ID` | Inbound only. Printed by `setup_inbound.py`. |
| `VALIDATE_SIGNATURE` | `true` rejects webhooks without a valid `X-Plivo-Signature-V3` |

## Run

```bash
# Terminal 1: expose port 5000
ngrok http 5000             # copy the https URL into PUBLIC_BASE_URL in .env

# Terminal 2: start the app (it reloads automatically when .env changes)
python app.py
```

**Outbound call:**
- Web UI: open http://localhost:5000, enter your number, and click **Call me**.
- CLI: `python make_call.py +91XXXXXXXXXX`

**Inbound call:**

Outbound calls need no setup because each call carries its own `answer_url`. Inbound calls are different. When someone dials a Plivo number, Plivo requests the `answer_url` of *the Plivo application associated with the number* ([Plivo voice overview](https://www.plivo.com/docs/voice/concepts/overview)). A number stores that link as a single `app_id`, so it answers through exactly one application at a time, and linking a new app replaces the old one.

The assigned number is shared and already linked to another application. Routing inbound calls to this app therefore means temporarily taking the number over. `setup_inbound.py` does that and remembers the previous link, and `--restore` hands the number back.

```bash
python setup_inbound.py     # first run prints PLIVO_APP_ID; add it to .env
```
Then dial `+918035454161` from your phone. Re-run `setup_inbound.py` whenever the ngrok URL changes.

The script saves the app the number was linked to before. When you're done, give the number back:
```bash
python setup_inbound.py --restore
```

## Test

Unit tests cover every XML step and a full simulated call. They make no network calls.

```bash
python -m pytest -q
```

Manual test on a real call:

1. Answer the call. You hear the greeting and the OTP prompt.
2. Enter a wrong OTP (e.g. `0000`). You hear "Incorrect OTP" and the prompt again.
3. Enter the correct OTP. You hear "Authentication successful" and the language menu.
4. Press `5`, which is invalid. The language menu repeats. Then press `2` (Spanish) or `1` (English).
5. Press `1`. The audio plays, then the menu returns.
6. Press `2`. You hear "connecting" and the associate number rings.

The app logs one line per step (`call=<CallUUID> dir=<inbound|outbound> step=…`), which is useful to show in the demo video.

## Troubleshooting

- **Call connects, then silence or a hangup.** Plivo couldn't reach `/answer`. Check that ngrok is running, that `PUBLIC_BASE_URL` matches it, and that the app was restarted after editing `.env`.
- **403 on webhooks.** `VALIDATE_SIGNATURE=true` but `PUBLIC_BASE_URL` doesn't match the URL Plivo called. Fix the URL, or set it to `false` while testing.
- **Audio doesn't play.** The MP3 must be a direct HTTPS link with no auth or redirects.
- **Dial to associate fails.** In India the caller ID must be the Plivo-rented number, which is what the app sends.
