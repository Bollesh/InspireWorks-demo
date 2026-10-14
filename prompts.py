"""Prompt text and TTS language codes for each supported language."""

LANGUAGES = ("en", "es")

PROMPTS = {
    "en": {
        "voice_lang": "en-US",
        "greeting_outbound": "Hello, this is InspireWorks.",
        "greeting_inbound": "Thank you for calling InspireWorks.",
        "otp": "Please enter your 4 digit O T P.",
        "otp_wrong": "Incorrect O T P. Please try again.",
        "otp_ok": "Authentication successful.",
        "no_input": "We did not receive any input.",
        "language": "For English, press 1.",
        "menu": "Press 1 to hear a short message. Press 2 to speak with an associate.",
        "invalid": "Invalid option. Please try again.",
        "playing": "Here is your message.",
        "after_audio": "Returning to the menu.",
        "connecting": "Connecting you to an associate. Please hold.",
        "associate_unavailable": "Sorry, the associate is not available right now.",
        "goodbye": "Thank you for calling. Goodbye.",
    },
    "es": {
        "voice_lang": "es-US",
        "language": "Para español, oprima 2.",
        "menu": "Oprima 1 para escuchar un mensaje breve. Oprima 2 para hablar con un asociado.",
        "no_input": "No recibimos ninguna respuesta.",
        "invalid": "Opción no válida. Por favor, intente de nuevo.",
        "playing": "Este es su mensaje.",
        "after_audio": "Regresando al menú.",
        "connecting": "Le estamos conectando con un asociado. Por favor espere.",
        "associate_unavailable": "Lo sentimos, el asociado no está disponible en este momento.",
        "goodbye": "Gracias por su llamada. Adiós.",
    },
}


def normalize_lang(lang):
    return lang if lang in LANGUAGES else "en"


def t(lang, key):
    """Prompt text for `key` in `lang`."""
    return PROMPTS[normalize_lang(lang)][key]


def voice(lang):
    return PROMPTS[normalize_lang(lang)]["voice_lang"]
