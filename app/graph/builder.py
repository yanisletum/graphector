from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph

from .state import ReviewState
from .nodes import (
    parse_code, security_check, style_check,
    logic_check, generate_report, validate_report,
)
from .router import route_after_validation


def build_graph() -> CompiledGraph:
    builder = StateGraph(ReviewState)

    # Регистрируем узлы
    builder.add_node("parse_code", parse_code)
    builder.add_node("security_check", security_check)
    builder.add_node("style_check", style_check)
    builder.add_node("logic_check", logic_check)
    builder.add_node("generate_report", generate_report)
    builder.add_node("validate_report", validate_report)

    # Точка входа
    builder.set_entry_point("parse_code")

    # parse_code → три проверки параллельно
    builder.add_edge("parse_code", "security_check")
    builder.add_edge("parse_code", "style_check")
    builder.add_edge("parse_code", "logic_check")

    # Три проверки → генерация отчёта
    builder.add_edge("security_check", "generate_report")
    builder.add_edge("style_check", "generate_report")
    builder.add_edge("logic_check", "generate_report")

    # generate_report → validate_report
    builder.add_edge("generate_report", "validate_report")

    # validate_report → conditional (цикл или END)
    builder.add_conditional_edges(
        "validate_report",
        route_after_validation,
        {
            "retry": "generate_report",   # ← цикл
            "done": END,
        }
    )

    return builder.compile()


# Синглтон — создаём граф один раз при старте
review_graph = build_graph()
