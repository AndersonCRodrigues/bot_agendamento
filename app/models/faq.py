from pydantic import BaseModel


class FAQResponse(BaseModel):
    question: str
    answer: str
