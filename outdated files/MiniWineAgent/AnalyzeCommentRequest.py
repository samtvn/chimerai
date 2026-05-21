from pydantic import BaseModel


class AnalyzeCommentRequest(BaseModel):
    comment: str
