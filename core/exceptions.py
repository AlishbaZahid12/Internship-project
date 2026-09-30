"""
Custom exception hierarchy for the whole project.
Catching these specific types (instead of bare Exception) makes error
handling in the service layer and Streamlit UI precise and predictable.
"""


class BlindAssistError(Exception):
    """Base exception for all app-specific errors."""
    pass


# ---------------- Database ----------------
class DatabaseConnectionError(BlindAssistError):
    """Raised when the app cannot connect to MySQL."""
    pass


class RecordNotFoundError(BlindAssistError):
    """Raised when a expected DB record doesn't exist."""
    pass


# ---------------- Auth ----------------
class AuthenticationError(BlindAssistError):
    """Raised on invalid login credentials."""
    pass


class DuplicateUserError(BlindAssistError):
    """Raised when signing up with a username that already exists."""
    pass


class ValidationError(BlindAssistError):
    """Raised when input data fails validation (empty fields, bad format, etc.)."""
    pass


# ---------------- Vision / Voice / RAG (used in later phases) ----------------
class CameraAccessError(BlindAssistError):
    """Raised when the webcam can't be accessed."""
    pass


class ModelLoadError(BlindAssistError):
    """Raised when a CV/OCR/embedding model fails to load."""
    pass


class SpeechRecognitionError(BlindAssistError):
    """Raised when STT fails to understand or reach the recognition service."""
    pass