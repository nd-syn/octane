"""Typed exceptions with HTTP status codes.

Service-layer code raises these. The API layer maps them to JSON responses
in phase 9. Keeping them centralized means we never sprinkle `raise HTTPException`
throughout business logic.
"""

from __future__ import annotations


class AppError(Exception):
    """Base. All domain errors inherit from this."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


# --- 400-level ---

class BadRequest(AppError):
    status_code = 400
    code = "bad_request"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str = "rate_limited", retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


# --- domain-specific ---

class UserNotFound(NotFound):
    code = "user_not_found"


class ConversationNotFound(NotFound):
    code = "conversation_not_found"


class MessageNotFound(NotFound):
    code = "message_not_found"


class EmailTaken(Conflict):
    code = "email_taken"


class UsernameTaken(Conflict):
    code = "username_taken"


class InvalidCredentials(Unauthorized):
    code = "invalid_credentials"


class TokenInvalid(Unauthorized):
    code = "token_invalid"


class TokenExpired(Unauthorized):
    code = "token_expired"


class NotAMember(Forbidden):
    code = "not_a_member"


class NotMutualFollow(Forbidden):
    code = "not_mutual_follow"


class CannotMessageSelf(Forbidden):
    code = "cannot_message_self"
