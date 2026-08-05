"""SSE / event-stream 响应公共头。

Nginx 默认 proxy_buffering on 会把上游流式响应攒块再下发，聊天表现为
「一下蹦出一大段」。X-Accel-Buffering: no 让 Nginx 对该响应关缓冲；
Cache-Control 避免中间层缓存流。
"""
from __future__ import annotations

from typing import Any, Iterable

from fastapi.responses import StreamingResponse

SSE_MEDIA_TYPE = "text/event-stream"

SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def sse_response(body: Iterable[Any], **kwargs) -> StreamingResponse:
    """构造带反缓冲头的 StreamingResponse。"""
    headers = dict(SSE_HEADERS)
    extra = kwargs.pop("headers", None) or {}
    headers.update(extra)
    return StreamingResponse(
        body,
        media_type=kwargs.pop("media_type", SSE_MEDIA_TYPE),
        headers=headers,
        **kwargs,
    )
