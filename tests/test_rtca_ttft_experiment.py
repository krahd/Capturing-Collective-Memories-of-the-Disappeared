from __future__ import annotations

import asyncio
import json

import httpx

from scripts.run_rtca_ttft_experiment import _stream_candidate, percentile


def test_percentile_interpolates() -> None:
    assert percentile([1.0, 2.0, 3.0], 0.5) == 2.0
    assert percentile([1.0, 2.0], 0.5) == 1.5


def test_stream_candidate_reassembles_openai_sse_and_records_ttft() -> None:
    chunks = [
        {"choices": [{"delta": {"role": "assistant", "content": ""}}]},
        {"choices": [{"delta": {"content": '{"move":"INVITE_CONTINUE",'}}]},
        {"choices": [{"delta": {"content": '"utterance":"Contame."}'}}]},
    ]
    body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["stream"] is True
        return httpx.Response(
            200,
            text=body,
            headers={"content-type": "text/event-stream"},
            request=request,
        )

    async def run() -> tuple[str, float | None, float]:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await _stream_candidate(
                client,
                url="http://test/v1/chat/completions",
                api_key=None,
                model="test-model",
                system_prompt="test",
                participant_text="Hola",
                prior_raw_outputs=[],
                temperature=0.7,
                top_p=0.8,
                max_tokens=256,
            )

    text, ttft_ms, completion_ms = asyncio.run(run())
    assert text == '{"move":"INVITE_CONTINUE","utterance":"Contame."}'
    assert ttft_ms is not None
    assert ttft_ms >= 0
    assert completion_ms >= ttft_ms
