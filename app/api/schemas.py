from pydantic import BaseModel, Field


class CategorizeRequest(BaseModel):
    use_llm: bool = True


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class CategoryUpdate(BaseModel):
    category: str
