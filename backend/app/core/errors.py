"""Uniform JSON errors: {"error": <code>, "message": <text>, ...}. Never leaks SQL or tracebacks."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import DatabaseNotConfiguredError

logger = logging.getLogger("opassure.api")

_HTTP_CODES = {400: "bad_request", 404: "not_found", 409: "conflict", 422: "validation_error", 503: "unavailable"}


class NotFoundError(Exception):
    def __init__(self, resource: str, resource_id: str):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource.capitalize()} {resource_id} not found")


class InvalidRequestError(Exception):
    """A well-formed request that makes no sense for our data (-> 422)."""


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message, **extra})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError):
        return _error(404, "not_found", str(exc), resource=exc.resource, id=exc.resource_id)

    @app.exception_handler(InvalidRequestError)
    async def invalid(_: Request, exc: InvalidRequestError):
        return _error(422, "invalid_request", str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return _error(422, "validation_error", "Request is invalid", details=details)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        return _error(exc.status_code, _HTTP_CODES.get(exc.status_code, "http_error"), str(exc.detail))

    @app.exception_handler(DatabaseNotConfiguredError)
    async def db_not_configured(_: Request, exc: DatabaseNotConfiguredError):
        logger.error("Database not configured: %s", exc)
        return _error(503, "database_not_configured", "Database is not configured (DATABASE_URL)")

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        return _error(503, "database_error", "Database unavailable or query failed")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error(500, "internal_error", "Unexpected server error")
