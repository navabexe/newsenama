from fastapi import HTTPException

class TooManyRequestsException(HTTPException):
    def __init__(self, detail: str = "Too many requests. Please try again later."):
        super().__init__(status_code=429, detail=detail)
