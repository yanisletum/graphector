from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    code: str = Field(..., min_length=10, description="Код для ревью")
    language_hint: str | None = Field(
        None,
        description="Подсказка языка (опционально): python, js, java..."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "def get_user(id):\n    query = f'SELECT * FROM users WHERE id={id}'\n    return db.execute(query)",
                    "language_hint": "python"
                }
            ]
        }
    }


class IssuesList(BaseModel):
    security: list[str]
    style: list[str]
    logic: list[str]


class ReviewResponse(BaseModel):
    language: str
    issues: IssuesList
    report: str
    quality_score: int = Field(..., ge=0, le=10)
    attempts: int
    total_issues: int
    from_cache: bool = False
