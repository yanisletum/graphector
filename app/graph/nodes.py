import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from .state import ReviewState

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY не найден. Проверь, что файл .env существует "
        "в корне проекта и содержит строку GEMINI_API_KEY=твой_ключ"
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.3,
)

# ─── Узел 1: определяем язык ──────────────────────────────────────────────────
def parse_code(state: ReviewState) -> dict:
    prompt = f"""Определи язык программирования этого кода.
Ответь ТОЛЬКО одним словом: python, javascript, java, go, other.

Код:
{state['code']}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    language = response.content.strip().lower()

    return {"language": language, "attempts": 0}


# ─── Узел 2а: проверка безопасности ──────────────────────────────────────────
def security_check(state: ReviewState) -> dict:
    prompt = f"""Ты эксперт по безопасности кода.
Найди проблемы безопасности: SQL injection, захардкоженные секреты,
небезопасные функции, открытые порты и т.д.

Код ({state['language']}):
{state['code']}

Если проблем нет — ответь: NO_ISSUES
Если есть — перечисли каждую с новой строки, начиная с "- "."""

    response = llm.invoke([HumanMessage(content=prompt)])
    issues = _parse_issues(response.content)
    return {"security_issues": issues}


# ─── Узел 2б: проверка стиля ─────────────────────────────────────────────────
def style_check(state: ReviewState) -> dict:
    prompt = f"""Ты эксперт по чистому коду.
Найди проблемы стиля: именование переменных, длина функций,
дублирование, магические числа, отсутствие docstrings.

Код ({state['language']}):
{state['code']}

Если проблем нет — ответь: NO_ISSUES
Если есть — перечисли каждую с новой строки, начиная с "- "."""

    response = llm.invoke([HumanMessage(content=prompt)])
    issues = _parse_issues(response.content)
    return {"style_issues": issues}


# ─── Узел 2в: проверка логики ─────────────────────────────────────────────────
def logic_check(state: ReviewState) -> dict:
    prompt = f"""Ты senior Python разработчик.
Найди логические проблемы: неэффективные алгоритмы, off-by-one ошибки,
неправильная обработка ошибок, бесконечные циклы, утечки памяти.

Код ({state['language']}):
{state['code']}

Если проблем нет — ответь: NO_ISSUES
Если есть — перечисли каждую с новой строки, начиная с "- "."""

    response = llm.invoke([HumanMessage(content=prompt)])
    issues = _parse_issues(response.content)
    return {"logic_issues": issues}


# ─── Узел 3: генерация финального отчёта ─────────────────────────────────────
def generate_report(state: ReviewState) -> dict:
    security = "\n".join(state.get("security_issues", [])) or "Не обнаружено"
    style = "\n".join(state.get("style_issues", [])) or "Не обнаружено"
    logic = "\n".join(state.get("logic_issues", [])) or "Не обнаружено"

    prompt = f"""Составь структурированный отчёт code review на русском языке.

Язык: {state['language']}

Проблемы безопасности:
{security}

Проблемы стиля:
{style}

Логические проблемы:
{logic}

Отчёт должен:
1. Начинаться с общей оценки (1 предложение)
2. Иметь разделы: 🔒 Безопасность, 🎨 Стиль, ⚙️ Логика
3. Заканчиваться списком приоритетных правок
4. Быть конкретным и actionable
5. Быть не длиннее 500 слов"""

    response = llm.invoke([HumanMessage(content=prompt)])
    attempts = state.get("attempts", 0) + 1
    return {"final_report": response.content, "attempts": attempts}


# ─── Узел 4: валидация отчёта (цикл!) ────────────────────────────────────────
def validate_report(state: ReviewState) -> dict:
    prompt = f"""Оцени качество этого code review отчёта по шкале 0-10.
Критерии: конкретность, наличие примеров, actionable советы, структура.

Отчёт:
{state['final_report']}

Ответь ТОЛЬКО числом от 0 до 10."""

    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        score = int(response.content.strip())
        score = max(0, min(10, score))  # clamp 0-10
    except ValueError:
        score = 5

    return {"quality_score": score}


# ─── Вспомогательная функция ──────────────────────────────────────────────────
def _parse_issues(text: str) -> list[str]:
    if "NO_ISSUES" in text:
        return []
    lines = text.strip().split("\n")
    return [line.strip() for line in lines if line.strip().startswith("-")]
