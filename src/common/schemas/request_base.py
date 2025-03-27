# common/schemas/request_base.py

from pydantic import BaseModel, Field

class BaseRequestModel(BaseModel):
    language: str = Field(default="fa", description="Language code (fa or en)")

    model_config = {
        "extra": "forbid",
        "str_strip_whitespace": True
    }
