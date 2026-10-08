from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?[0-9][0-9\s\-()]{6,18}[0-9]$",
    message="Enter a valid phone number, e.g. +91 98765 43210.",
)
