# 写作台对话驱动写作 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans(inline,带检查点)。Steps 用 `- [ ]` 跟踪。

**Goal:** 把 scribe3 写作台改成"对话驱动"——右轨主编对话出草稿卡,接受/弃用改中间手稿;旧写作台改名「推演台」保留。

**Architecture:** 后端新 `/chat/write` SSE 用 `⟦PROPOSAL⟧` 围栏状态机分流"对话delta/工具/草稿散文";接受走扩展的 `/save-chapter`(落库+软校验+回写)。前端右轨 WriteChat 出 proposal → 中区 DraftCard 接受/弃用。复用 render/critique/discipline/ingest/agentic(:8643)。

**Tech Stack:** FastAPI + Hermes responses(:8643)+ SurrealDB;React + TipTap v3 + Tailwind v4。

---

## 文件结构

后端:
- `scribe3/proposal.py`(新):`ProposalParser` 流式围栏状态机。
- `scribe3/app.py`(改):`/chat/write` SSE + 扩 `/save-chapter`(软校验+ingest)。
- `scribe3/llm.py`(改):`_editor_write_system`(在 _editor_system 上加围栏指令)——实际放 app.py(_editor_system 在 app.py)。
- `scribe3/tests/test_proposal.py`(新)、`scribe3/tests/test_app.py`(改)。

前端(scribe3/web/src):
- `DeduceLayout.jsx`(= 现 WriteLayout.jsx 改名,逻辑不动)。
- `editor/DraftCard.jsx`(新):草稿卡。
- `WriteChat.jsx`(新,提炼 ChatView):右轨主编 cap,/chat/write,onProposal。
- `NorthStarBar.jsx`(新):顶栏北极星条。
- `WriteLayout.jsx`(重写):对话驱动写作台。
- `api.js`、`AppRail.jsx`、`App.jsx`(改)。

---

## Task 1: 围栏状态机 ProposalParser

**Files:** Create `scribe3/proposal.py`;Test `scribe3/tests/test_proposal.py`

- [ ] **Step 1: 失败测试**
```python
from scribe3.proposal import ProposalParser

def test_plain_delta():
    p = ProposalParser()
    assert p.feed("主编回话") == []  # 留尾防标记,flush 才出
    assert p.flush() == [("delta", "主编回话")]

def test_proposal_block_whole():
    p = ProposalParser()
    ev = p.feed("好的：⟦PROPOSAL scope=selection⟧新散文⟦/PROPOSAL⟧收工") + p.flush()
    kinds = [e[0] for e in ev]
    assert ("delta", "好的：") in ev
    assert ("proposal_open", "selection") in ev
    assert ("proposal_delta", "新散文") in ev
    assert ("proposal_close", None) in ev
    assert ev[-1] == ("delta", "收工")

def test_split_marker_across_chunks():
    p = ProposalParser()
    out = []
    for c in ["前文⟦PROPO", "SAL scope=chapter⟧整章", "草稿⟦/PRO", "POSAL⟧尾"]:
        out += p.feed(c)
    out += p.flush()
    assert ("proposal_open", "chapter") in out
    assert ("proposal_close", None) in out
    txt = "".join(t for k, t in out if k == "proposal_delta")
    assert txt == "整章草稿"
    assert ("delta", "前文") in out and ("delta", "尾") in out
```

- [ ] **Step 2: 跑测试看失败** — `scribe3/.venv/bin/python -m pytest scribe3/tests/test_proposal.py -q` → FAIL(no module)。

- [ ] **Step 3: 实现**
```python
import re

_OPEN = re.compile(r"⟦PROPOSAL\s+scope=(selection|chapter|append)⟧")
_CLOSE = "⟦/PROPOSAL⟧"
_MARK = "⟦"


class ProposalParser:
    """流式拆分主编输出:围栏外=对话 delta,围栏内=proposal 散文。
    feed(chunk)→事件列表;末尾 flush() 吐净。事件:('delta',t)/('proposal_open',scope)/
    ('proposal_delta',t)/('proposal_close',None)。跨 chunk 标记靠"留住最后一个 ⟦ 的尾巴"。"""

    def __init__(self):
        self.buf = ""
        self.in_prop = False

    def _emit_safe(self, kind, out):
        # 吐出不含未完成标记的前缀,留住从最后一个 ⟦ 起的尾巴
        i = self.buf.rfind(_MARK)
        cut = i if i != -1 else len(self.buf)
        if cut > 0:
            out.append((kind, self.buf[:cut]))
            self.buf = self.buf[cut:]

    def feed(self, chunk):
        self.buf += chunk
        out = []
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

    def flush(self):
        out = []
        if self.buf:
            out.append(("proposal_delta" if self.in_prop else "delta", self.buf))
            self.buf = ""
        return out
```

