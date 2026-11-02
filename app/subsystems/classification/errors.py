"""Error handling for the Waste Identification & Classification subsystem
(Home Assignment 4).

Every failure in this subsystem goes through one class, which:
1. writes the error to the log (so developers can see what went wrong), and
2. returns a short, friendly message for the page (so users never see a crash).
"""

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.subsystems.classification.classifier import ClassificationError


class ClassificationErrorHandler:
    """Turns any error in the classification subsystem into a friendly message."""

    DATABASE_MESSAGE = "The database is not available right now. Please try again later."
    UNEXPECTED_MESSAGE = "Something went wrong. Please try again."

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    def handle(self, error: Exception) -> str:
        """Log the error and return the message to show on the page."""
        if isinstance(error, ClassificationError):
            # Expected problems (bad file, API failure): the message is already user-friendly.
            self.logger.warning("Classification failed: %s", error)
            return str(error)

        if isinstance(error, SQLAlchemyError):
            self.logger.error("Database error: %s", error)
            self._rollback()
            return self.DATABASE_MESSAGE

        # Anything else is a bug: keep the full traceback in the log.
        self.logger.error("Unexpected error in the classification subsystem", exc_info=error)
        return self.UNEXPECTED_MESSAGE

    def _rollback(self):
        """Undo the failed database transaction so the next request starts clean."""
        try:
            db.session.rollback()
        except Exception:  # e.g. the connection itself is gone
            self.logger.warning("Database rollback failed as well.")