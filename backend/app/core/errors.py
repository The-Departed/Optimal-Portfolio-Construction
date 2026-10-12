"""Domain errors and their mapping to HTTP responses.

Services raise these exceptions; the handlers registered in ``app.main`` convert them
into the shared ``ErrorResponse`` schema so routes stay thin.
"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorCode, ErrorResponse


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DataNotReadyError(AppError):
    """The validated dataset required for an analysis is not available."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ErrorCode.DATA_NOT_READY


class AnalysisNotImplementedError(AppError):
    """The analysis is reserved for a later implementation phase."""

    status_code = status.HTTP_501_NOT_IMPLEMENTED
    code = ErrorCode.NOT_IMPLEMENTED


class InvalidParameterError(AppError):
    """A request parameter is syntactically valid but not acceptable (e.g. unknown asset)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ErrorCode.VALIDATION_ERROR


class OptimizationFailedError(AppError):
    """The numerical optimizer did not converge to a valid allocation."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ErrorCode.OPTIMIZATION_FAILED


class InfeasibleConstraintError(AppError):
    """A user-supplied constraint (e.g. sigma_max) admits no feasible portfolio."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ErrorCode.INFEASIBLE_CONSTRAINT


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    body = ErrorResponse(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = jsonable_encoder(exc.errors(), exclude={"input", "url", "ctx"})
    body = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed.",
        details={"errors": errors},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body.model_dump(mode="json")
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
