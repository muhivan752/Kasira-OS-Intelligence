# AI SKILL

## Model Selection
CLASSIFIER = "claude-haiku-4-5-20251001"  # cepat, murah
RESPONSE   = "claude-sonnet-4-6"          # BUKAN opus

## SSE Streaming (BUKAN WebSocket untuk AI)
@app.post("/api/v1/ai/chat/stream")
async def stream_chat(query, tenant=Depends()):
    # 1. Rate limit (200/hour/tenant)
    await check_rate_limit(f"ai:{tenant.id}")
    # 2. Classify intent (READ vs WRITE)
    intent = await classify_intent(query.message)
    # 3. WRITE: confirm dulu
    if intent.is_write:
        return await request_confirmation(intent)
    # 4. Build KG context
    context = await build_kg_context(query, tenant.id)
    # 5. Stream
    async def generate():
        async with claude.messages.stream(...) as s:
            async for chunk in s.text_stream:
                yield f"data: {chunk}\n\n"
    return StreamingResponse(generate(),
        media_type="text/event-stream")

## Context
SYSTEM = """
Kamu asisten bisnis {cafe_name}. Jawab bahasa Indonesia.
Revenue hari ini: {today_revenue}
Menu populer: {top_products}
"""