- [ ] **Step 4: 跑测试通过** — 同命令 → PASS(3 个)。
- [ ] **Step 5: commit** — `git add scribe3/proposal.py scribe3/tests/test_proposal.py && git commit -m "feat(写作台): ⟦PROPOSAL⟧ 围栏流式状态机 + TDD"`

---

## Task 2: 后端 /chat/write 端点

**Files:** Modify `scribe3/app.py`;Test `scribe3/tests/test_app.py`

- [ ] **Step 1: 失败测试**(monkeypatch responses 事件,验对话分流 + proposal)
```python
def test_chat_write_splits_proposal(store, monkeypatch):
    import scribe3.app as appmod
    def fake_events(msg, instructions, model=None):
        for t in ["这样改：", "⟦PROPOSAL scope=selection⟧", "单嫣立于老槐之下。", "⟦/PROPOSAL⟧"]:
            yield {"type": "response.output_text.delta", "delta": t}
    monkeypatch.setattr(appmod, "_responses_events", fake_events)
    r = _client(store).get("/chat/write", params={"msg": "把这段写冷点", "chapter": 1, "focalizer": "role:x"})
    body = r.text
    assert '"delta": "这样改："' in body
    assert '"proposal"' in body and "单嫣立于老槐之下" in body
    assert '"scope": "selection"' in body
```

- [ ] **Step 2: 跑失败** — `pytest scribe3/tests/test_app.py::test_chat_write_splits_proposal -v` → FAIL。

- [ ] **Step 3: 实现**(在 app.py,_editor_system 之后)
```python
def _editor_write_system(st) -> str:
    return _editor_system(st) + (
        "\n\n你能直接帮作者写/改这部书的手稿。规则:\n"
        "- 若作者只是讨论/提问 → 正常回话,不要写手稿。\n"
        "- 若作者要你写或改手稿(写本章/续写/把某段改成…)→ 先简短说一句你怎么处理,"
        "然后把**要落到手稿的新散文**放进围栏,严格用此格式(scope 取 chapter=整章/selection=改选中段/append=续写接在后面):\n"
        "⟦PROPOSAL scope=chapter⟧\n（新散文，纯正文，不要解说）\n⟦/PROPOSAL⟧\n"
        "围栏里只放正文散文本身。贴住焦点者知识帧(限知),别写帧外私密。"
    )


@app.get("/chat/write")
def chat_write(msg: str, chapter: int = 1, focalizer: str = "", work: str = "main"):
    from scribe3.llm import hermes_responses_events
    from scribe3.proposal import ProposalParser
    fn = _responses_events or hermes_responses_events
    st = _store_for(work)
    instructions = _editor_write_system(st)
    if focalizer:
        instructions += f"\n本章焦点者:{focalizer};当前第 {chapter} 章。"

    def gen():
        parser = ProposalParser()
        prop = {"scope": None, "prose": []}
        def drain(events):
            for kind, val in events:
                if kind == "delta":
                    yield f"data: {json.dumps({'delta': val}, ensure_ascii=False)}\n\n"
                elif kind == "proposal_open":
                    prop["scope"] = val
                elif kind == "proposal_delta":
                    prop["prose"].append(val)
                elif kind == "proposal_close":
                    yield f"data: {json.dumps({'proposal': {'scope': prop['scope'], 'prose': ''.join(prop['prose'])}}, ensure_ascii=False)}\n\n"
                    prop["scope"] = None; prop["prose"] = []
        try:
            for ev in fn(msg, instructions):
                t = ev.get("type", "")
                if t == "response.output_text.delta":
                    yield from drain(parser.feed(ev.get("delta", "")))
                elif t == "response.output_item.added":
                    item = ev.get("item", {}) or {}
                    if item.get("type") == "function_call":
                        yield f"data: {json.dumps({'tool': item.get('name', '')}, ensure_ascii=False)}\n\n"
            yield from drain(parser.flush())
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)[:160]}, ensure_ascii=False)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 4: 跑通过** — PASS。
- [ ] **Step 5: commit** — `git commit -am "feat(写作台): /chat/write SSE 对话+围栏proposal分流 + TDD"`

---

## Task 3: 扩展 /save-chapter(软校验 + 回写)

**Files:** Modify `scribe3/app.py`;Test `scribe3/tests/test_app.py`

- [ ] **Step 1: 失败测试**
```python
def test_save_chapter_runs_softcheck(store):
    c = _client(store)
    r = c.post("/save-chapter", json={"seq": 1, "prose": "一段正常的志怪。", "focalizer": "role:x"}).json()
    assert "qc" in r and "leaks" in r  # 软校验结果随保存返回
