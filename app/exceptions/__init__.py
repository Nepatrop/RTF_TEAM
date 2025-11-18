from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.exceptions.custom import NotFoundException


def init_exception_handlers(app: FastAPI):
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=400,
            content={
                "message": "Error: Integrity Constraint Violation",
                "detail": f"{exc.orig}",
            },
        )

    @app.exception_handler(NotFoundException)
    async def not_found_exception_handler(request: Request, exc: NotFoundException):
        return JSONResponse(
            status_code=404,
            content={
                "message": "Error: Not Found Exception",
                "detail": f"{exc.model.title()[:-1]} with {exc.field} {exc.value} not found",
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=422,
            content={"message": "Error: Validation Error", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"message": "Error: Internal Server Error", "detail": str(exc)},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        message = {
            400: "Error: Bad Request",
            401: "Error: Unauthorized",
            403: "Error: Forbidden",
            404: "Error: Not Found",
            409: "Error: Conflict",
            422: "Error: Validation Error",
            500: "Error: Internal Server Error",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": message.get(exc.status_code, f"Error: {exc.status_code}"),
                "detail": exc.detail,
            },
        )
