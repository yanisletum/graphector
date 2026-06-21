import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.graph.builder import review_graph
from app.api.schemas import ReviewRequest, ReviewResponse, IssuesList
from app.cache import get_cached, set_cached
from app.limiter import limiter

router = APIRouter(prefix="/api/v1", tags=["Code Review"])


# ─── POST /review ─────────────────────────────────────────────────────────────
@router.post("/review", response_model=ReviewResponse)
@limiter.limit("5/minute")
async def review_code(request: Request, body: ReviewRequest):

    # 1. Проверяем кэш
    cached = await get_cached(body.code)
    if cached:
        cached["from_cache"] = True
        return ReviewResponse(**cached)

    # 2. Запускаем граф
    initial_state = {
        "code": body.code,
        "language": body.language_hint or "",
        "security_issues": [],
        "style_issues": [],
        "logic_issues": [],
        "final_report": "",
        "quality_score": 0,
        "attempts": 0,
    }

    try:
        result = await review_graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph error: {str(e)}")

    security = result.get("security_issues", [])
    style    = result.get("style_issues", [])
    logic    = result.get("logic_issues", [])

    response_data = {
        "language":     result["language"],
        "issues":       {
            "security": security,
            "style":    style,
            "logic":    logic,
        },
        "report":         result["final_report"],
        "quality_score":  result["quality_score"],
        "attempts":       result["attempts"],
        "total_issues":   len(security) + len(style) + len(logic),
        "from_cache":     False,
    }

    # 3. Сохраняем в кэш
    await set_cached(body.code, response_data)

    return ReviewResponse(**response_data)


# ─── GET /review/stream ───────────────────────────────────────────────────────
@router.get("/review/stream")
@limiter.limit("5/minute")
async def review_stream(request: Request, code: str):
    async def event_generator():
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

        node_labels = {
            "parse_code":      "🔍 Определяю язык...",
            "security_check":  "🔒 Проверяю безопасность...",
            "style_check":     "🎨 Проверяю стиль...",
            "logic_check":     "⚙️ Проверяю логику...",
            "generate_report": "📝 Генерирую отчёт...",
            "validate_report": "✅ Валидирую отчёт...",
        }

        try:
            async for event in review_graph.astream_events(initial_state, version="v2"):
                if await request.is_disconnected():
                    break

                kind = event.get("event")
                name = event.get("name", "")

                if kind == "on_chain_start" and name in node_labels:
                    data = json.dumps({
                        "node": name, "status": "running",
                        "message": node_labels[name],
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

                elif kind == "on_chain_end" and name in node_labels:
                    output = event.get("data", {}).get("output", {})
                    data = json.dumps({
                        "node": name, "status": "done", "output": output,
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            yield f"data: {json.dumps({'status': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── GET /health ──────────────────────────────────────────────────────────────
@router.get("/health")
async def health():
    return {"status": "ok", "service": "graphector"}
