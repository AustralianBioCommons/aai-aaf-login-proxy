from email_validator import ValidatedEmail
from proxy.utils import get_validated_email


def test_get_validated_email():
    """
    get_validated_email should return None for invalid emails, and a ValidatedEmail object for valid emails.
    """
    valid = get_validated_email("valid@example.com")
    assert isinstance(valid, ValidatedEmail)
    assert valid is not None
    assert valid.domain == "example.com"

    invalid = get_validated_email("invalid")
    assert invalid is None
