"""
ClearSlate error hierarchy.
All errors carry stable machine code and user-facing message.
"""


class ClearSlateError(Exception):
    """Base; carries a stable machine code and a user-facing message."""

    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(f"{code}: {message}")


class ParserError(ClearSlateError):
    """Parser stage errors."""



class ExtractionValidationError(ClearSlateError):
    """Extraction validation errors (after 1 retry)."""



class BreakdownStageError(ClearSlateError):
    """Breakdown stage errors."""

