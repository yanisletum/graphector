from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from app.graph.builder import review_graph

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🔗 *Graphector*\n\n"
        "Мульти-агентный code review на LangGraph + Gemini.\n"
        "Отправь мне код — проверю безопасность, стиль и логику.\n\n"
        "Можно отправить как обычный текст или code block.",
        parse_mode="Markdown"
    )


@router.message(F.text)
async def handle_code(message: Message):
    code = message.text.strip()

    if len(code) < 10:
        await message.answer("Слишком мало кода. Отправь что-нибудь существеннее 🙂")
        return

    wait_msg = await message.answer("🔍 Анализирую код... (займёт 15-30 сек)")

    try:
        initial_state = {
            "code": code,
            "language": "",
            "security_issues": [],
            "style_issues": [],
            "logic_issues": [],
            "final_report": "",
            "quality_score": 0,
            "attempts": 0,
        }

        result = await review_graph.ainvoke(initial_state)

        report = result["final_report"]
        score = result["quality_score"]
        attempts = result["attempts"]

        header = (
            f"📋 *Graphector Review* | Язык: `{result['language']}`\n"
            f"⭐ Качество отчёта: {score}/10 | Попыток: {attempts}\n"
            f"{'─' * 30}\n\n"
        )

        await wait_msg.delete()
        full_text = header + report
        for chunk in _split_message(full_text):
            await message.answer(chunk, parse_mode="Markdown")

    except Exception as e:
        await wait_msg.edit_text(f"❌ Ошибка: {e}")


def _split_message(text: str, limit: int = 4000) -> list[str]:
    """Разбиваем длинный текст на чанки для Telegram"""
    return [text[i:i+limit] for i in range(0, len(text), limit)]
