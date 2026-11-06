"""
Custom Exception Classes for Subsystem 1 (User Management)
"""

class UserManagementError(Exception):
    """Base exception class for all User Management errors."""
    pass


class UserNotFoundError(UserManagementError):
    """Raised when a requested user ID or email does not exist in the database."""
    def __init__(self, message="User not found in the system."):
        super().__init__(message)


class DuplicateEmailError(UserManagementError):
    """Raised when attempting to register an account with an already registered email."""
    def __init__(self, message="An account with this email address already exists."):
        super().__init__(message)


class InactiveUserError(UserManagementError):
    """Raised when an inactive or deactivated user attempts authentication."""
    def __init__(self, message="This account has been deactivated."):
        super().__init__(message)
