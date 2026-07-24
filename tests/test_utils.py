from email_validator import ValidatedEmail
from proxy.utils import get_validated_email
from utils import get_project_version


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


def test_get_project_version_returns_project_version(mocker):
    mocker.patch(
        "utils.tomllib.load",
        return_value={"project": {"version": "1.2.3"}},
    )

    assert get_project_version() == "1.2.3"


def test_get_project_version_returns_unknown_when_version_missing(mocker):
    mocker.patch("utils.tomllib.load", return_value={"project": {}})

    assert get_project_version() == "unknown"
