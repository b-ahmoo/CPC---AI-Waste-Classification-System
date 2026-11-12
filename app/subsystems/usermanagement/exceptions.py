class UserManagementError(Exception):
    """Base exception class for all user management subsystem errors."""
    pass

class UserNotFoundError(UserManagementError):
    """Raised when a requested user cannot be found in the system."""
    def __init__(self, message="User not found."):
        super().__init__(message)

class DuplicateEmailError(UserManagementError):
    """Raised when attempting to register an email that already exists."""
    def __init__(self, message="Email address is already registered."):
        super().__init__(message)

class DuplicateUsernameError(UserManagementError):
    """Raised when attempting to register a username that is already taken."""
    def __init__(self, message="That username is already taken."):
        super().__init__(message)

class InactiveUserError(UserManagementError):
    """Raised when an action is attempted on a deactivated account."""
    def __init__(self, message="User account is inactive."):
        super().__init__(message)