```

- [ ] **Step 2: 跑失败** → 现 save-chapter 不返回 qc/leaks → FAIL。

- [ ] **Step 3: 实现**(改现有 save_chapter 端点,落库后跑软校验)
```python
# 在 save_chapter 端点落库后加:
from scribe3.critique import quality_flags
qf = quality_flags(prose)
leaks = st.find_leaks(prose, focalizer, seq) if focalizer else []   # 复用 mcp 的 find_leaks 逻辑;若 store 无则从 verify 导
# 自动回写(知识增量)——失败不阻断保存
try:
    from scribe3.ingest import ingest_chapter
    ingest_chapter(st, seq, lambda p: hermes_complete(p))
except Exception:
    pass
return {"ok": True, "qc": {"repetition": len(qf["repetition"]), "structural": len(qf["structural"]), "purple": len(qf["purple"])}, "leaks": len(leaks)}
```
（注:`find_leaks` 若不在 store,落到 `scribe3/verify.py` 的纯函数 `find_leaks(prose, frame_facts)`;实现时按现有代码定位最小接线。)

- [ ] **Step 4: 跑通过** → PASS。
- [ ] **Step 5: commit**

---

## Task 4: 前端 api.js — chatWrite + saveChapter QC

**Files:** Modify `scribe3/web/src/api.js`

- [ ] **Step 1-2:** 加 `chatWrite(msg, {chapter, focalizer, onDelta, onTool, onProposal, onDone, onError})`(EventSource `/chat/write`,事件分 delta/tool/proposal/done/error);`saveChapter` 返回 QC(已是 post,取返回值)。
- [ ] **Step 3: commit**

---

## Task 5: 旧 WriteLayout 改名 DeduceLayout(推演台)

**Files:** `git mv scribe3/web/src/WriteLayout.jsx scribe3/web/src/DeduceLayout.jsx`;改组件名 `WriteLayout`→`DeduceLayout`。

- [ ] **Step 1:** `git mv` + 改 `export function WriteLayout`→`DeduceLayout`。
- [ ] **Step 2:** `npm run build` 绿(此时 App 仍引旧名→下一 Task 一起改)。先不 build,Task 9/10 一起。
- [ ] **Step 3: commit**(连同 Task 9/10)

---

## Task 6: DraftCard 组件

**Files:** Create `scribe3/web/src/editor/DraftCard.jsx`

- [ ] **Step 1: 实现**——proposal 草稿卡:显示 scope 标签(整章/改这段/续写)+ 流式散文 + [接受]/[弃用]。
```jsx
import { Check, X, Sparkles } from 'lucide-react'
const LABEL = { chapter: '整章改写', selection: '改这段', append: '续写' }
export function DraftCard({ proposal, streaming, onAccept, onReject }) {
  if (!proposal) return null
  return (
    <div className="my-3 rounded-xl border border-brand/40 bg-brand/[.04] overflow-hidden">
      <div className="flex items-center gap-2 px-3 h-9 border-b border-brand/20 bg-brand/[.06]">
        <Sparkles size={14} className="text-brand" />
        <span className="text-[12px] font-medium text-brand">主编提议 · {LABEL[proposal.scope] || '改写'}</span>
        {streaming && <span className="text-[11px] text-faint">书写中…</span>}
        <div className="ml-auto flex gap-1.5">
          <button onClick={onReject} className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-[12px] text-faint hover:bg-soft cursor-pointer"><X size={13} />弃用</button>
          <button onClick={onAccept} disabled={streaming} className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-[12px] bg-brand text-white hover:opacity-90 disabled:opacity-40 cursor-pointer"><Check size={13} />接受</button>
        </div>
      </div>
      <div className="manuscript px-4 py-3 text-[15px] whitespace-pre-wrap text-ink max-h-[40vh] overflow-y-auto">{proposal.prose}</div>
    </div>
  )
}
```
- [ ] **Step 2: commit**

---

## Task 7: WriteChat(右轨主编 cap)

**Files:** Create `scribe3/web/src/WriteChat.jsx`(提炼 ChatView 的流式逻辑;新增 onProposal)

- [ ] **Step 1: 实现**——消息列表 + 输入;发消息走 `api.chatWrite`;onDelta 累进助手气泡;**onProposal 回调把 proposal 提给父(中区)**;onTool 显 chip。结构同 ChatView 但右轨窄版,且不自带视图壳。Props:`{chapter, focalizer, seedQuote, onProposal}`。
- [ ] **Step 2: commit**

---

## Task 8: NorthStarBar

**Files:** Create `scribe3/web/src/NorthStarBar.jsx`

- [ ] **Step 1: 实现**——顶栏常驻条:读 `api.intent()`,显读者感受/情感弧/红线(紧凑,可点开编辑);状态色左边框。
- [ ] **Step 2: commit**

---

## Task 9: 新 WriteLayout(对话驱动,组装)

**Files:** Create `scribe3/web/src/WriteLayout.jsx`(新)

- [ ] **Step 1: 实现**——Shell:顶栏(章导航 + NorthStarBar + 视角安静下拉)+ 中区(ProseEditor + DraftCard 叠加 + 划词"让主编改这段")+ 右轨(WriteChat 默认 cap + 校验/伏笔/设定速查/本章在场 支撑 caps)。
  - state:proposal(来自 WriteChat onProposal)、prose、selection。
  - 接受 proposal:按 scope 应用进 prose(chapter=整体替换;append=接在后;selection=替换选区)→ `api.saveChapter` → 拿 qc/leaks 刷新校验 cap → proposal 清空。
  - 弃用:proposal 清空。
  - 划词"让主编改这段":把选区文本塞进 WriteChat 的 seedQuote + 聚焦右轨。
- [ ] **Step 2: build 绿**
- [ ] **Step 3: commit**

---

## Task 10: AppRail VIEWS + App 路由

**Files:** Modify `scribe3/web/src/AppRail.jsx`、`App.jsx`

- [ ] **Step 1:** VIEWS 改成 `写作台(write→新WriteLayout)·推演台(deduce→DeduceLayout)·设定库·图谱·仪表盘`;**移除独立 chat tab**(ChatView 路由删,组件留存档)。App.jsx:`view==='deduce'`→DeduceLayout;`write`→新 WriteLayout;删 `chat` 分支。
- [ ] **Step 2: build 绿**
- [ ] **Step 3: commit**

---

## Task 11: 端到端验证全逻辑

- [ ] 后端全回归 `pytest scribe3/ -q` 全绿。
- [ ] `npm run build` 绿;重启前后端;五端口在线。
- [ ] 真机:`/chat/write` 讨论分支(只回话)、动稿分支(出 proposal,围栏被正确分流)。
- [ ] 真机:接受 proposal → save-chapter 返回 qc/leaks → 推演台看帧/章更新(脊椎共用)。
- [ ] 故意诱导泄露 → leaks>0 红标。

---

## Task 12: 真机生成 3 章达乱世铜炉水平

- [ ] 用新写作台流程(提思路→主编出整章草稿→接受→回写→下一章帧更新)在真机连写 3 章。
- [ ] 每章过软校验(QC/泄露/因果/伏笔);分数噪声大,多次取均(见 [[scribe-novel-generation-validated]])。
- [ ] 质量对标乱世铜炉:限知不穿帮、跨章连贯、伏笔有埋有收、文笔入味、声音不崩。
- [ ] 产出落库(SurrealDB),可在推演台/仪表盘核验字数/QC/伏笔。

---

## 自检

- **spec 覆盖**:D1 草稿卡(Task6/9)、D2 软校验(Task3/11)、D3 围栏(Task1/2)、D4 改名+折叠(Task5/10);数据脊椎(Task11 验);3章(Task12)。✓
- **占位扫描**:Task3 find_leaks 接线点已注明"按现有代码定位最小接线"——实现时确认 find_leaks 来源(mcp.py 的 s3_find_leaks 调的纯函数),非占位。
- **类型一致**:proposal 形 `{scope, prose}` 全程一致;事件 kind 名 delta/proposal_open/proposal_delta/proposal_close 一致。✓
