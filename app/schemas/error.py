from pydantic import Field, BaseModel
from typing import List


class RequestValidationErrorBase(BaseModel):
    type: str = Field(..., title="Error Type")
    loc: List[str | int] = Field(..., title="Location")
    msg: str = Field(..., title="Message")
    ctx: dict = Field(..., title="Context")


class RequestValidationError(BaseModel):
    message: str = Field(..., title="Error Message")
    detail: List[RequestValidationErrorBase]


class ErrorResponse(BaseModel):
    message: str = Field(..., title="Error Message")
    detail: str = Field(..., title="Error Detail")
