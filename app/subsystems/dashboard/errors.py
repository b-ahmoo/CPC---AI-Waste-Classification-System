"""Error handling for the Statistical Dashboard subsystem (Home Assignment 4).

Two parts:

1. A small exception hierarchy. Code in the dashboard raises these when
   something specific goes wrong, each carrying an HTTP status and a message
   that is safe to show to users.

       DashboardError                (500)  base class for all dashboard errors
       ├── InvalidSettingError       (400)  a setting value was rejected
       ├── InvalidFilterError        (400)  a query parameter (e.g. ?days=) is invalid
       └── DataSourceError           (503)  the scans/snapshot data could not be read or saved

2. DashboardErrorHandler: one class that every dashboard route uses. It logs
   the error, rolls back a failed database transaction, and turns ANY error
   into a JSON response, so the user never sees a crash or a stack trace.
"""

import logging

from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from app.extensions import db


# --- 1. Exception hierarchy ----------------------------------------------------

class DashboardError(Exception):
    """Base class for every error raised by the dashboard subsystem."""

    status_code = 500
    default_message = "The dashboard ran into a problem. Please try again."

    def __init__(self, message=None, *, field=None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.field = field  # which input caused it, if any

    def to_dict(self):
        body = {"error": self.message, "type": type(self).__name__}
        if self.field:
            body["field"] = self.field
        return body


class InvalidSettingError(DashboardError):
    """A dashboard setting (mock data, time range) was given an invalid value."""

    status_code = 400
    default_message = "That setting value is not valid."


class InvalidFilterError(DashboardError):
    """A filter in the request URL, such as ?days=, is not valid."""

    status_code = 400
    default_message = "That filter value is not valid."


class DataSourceError(DashboardError):
    """The classification data or the dashboard tables could not be read or written."""

    status_code = 503
    default_message = "The dashboard data is not available right now. Please try again later."


# --- 2. The error-handling class ------------------------------------------------

class DashboardErrorHandler:
    """Turns any error in the dashboard subsystem into a logged, user-friendly JSON response."""

    UNEXPECTED_MESSAGE = "Something went wrong in the dashboard. Please try again."

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.handled_count = 0  # how many errors this handler has dealt with

    def classify(self, error):
        """Map any exception to a DashboardError, so the rest of the code only deals with one type."""
        if isinstance(error, DashboardError):
            return error
        if isinstance(error, ValueError):
            # The model setters raise ValueError for bad values (e.g. time_range_days=0).
            return InvalidSettingError(str(error))
        if isinstance(error, SQLAlchemyError):
            return DataSourceError()
        return DashboardError(self.UNEXPECTED_MESSAGE)

    def handle(self, error):
        """Log the error, clean up, and return (JSON body, HTTP status)."""
        self.handled_count += 1
        dashboard_error = self.classify(error)

        if isinstance(error, SQLAlchemyError):
            self.logger.error("Dashboard database error: %s", error)
            self._rollback()
        elif dashboard_error.status_code >= 500 and not isinstance(error, DashboardError):
            # A real bug: keep the full traceback in the log for the developers.
            self.logger.error("Unexpected error in the dashboard", exc_info=error)
        elif dashboard_error.status_code >= 500:
            self.logger.error("Dashboard error: %s", error)
            self._rollback()
        else:
            # The user sent something invalid: not a bug, so only a warning.
            self.logger.warning("Rejected dashboard request: %s", dashboard_error.message)

        return dashboard_error.to_dict(), dashboard_error.status_code

    def response(self, error):
        """The Flask response for an error (used by the routes and the blueprint)."""
        body, status = self.handle(error)
        return jsonify(body), status

    def register(self, blueprint):
        """Catch every uncaught error inside the dashboard blueprint.

        Normal HTTP errors (404, 405, ...) keep their own status code, but are
        returned as JSON in the same format as the dashboard's other errors.
        Flask raises 404 and 405 while matching the URL, before it knows the
        blueprint, so those are registered on the app but only answer for
        URLs under the dashboard's prefix; other subsystems keep their own pages.
        """
        def http_error_as_json(error):
            return jsonify({"error": error.description, "type": type(error).__name__}), error.code

        def on_error(error):
            if isinstance(error, HTTPException):
                return http_error_as_json(error)
            return self.response(error)

        blueprint.register_error_handler(Exception, on_error)

        def on_register(state):
            prefix = state.url_prefix or "/"

            def routing_error(error):
                if request.path.startswith(prefix):
                    return http_error_as_json(error)
                return error  # not a dashboard URL: Flask's normal error page

            state.app.register_error_handler(404, routing_error)
            state.app.register_error_handler(405, routing_error)

        blueprint.record_once(on_register)

    def _rollback(self):
        """Undo the failed transaction so the next request starts with a clean session."""
        try:
            db.session.rollback()
        except Exception:  # the connection itself may be gone
            self.logger.warning("Dashboard rollback failed as well.")
