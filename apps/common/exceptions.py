"""
A single exception handler so every error the API returns has the same shape:

    {
        "error": {
            "status": 400,
            "code": "validation_error",
            "message": "email: A user with this email already exists.",
            "details": {"email": ["A user with this email already exists."]}
        }
    }

`details` is only present for validation errors, where it maps each field to its
list of problems (`non_field_errors` for object-level problems).
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)

STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"


def error_body(status_code, code, message, details=None):
    error = {"status": status_code, "code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def _first_message(data, path=()):
    """Walk a nested DRF error structure and return its first message, prefixed by the field."""
    if isinstance(data, dict):
        for key, value in data.items():
            key_path = path if key in ("non_field_errors", "detail") else (*path, str(key))
            if found := _first_message(value, key_path):
                return found
    elif isinstance(data, list):
        for item in data:
            if found := _first_message(item, path):
                return found
    elif data:
        return f"{'.'.join(path)}: {data}" if path else str(data)
    return None


def _normalise(exc):
    """Translate Django / database exceptions into DRF API exceptions."""
    if isinstance(exc, DjangoValidationError):
        return exceptions.ValidationError(as_serializer_error(exc))
    if isinstance(exc, ProtectedError):
        return Conflict("This record is still referenced by other records and cannot be deleted.")
    if isinstance(exc, IntegrityError):
        logger.warning("Integrity error converted to 409: %s", exc)
        return Conflict("This record conflicts with an existing one.")
    return exc


def api_exception_handler(exc, context):
    exc = _normalise(exc)
    response = drf_exception_handler(exc, context)

    if response is None:
        # Anything DRF does not know about is a bug: log it with the traceback and hide
        # the internals from the client.
        view = context.get("view")
        logger.exception(
            "Unhandled exception in %s", view.__class__.__name__ if view else "view", exc_info=exc
        )
        set_rollback()
        return Response(
            error_body(
                500, "server_error", "An unexpected error occurred. Please try again later."
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        details = (
            response.data
            if isinstance(response.data, dict)
            else {"non_field_errors": response.data}
        )
        response.data = error_body(
            response.status_code,
            "validation_error",
            _first_message(details) or "Invalid input.",
            details,
        )
        return response

    data = response.data
    message = data.get("detail") if isinstance(data, dict) else _first_message(data)
    response.data = error_body(
        response.status_code,
        _error_code(exc, data, response.status_code),
        str(message or "Request failed."),
    )
    return response


def _error_code(exc, data, status_code):
    """Most specific machine-readable code available, e.g. `token_not_valid`."""
    if isinstance(data, dict) and isinstance(data.get("code"), str):
        return data["code"]
    if isinstance(exc, exceptions.APIException):
        codes = exc.get_codes()
        if isinstance(codes, str):
            return codes
        return exc.default_code
    return STATUS_CODES.get(status_code, "error")
