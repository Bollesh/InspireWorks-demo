"""Places the outbound demo call via Plivo's REST API."""
import plivo

import config


def place_call(to_number):
    """Call `to_number` from the Plivo number; Plivo fetches /answer when it's picked up."""
    client = plivo.RestClient(config.PLIVO_AUTH_ID, config.PLIVO_AUTH_TOKEN)
    return client.calls.create(
        from_=config.PLIVO_FROM_NUMBER,
        to_=to_number,
        answer_url=f"{config.PUBLIC_BASE_URL}/answer",
        answer_method="POST",
        hangup_url=f"{config.PUBLIC_BASE_URL}/hangup",
        hangup_method="POST",
        ring_timeout=30,
    )
