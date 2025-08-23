from django.core import signing

_SALT = "email-unsub-v1"


def make_unsub_token(user_id: int, kind: str) -> str:
    """kind is one of: 'comment', 'like', 'art'."""
    payload = {"uid": user_id, "kind": kind}
    return signing.dumps(payload, salt=_SALT)


def load_unsub_token(token: str, max_age_days: int = 365) -> dict:
    # max_age seconds
    return signing.loads(token, salt=_SALT, max_age=max_age_days * 24 * 3600)
