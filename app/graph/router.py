from .state import ReviewState


def route_after_validation(state: ReviewState) -> str:
    """
    Цикл: если отчёт плохой и попыток < 3 — регенерируем.
    Иначе — финиш.
    """
    score = state.get("quality_score", 0)
    attempts = state.get("attempts", 0)

    if score >= 7:
        return "done"          # отчёт хороший → END
    elif attempts >= 3:
        return "done"          # исчерпали попытки → END всё равно
    else:
        return "retry"         # отчёт плохой → назад в generate_report
