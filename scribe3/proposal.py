"""主编输出的 ⟦PROPOSAL⟧ 围栏流式状态机。

把主编(/chat/write)的流式文本拆成:围栏外=对话 delta(进右轨),围栏内=手稿改写
散文(进中区草稿卡)。跨 chunk 的标记靠"留住最后一个 ⟦ 起的尾巴"兜住,末尾 flush() 吐净。
"""
import re

_OPEN = re.compile(r"⟦PROPOSAL\s+scope=(selection|chapter|append)⟧")
_CLOSE = "⟦/PROPOSAL⟧"
_MARK = "⟦"


class ProposalParser:
    """feed(chunk)→事件列表;末尾 flush() 吐净。
    事件:('delta',t) / ('proposal_open',scope) / ('proposal_delta',t) / ('proposal_close',None)。"""

    def __init__(self):
        self.buf = ""
        self.in_prop = False

    def _emit_safe(self, kind: str, out: list) -> None:
        # 吐出不含未完成标记的前缀,留住从最后一个 ⟦ 起的尾巴(可能是被截断的标记)
        i = self.buf.rfind(_MARK)
        cut = i if i != -1 else len(self.buf)
        if cut > 0:
            out.append((kind, self.buf[:cut]))
            self.buf = self.buf[cut:]

    def feed(self, chunk: str) -> list:
        self.buf += chunk
        out: list = []
        while True:
            if not self.in_prop:
                m = _OPEN.search(self.buf)
                if not m:
                    self._emit_safe("delta", out)
                    break
                if m.start() > 0:
                    out.append(("delta", self.buf[:m.start()]))
                out.append(("proposal_open", m.group(1)))
                self.in_prop = True
                self.buf = self.buf[m.end():]
            else:
                idx = self.buf.find(_CLOSE)
                if idx == -1:
                    self._emit_safe("proposal_delta", out)
                    break
                if idx > 0:
                    out.append(("proposal_delta", self.buf[:idx]))
                out.append(("proposal_close", None))
                self.in_prop = False
                self.buf = self.buf[idx + len(_CLOSE):]
        return out

    def flush(self) -> list:
        out: list = []
        if self.buf:
            out.append(("proposal_delta" if self.in_prop else "delta", self.buf))
            self.buf = ""
        return out
