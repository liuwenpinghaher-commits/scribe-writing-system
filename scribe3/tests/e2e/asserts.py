"""跨测试复用的 SSE 解析 + 断言。只放真正复用两次以上的;单次断言内联在测试里。"""
import json


def sse_frames(response):
    """把 TestClient 的流式响应解析成 [dict, ...](每个 data: 行的 JSON)。"""
    body = b"".join(response.iter_bytes()).decode()
    frames = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            try:
                frames.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
    return frames


def assert_error_frame_carries_cause(response, cause_substr):
    """断言 SSE 里有 error 帧且携带真实异常原文,并以 done 帧优雅收尾(非裸断/500)。"""
    frames = sse_frames(response)
    errs = [f for f in frames if "error" in f]
    assert errs, f"应有 error 帧,实际帧={frames!r}"
    assert any(cause_substr in str(f["error"]) for f in errs), \
        f"error 帧应含原文 {cause_substr!r},实际={errs!r}"
    assert any(f.get("done") for f in frames), f"应有 done 帧优雅收尾,实际={frames!r}"
