from typing import TypedDict, Annotated
import operator


class ReviewState(TypedDict):
    # Входные данные
    code: str
    language: str

    # Результаты проверок (узлы добавляют в список)
    security_issues: Annotated[list[str], operator.add]
    style_issues: Annotated[list[str], operator.add]
    logic_issues: Annotated[list[str], operator.add]

    # Финальный отчёт
    final_report: str
    quality_score: int   # 0-10, валидатор оценивает отчёт
    attempts: int         # счётчик попыток генерации отчёта
