"""
AI Energy Coach chat route
POST /api/chat  — streaming chat with OpenAI (mirrors Supabase edge function)
"""
import os
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/api/chat", tags=["chat"])

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """You are WattWise AI, an expert energy coach specializing in Kerala's 
electricity system (KSEB). Help users reduce their electricity bills, understand KSEB 
tariff slabs, optimize appliance usage, and evaluate solar options.

Key KSEB knowledge:
- Telescopic billing (≤250 units/month): progressive slab rates ₹3.35–₹8.50/unit
- Non-telescopic billing (>250 units/month): flat rate on ALL units ₹6.40–₹9.20/unit
- The 250-unit cliff is critical — crossing it dramatically increases the bill
- Fixed charge: ₹110 (1-phase), ₹220 (3-phase)
- Electricity duty: 10% on energy charge
- Fuel surcharge: ₹0.15/unit
- PM Surya Ghar subsidy available for rooftop solar

Always give practical, actionable advice. Use Indian Rupee (₹) symbol."""


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]


async def stream_openai(messages: list[dict]) -> AsyncGenerator[str, None]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    payload = {
        "model": "gpt-4o-mini",
        "stream": True,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            OPENAI_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise HTTPException(status_code=response.status_code, detail=body.decode())

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return
                    try:
                        parsed = json.loads(data)
                        content = parsed["choices"][0]["delta"].get("content")
                        if content:
                            yield f"data: {json.dumps(parsed)}\n\n"
                    except (json.JSONDecodeError, KeyError):
                        continue


@router.post("")
async def chat(req: ChatRequest):
    """Streaming SSE chat endpoint — mirrors the Supabase edge function."""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    return StreamingResponse(
        stream_openai(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
