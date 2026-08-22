"""Stable public validation-error contract.

The codes in this module classify public parse and validation failures without
making callers depend on human-readable wording.  Messages remain intentionally
safe and useful for an operator, but are not a compatibility surface.
"""

from __future__ import annotations

from enum import Enum
import json
from typing import Any


VALIDATION_ERROR_SCHEMA = "esio-validation-error/1.0-candidate.1"


class ValidationErrorCode(str, Enum):
    """Machine-stable failure classes for the candidate public boundary."""

    MODEL_INVALID = "MODEL_INVALID"
    UNSUPPORTED_CONTRACT = "UNSUPPORTED_CONTRACT"
    STATE_TRANSITION_INVALID = "STATE_TRANSITION_INVALID"
    CREDENTIAL_LIKE_IDENTIFIER = "CREDENTIAL_LIKE_IDENTIFIER"
    JSON_SYNTAX_INVALID = "JSON_SYNTAX_INVALID"
    JSON_DUPLICATE_KEY = "JSON_DUPLICATE_KEY"
    JSON_NUMBER_INVALID = "JSON_NUMBER_INVALID"
    JSON_DEPTH_EXCEEDED = "JSON_DEPTH_EXCEEDED"
    INPUT_SIZE_EXCEEDED = "INPUT_SIZE_EXCEEDED"
    INPUT_ENCODING_INVALID = "INPUT_ENCODING_INVALID"
    INPUT_READ_FAILED = "INPUT_READ_FAILED"
    CLI_ARGUMENT_INVALID = "CLI_ARGUMENT_INVALID"
    OUTPUT_ENCODING_FAILED = "OUTPUT_ENCODING_FAILED"


_PUBLIC_MESSAGES: dict[ValidationErrorCode, str] = {
    ValidationErrorCode.MODEL_INVALID: "Input does not satisfy the active model contract",
    ValidationErrorCode.UNSUPPORTED_CONTRACT: "Input identifies an unsupported contract",
    ValidationErrorCode.STATE_TRANSITION_INVALID: "Evidence-state transition is invalid",
    ValidationErrorCode.CREDENTIAL_LIKE_IDENTIFIER: (
        "Authorization context identifier resembles prohibited credential material"
    ),
    ValidationErrorCode.JSON_SYNTAX_INVALID: "JSON syntax is invalid",
    ValidationErrorCode.JSON_DUPLICATE_KEY: "JSON contains a duplicate object key",
    ValidationErrorCode.JSON_NUMBER_INVALID: "JSON contains an unsupported numeric value",
    ValidationErrorCode.JSON_DEPTH_EXCEEDED: (
        "JSON nesting exceeds the supported parser depth"
    ),
    ValidationErrorCode.INPUT_SIZE_EXCEEDED: "JSON input exceeds the supported size",
    ValidationErrorCode.INPUT_ENCODING_INVALID: "JSON input or output is not valid UTF-8",
    ValidationErrorCode.INPUT_READ_FAILED: "JSON input could not be read",
    ValidationErrorCode.CLI_ARGUMENT_INVALID: "Command arguments are invalid",
    ValidationErrorCode.OUTPUT_ENCODING_FAILED: "JSON output could not be produced safely",
}


class ModelValidationError(ValueError):
    """Raised when public input cannot be represented without ambiguity.

    ``code`` is the stable machine contract.  The exception string is retained
    as safe operator-facing context and may become more precise without a
    contract revision.
    """

    def __init__(
        self,
        message: str,
        *,
        code: ValidationErrorCode = ValidationErrorCode.MODEL_INVALID,
    ) -> None:
        if not isinstance(code, ValidationErrorCode):
            raise TypeError("code must be a ValidationErrorCode")
        super().__init__(message)
        self.code = code


def public_validation_error(exc: BaseException) -> dict[str, Any]:
    """Return the versioned, safe public JSON representation of ``exc``.

    This function deliberately maps broad runtime exception classes to stable
    codes.  It does not expose filesystem paths or input contents for I/O and
    encoding failures.
    """

    if isinstance(exc, ModelValidationError):
        code = exc.code
        message = _PUBLIC_MESSAGES[code]
    elif isinstance(exc, json.JSONDecodeError):
        code = ValidationErrorCode.JSON_SYNTAX_INVALID
        message = (
            "JSON syntax is invalid at "
            f"line {exc.lineno}, column {exc.colno}"
        )
    elif isinstance(exc, OSError):
        code = ValidationErrorCode.INPUT_READ_FAILED
        message = "JSON input could not be read"
    elif isinstance(exc, UnicodeError):
        code = ValidationErrorCode.INPUT_ENCODING_INVALID
        message = "JSON input or output is not valid UTF-8"
    elif isinstance(exc, RecursionError):
        code = ValidationErrorCode.JSON_DEPTH_EXCEEDED
        message = "JSON nesting exceeds the supported parser depth"
    elif isinstance(exc, OverflowError):
        code = ValidationErrorCode.JSON_NUMBER_INVALID
        message = "JSON numeric value exceeds the supported range"
    else:
        raise TypeError("unsupported public validation exception")

    return {
        "error": {
            "validation_error_schema": VALIDATION_ERROR_SCHEMA,
            "code": code.value,
            "type": type(exc).__name__,
            "message": message,
        }
    }
