from email_validator import validate_email, ValidatedEmail, EmailNotValidError


def get_validated_email(email: str) -> ValidatedEmail | None:
    try:
        return validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return None
