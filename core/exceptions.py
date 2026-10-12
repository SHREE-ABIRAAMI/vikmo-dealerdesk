"""DealerDesk error handling and exceptions matching API_CONTRACT.md section 3."""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from django.http import Http404


def format_error(code: str, message: str, details=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details if details is not None else []
        }
    }


def error_response(code: str, message: str, details=None, status_code: int = 400):
    return Response(format_error(code, message, details), status=status_code)


class DealerDeskAPIException(APIException):
    code = "VALIDATION_ERROR"
    status_code = 400
    message = "An error occurred."
    details = []

    def __init__(self, message=None, code=None, details=None, status_code=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if details is not None:
            self.details = details
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class ValidationError(DealerDeskAPIException):
    status_code = 400
    code = "VALIDATION_ERROR"


class NotFoundError(DealerDeskAPIException):
    status_code = 404
    code = "NOT_FOUND"


class DuplicateError(DealerDeskAPIException):
    status_code = 409
    code = "DUPLICATE"


class InsufficientStockError(DealerDeskAPIException):
    status_code = 409
    code = "INSUFFICIENT_STOCK"


class InvalidTransitionError(DealerDeskAPIException):
    status_code = 409
    code = "INVALID_TRANSITION"


class OrderLockedError(DealerDeskAPIException):
    status_code = 409
    code = "ORDER_LOCKED"


class IdempotencyConflictError(DealerDeskAPIException):
    status_code = 409
    code = "IDEMPOTENCY_CONFLICT"


class SupplierUnavailableError(DealerDeskAPIException):
    status_code = 502
    code = "SUPPLIER_UNAVAILABLE"


def custom_exception_handler(exc, context):
    """Custom DRF exception handler ensuring all responses adhere to API_CONTRACT.md."""
    if isinstance(exc, DealerDeskAPIException):
        return error_response(exc.code, exc.message, exc.details, exc.status_code)

    if isinstance(exc, Http404):
        return error_response("NOT_FOUND", str(exc) or "Resource not found.", [], status_code=404)

    # Standard DRF exception handler
    response = exception_handler(exc, context)

    if response is not None:
        status_code = response.status_code
        details = []

        if status_code == 404:
            code = "NOT_FOUND"
            message = "Resource not found."
        elif status_code == 400:
            code = "VALIDATION_ERROR"
            message = "Validation error."
            if isinstance(response.data, dict):
                details = [{"field": k, "error": v} for k, v in response.data.items()]
            elif isinstance(response.data, list):
                details = [{"error": item} for item in response.data]
        elif status_code == 409:
            code = "DUPLICATE"
            message = "Conflict."
        else:
            code = "ERROR"
            message = str(response.data)

        response.data = format_error(code, message, details)
        return response

    return None
