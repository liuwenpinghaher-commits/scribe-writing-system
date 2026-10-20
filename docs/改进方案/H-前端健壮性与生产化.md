# 枢纽 H · 前端健壮性与生产化

> 对象:**scribe3**(根 `<repo-root>`)。前端 React 18 / Vite 6(`scribe3/web/`),后端 FastAPI(`scribe3/app.py`,:3321)。
> 本枢纽聚合**前端健壮性 + 工程化/部署**两条线,把"原型能跑"推进到"可交付他人、可生产部署"。
> 来源诊断:[03-问题诊断与整改方案.md](../系统架构/03-问题诊断与整改方案.md) §6/§7、[05-HermesAgent使用深度诊断.md](../系统架构/05-HermesAgent使用深度诊断.md)。所有问题带 `文件:行号`,可直接定位。
> **这是方案文档,不在本文真改代码。** 文中所有代码/配置为目标示例(jsx/yaml/python),供后续 TDD 实施参照。

---

## 1. 概述

scribe3 架构骨相很正(限知范式 + `_execute_write` 单一写点 + MCP elicitation 写门控,后端 24 测试覆盖广),但**前端健壮性、测试、生产化、配置**四组横切关注**集体缺失**,共同卡住"交付他人 / 暴露部署"这一步。本枢纽聚合并逐一给修法:

| 组 | 聚合问题 | 核心症状 |
|---|---|---|
| **A 前端健壮性** | P09 / P10 / P25 / P46 / P47 + api 无 `r.ok`/重试/loading-error 态 | 任一异常**整屏白屏**;`BASE` 硬编码 `:3321` 使**生产实际不可用**;后端关键端点**假成功**;`alert/confirm` 阻塞且不可主题化;模态无 focus trap/aria |
| **B 测试缺口** | P11 / P37 | 前端**零自动化测试**;`llm.py` 重试/SSE 解析无直接单测 |
| **C 生产化** | P12 / P35 / P36 / P48 / P49 | 无 Docker / 无 CI / 无 `.env.example` / 无 `requirements.txt`·`pyproject` / 迁移无版本表 |
| **D 配置** | P30 | MCP `setup_store(db="main")` 硬编码,多书 agentic **写错书** |

**目标(本枢纽完成后达成)**:① 前端任何渲染异常降级为局部错误卡而非白屏;② API base 经 `import.meta.env.VITE_API_BASE` 可配,生产可部署;③ 关键端点输入校验,不存在即 404,不再假成功;④ 前端关键路径(ProposalParser / SSE / TipTap 互转)+ `llm.py`(重试/SSE)有测试;⑤ `docker compose up` 一键拉起 SurrealDB + 后端 + 前端 + Hermes 网关;⑥ GitHub Actions 跑 `pytest` + 前端 `build` 绿;⑦ 迁移有"已应用版本"表;⑧ MCP 写工具按 `work` 切库。

---

## 2. 背景与动机

### 2.1 前端硬编码使"生产部署"实际不可行(P10/P36,三阶段但卡交付)

`scribe3/web/src/api.js:2` 把后端地址写死:

```js
const BASE = 'http://127.0.0.1:3321'
```

这意味着:**任何不在本机 `127.0.0.1:3321` 跑后端的环境(同事的机器、容器、内网他机、反代后的域名)前端都打不通**。诊断 P36 的判定即"前端硬编码使生产实际不可行"(03 §1 矩阵 P36、§7 P10/P35/P36/P48)。配套地,`scribe3/web/package.json:5-9` 只有 `dev/build/preview`,**无 `test` 脚本**,前端零测试(P11)。

### 2.2 任一前端异常 = 整屏白屏(P09)

`scribe3/web/src/main.jsx:4` 直接渲染根组件,**无 React ErrorBoundary**:

```js
createRoot(document.getElementById('root')).render(<App />)
```

React 18 的语义:子树渲染期抛出未捕获异常 → **整棵树卸载,页面白屏**,且无错误提示、无恢复入口。对一个"作者正在写长篇、随时可能命中边界数据"的工具,白屏=直接丢失工作上下文。

### 2.3 后端关键端点假成功 + 前端不查 `r.ok`(P25)

后端侧:`scribe3/app.py` 的写端点对**不存在的 id 不报 404**——`PATCH /facts/{local}`(`app.py:182`)、`DELETE /facts/{local}`(`app.py:189`)、`PATCH /characters/{local}`(`app.py:154`)等直接调 `update_record/delete_record`,底层 `store._update_by`/`_delete_by`(`store.py:259/265`)空结果静默,前端永远收 `{ok:true}`。范围参数无下界:`GET /facts?chapter=`(`app.py:102`,chapter 可为 0/负)、`GET /recall?k=`(`app.py:128`,k 可负)。

前端侧:`api.js:6-18` 的通用 helper `j/post/patch/del/put` **直接 `.then(r => r.json())`,从不检查 `r.ok`**——后端返 4xx/5xx 时,前端把错误响应体当正常数据 setState,或在 `.json()` 解析失败时静默吞掉(`api.js:66`、`api.js:121` 的 `catch(_){}`)。两端叠加 = **失败全程无声**。
> 注:`chatWrite`(`api.js:77`)与 `chatStream`(`api.js:111-123`)已有 `res.ok`/`onError` 处理,是正面参照;问题集中在 `api.js:6-18` 的简单 helper 层。

### 2.4 零测试零 CI 阻碍交付他人(P11/P12/P37)

- 前端:无 vitest/playwright,`package.json` 无 `test` 脚本(P11)。
- 后端:`llm.py` 已有 3 次重试(`llm.py:41-54`),但**无直接单测**守护"4xx 不重试 / 5xx 重试 / SSE 增量解析"这些易回归的分支(P37);且 `hermes_complete_stream`(`llm.py:57-78`)与 `hermes_responses_events`(`llm.py:81-105`)**完全没有重试**(对话/agentic 主路径,P15 关联)。
- 全仓**无 Dockerfile / 无 `.github/workflows` / 无 `requirements.txt`·`pyproject.toml` / 无 `.env.example`**(本枢纽起草前已 grep 全仓确认:scribe3 下零命中,唯一命中在无关的 `scribe/` 旧 worktree)。新人接手要靠口口相传启动四个进程(SurrealDB、后端、前端、Hermes 网关),且无法在 CI 上回归。

### 2.5 多书 agentic 写错书(P30)

`scribe3/mcp.py:259` `setup_store(ns="scribe3", db="main")` 把库写死成 `main`,`mcp.py:269` `main()` 又以默认参数调用它。后端 REST 侧早已支持 `?work=<slug>` 一书一库(`app.py:41` `_store_for`),但 MCP 侧主编 agent **只能写 `main` 库**——多书场景下主编自调 `s3_add_fact` 等写工具会**写进错误的书**(05 文档与 `AGENTIC_SETUP.md` 自承未做)。

### 2.6 与其他枢纽的边界

本枢纽聚焦"健壮性 + 工程化",**不碰**:认证(P01,留给安全枢纽 F)、写门控 REST 绕过(P02,F)、索引/N+1(P04/P05,性能枢纽)、限知持久化(P03,本体枢纽)。仅在 **CORS** 一处与 F 交接:前端 BASE 外置后,后端 `allow_origins`(`app.py:25` 当前 `["*"]`)需收紧到可配置白名单,见 §6。

---

## 3. 详细设计

> 红线遵守:React/Vite/pytest/docker 语法正确;**限知不破**(不改投影/门控语义);**后端所有世界状态写仍经 `store._execute_write`**(`store.py:121`),本枢纽不新增写路径,只加"写前校验 + 404"。

### A 组 · 前端健壮性

#### A1 · React ErrorBoundary 防白屏(P09)

新增 `scribe3/web/src/ErrorBoundary.jsx`(class 组件,React 唯一能捕获子树渲染错误的形式),在 `main.jsx` 包住 `<App/>`:

```jsx
// scribe3/web/src/ErrorBoundary.jsx
import { Component } from 'react'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }   // 渲染期异常 → 进降级 UI,而非白屏
  }

  componentDidCatch(error, info) {
    // 可观测:打到 console,后续可接上报端点
    console.error('[scribe3] UI 渲染异常:', error, info?.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="m-6 rounded-xl border border-danger/40 bg-danger/5 p-5">
          <h2 className="text-ink text-[15px] font-semibold mb-1">界面出错了</h2>
          <p className="text-faint text-[13px] mb-3">本视图渲染异常,你的书稿未受影响。可重试或刷新页面。</p>
          <pre className="text-[11px] text-faint/80 whitespace-pre-wrap mb-3">{String(this.state.error?.message || this.state.error)}</pre>
          <button onClick={this.reset} className="h-8 px-3 rounded-lg border border-line text-[13px] text-ink hover:border-brand/50">重试</button>
        </div>
      )
    }
    return this.props.children
  }
}
```

```jsx
// scribe3/web/src/main.jsx(目标)
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ErrorBoundary } from './ErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
)
```

> 进阶(可选):在 shell 的视图切换层(每个视图外)再各包一层 ErrorBoundary,使单视图崩溃不影响其他视图——但顶层一层已满足"不白屏 + 可恢复"的验收底线。

#### A2 · API base 外置 + 统一 `r.ok`/loading/error(P10 + 前端 api)

**(a) BASE 外置**。`api.js:2` 改用 Vite 的 `import.meta.env`(Vite 约定:`VITE_` 前缀变量才注入客户端):

```js
// scribe3/web/src/api.js(目标头部)
// 生产经 VITE_API_BASE 注入;开发缺省回退到本机 :3321。
const BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:3321'
```

配套 `scribe3/web/.env.example`(见 C3):`VITE_API_BASE=http://127.0.0.1:3321`。生产构建时设 `VITE_API_BASE=/api`(经反代)或绝对域名即可,无需改码。

**(b) 统一 `r.ok` 检查 + 错误类型**。给 `api.js:6-18` 的 helper 包一层 `handle`,把非 2xx 转成可识别的 `ApiError`:

```js
// scribe3/web/src/api.js(目标:替换裸 .then(r => r.json()))
export class ApiError extends Error {
  constructor(status, body) { super(`HTTP ${status}`); this.status = status; this.body = body }
}

async function handle(res) {
  if (!res.ok) {
    let body = null
    try { body = await res.json() } catch { /* 非 JSON 错误体 */ }
    throw new ApiError(res.status, body)
  }
  return res.json()
}

const j     = (p)       => fetch(BASE + ww(p)).then(handle)
const post  = (p, body) => fetch(BASE + ww(p), { method: 'POST',  headers: H, body: enc2(body) }).then(handle)
const patch = (p, body) => fetch(BASE + ww(p), { method: 'PATCH', headers: H, body: JSON.stringify(body) }).then(handle)
const put   = (p, body) => fetch(BASE + ww(p), { method: 'PUT',   headers: H, body: JSON.stringify(body) }).then(handle)
const del   = (p)       => fetch(BASE + ww(p), { method: 'DELETE' }).then(handle)
```

**(c) 统一 loading/error 态 hook**。前端各视图当前手写 `useEffect(() => api.x().then(setState))`,无 loading/error 分支(03 §4 "数据获取无缓存去重")。引入轻量 `useAsync` 把三态收口(不引重型依赖,先解决"失败可见";React Query 类缓存留作后续 P04/P38 性能枢纽):

```jsx
// scribe3/web/src/useAsync.js
import { useState, useEffect, useCallback } from 'react'

// fn: () => Promise<T>;deps 变化时重取。返回 { data, error, loading, reload }。
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const run = useCallback(() => {
    let live = true
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then(
      (data) => { if (live) setState({ data, error: null, loading: false }) },
      (error) => { if (live) setState({ data: null, error, loading: false }) },
    )
    return () => { live = false }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(run, [run])
  return { ...state, reload: run }
}
```

视图侧统一渲染 loading/error/data 三态(配合 A1 的 ErrorBoundary 兜住极端情况),失败时给"重试"按钮(`reload`)。

> **(d) 轻量重试(可选)**:对幂等的 GET 读端点,可在 `handle` 外再包一个"5xx/网络错最多重试 2 次、指数退避"的封装;写端点(POST/PATCH/DELETE)**不自动重试**(避免重复落库)。与后端 `llm.py` 的重试语义(4xx 不重试)对齐。

#### A3 · 后端关键端点输入校验 + 存在性 404(P25)

> 红线:写仍经 `_execute_write`;这里只在端点层加"范围校验 + 写前查存在性",**不改写路径语义**。

**(a) 范围校验**——用 FastAPI 的 `Query(ge=1)`:

```python
# scribe3/app.py(目标:facts / recall / events / frame / irony / causal 等带 chapter|k 的端点)
from fastapi import Query

@app.get("/facts")
def facts(chapter: int = Query(ge=1), work: str = "main"):
    return _facts(_store_for(work).facts_at(chapter))

@app.get("/recall")
def recall(q: str, k: int = Query(default=5, ge=1, le=50), work: str = "main"):
    return _facts(_store_for(work).semantic_recall(q, k))
```

`chapter` 当前在 `app.py:102/107/113/118/123` 多处裸 `int`,统一加 `Query(ge=1)`;`k`(`app.py:128`)加 `ge=1, le=50`。校验失败 FastAPI 自动返 422(无需手写)。

**(b) 写前存在性 → 404**——给 store 加一个只读 `exists(oid)`(走 `_query`,不是写,不碰 `_execute_write`),端点写前先查:

```python
# scribe3/store.py(新增只读辅助,非写路径)
def exists(self, oid: str) -> bool:
    rows = self._query("SELECT id FROM ONLY type::thing($oid) LIMIT 1", {"oid": oid})
    return bool(rows)
```

```python
# scribe3/app.py(目标:PATCH/DELETE facts·characters·promises·motifs)
from fastapi import HTTPException

@app.patch("/facts/{local}")
def edit_fact(local: str, f: FactIn, work: str = "main"):
    st = _store_for(work)
    if not st.exists(f"fact:{local}"):
        raise HTTPException(status_code=404, detail="fact not found")
    st.update_record(f"fact:{local}", {"entity": f.entity, "attribute": f.attribute,
                                       "value": f.value, "secret": f.secret})
    return {"ok": True}

@app.delete("/facts/{local}")
def del_fact(local: str, work: str = "main"):
    st = _store_for(work)
    if not st.exists(f"fact:{local}"):
        raise HTTPException(status_code=404, detail="fact not found")
    st.delete_record(f"fact:{local}")
    return {"ok": True}
```

同样模式套到 `edit_char`/`del_char`(`app.py:154/160`)、`edit_prom`/`del_prom`(`app.py:207/213`)、motif 等。前端 `handle`(A2-b)收到 404 即抛 `ApiError`,视图给"该条目已不存在"提示而非假成功。
> `exists` 的 surql 用参数 `$oid` 绑定(`type::thing`),不拼字符串,顺带不踩 P24 注入面。

#### A4 · alert/confirm → toast/确认浮层(P46)

`Library.jsx:18`(`window.alert('主书不可删除')`)、`Library.jsx:19`(`window.confirm`)、`CodexView.jsx:84` 等用原生对话框——阻塞、不可主题化、无法测试。改为应用内 toast + 确认浮层(轻量 context,不引第三方):

```jsx
// scribe3/web/src/Toast.jsx(草案:Provider + useToast + useConfirm)
import { createContext, useContext, useState, useCallback } from 'react'

const Ctx = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [confirmer, setConfirmer] = useState(null)

  const toast = useCallback((msg, kind = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, msg, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200)
  }, [])

  // 返回 Promise<boolean>,替代 window.confirm
  const confirm = useCallback((text) => new Promise((resolve) => {
    setConfirmer({ text, resolve })
  }), [])

  return (
    <Ctx.Provider value={{ toast, confirm }}>
      {children}
      <div className="fixed bottom-4 right-4 flex flex-col gap-2 z-50" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} role="status"
            className="rounded-lg border border-line bg-surface px-4 py-2.5 text-[13px] text-ink shadow-md">
            {t.msg}
          </div>
        ))}
      </div>
      {confirmer && (
        <ConfirmDialog text={confirmer.text}
          onYes={() => { confirmer.resolve(true); setConfirmer(null) }}
          onNo={() => { confirmer.resolve(false); setConfirmer(null) }} />
      )}
    </Ctx.Provider>
  )
}

export const useToast = () => useContext(Ctx).toast
export const useConfirm = () => useContext(Ctx).confirm
```

`Library.jsx` 的 `del` 改为:

```jsx
const toast = useToast(); const confirm = useConfirm()
const del = async (e, w) => {
  e.stopPropagation()
  if (w.slug === 'main') { toast('主书不可删除', 'warn'); return }
  if (await confirm(`删除《${w.title}》?该书所有内容将永久丢失。`)) {
    try { await api.deleteWork(w.slug); await reload(); toast('已删除') }
    catch (err) { toast(`删除失败:${err.message}`, 'error') }
  }
}
```

`ConfirmDialog` 复用 A5 的可访问模态(focus trap + Esc + aria),一举解决 P46 + P47。

#### A5 · a11y:模态 focus trap + aria(P47)

诊断点名 `shell.jsx`、`CommandPalette.jsx` 的模态/命令面板无 focus trap、无 aria、拖拽无键盘可达。提供一个可复用的 `Modal`(A4 的 `ConfirmDialog` 也基于它):

```jsx
// scribe3/web/src/Modal.jsx
import { useEffect, useRef } from 'react'

export function Modal({ title, onClose, children }) {
  const ref = useRef(null)
  useEffect(() => {
    const node = ref.current
    const prev = document.activeElement
    const focusables = () => node.querySelectorAll(
      'a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])')
    focusables()[0]?.focus()  // 打开即聚焦首个可聚焦元素
    const onKey = (e) => {
      if (e.key === 'Escape') { onClose(); return }
      if (e.key !== 'Tab') return
      const els = [...focusables()]; if (!els.length) return
      const first = els[0], last = els[els.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    node.addEventListener('keydown', onKey)
    return () => { node.removeEventListener('keydown', onKey); prev?.focus?.() } // 关闭归还焦点
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className="rounded-2xl border border-line bg-surface p-5 w-[min(92vw,440px)]">
        {title && <h2 className="text-ink text-[15px] font-semibold mb-3">{title}</h2>}
        {children}
      </div>
    </div>
  )
}
```

要点(WAI-ARIA Dialog 模式):`role="dialog"` + `aria-modal="true"` + `aria-label`;打开聚焦、`Tab`/`Shift+Tab` 在模态内循环、`Esc` 关闭、关闭归还焦点给触发元素;遮罩点击关闭。命令面板(`CommandPalette.jsx`)套同款键盘约束;拖拽交互(若有)补键盘等价操作(方向键移动)——拖拽键盘可达可标 **需人工确认**具体交互后细化。

---

### B 组 · 测试

#### B1 · 前端 vitest 关键路径(P11)

`package.json` 加 vitest + 测试脚本(devDependencies):

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.0",
    "jsdom": "^25.0.0"
  }
}
```

`vite.config.js` 加 test 段(jsdom 环境):

```js
// vite.config.js(test 段)
export default defineConfig({
  // ...plugins
  test: { environment: 'jsdom', setupFiles: ['./src/setupTests.js'], globals: true },
})
```

**关键路径**(spec 点名 ProposalParser / SSE / TipTap):

1. **ProposalParser**(围栏流式状态机)。当前实现是**后端** `scribe3/proposal.py`,而前端 `chatWrite`(`api.js:69-110`)的 SSE 消费侧靠 `onProposal` 回调——若前端另有一份 JS 版围栏解析(需人工确认其文件位置),它正是 vitest 头号目标。测例覆盖:跨 chunk 截断的 `⟦PROPOSAL scope=…⟧` 标记被正确"留尾"、围栏内外分流、`flush()` 吐净。

   ```js
   // scribe3/web/src/__tests__/proposalParser.test.js(以前端 JS 解析器为例)
   import { describe, it, expect } from 'vitest'
   import { ProposalParser } from '../proposalParser'   // 路径需人工确认

   describe('ProposalParser', () => {
     it('围栏外文本走 delta', () => {
       const p = new ProposalParser()
       expect(p.feed('你好')).toEqual([['delta', '你好']])
     })
     it('跨 chunk 截断的开标记被留尾,不误吐', () => {
       const p = new ProposalParser()
       const a = p.feed('正文⟦PROPOSAL sco')   // 标记被切断
       expect(a).toEqual([['delta', '正文']])    // 只吐安全前缀,标记尾巴留住
       const b = p.feed('pe=chapter⟧改写正文')
       expect(b).toContainEqual(['proposal_open', 'chapter'])
     })
   })
   ```

2. **SSE 解析**(`api.js:chatWrite` 的 `data:` 行分帧 + JSON 解析 + delta/tool/proposal/done/error 分发)。把 `api.js:78-105` 的逐行解析逻辑抽成纯函数 `parseSSELine(line)` 便于单测;mock 一个 `ReadableStream` 喂分块(含被切成两半的 `data:` 行),断言回调序列正确、`done` 后停止。

3. **TipTap 互转**(草稿卡 ↔ 编辑器内容的序列化/反序列化)。对编辑器的 prose ↔ TipTap JSON 互转做往返测试(round-trip 不丢内容/标记),保证草稿采纳(`proposal` → 中区草稿卡)不损字。具体 helper 文件 **需人工确认**(TipTap 配置在 `scribe3/web/src/` 编辑器组件内)。

4. **ErrorBoundary 捕获**(配合 A1,见 B 组 TDD):渲染一个会 throw 的子组件,断言降级 UI(`role="alert"`)出现、`reset` 后恢复。

5. **useAsync / api `handle`**:mock `fetch` 返 500,断言 `useAsync` 进 `error` 态、`handle` 抛 `ApiError(status=500)`。

#### B2 · `llm.py` 单测(重试 / SSE,P37)

`llm.py:41-54` 的重试矩阵(5xx/超时/连接错重试,4xx 立即抛)与 `hermes_complete_stream` 的 SSE 增量解析(`llm.py:67-78`)目前零守护。用 `respx`(httpx 的 mock 库)写 pytest:

```python
# scribe3/tests/test_llm.py(草案)
import httpx, pytest, respx
from scribe3 import llm

URL = "http://127.0.0.1:8642/v1/chat/completions"

@respx.mock
def test_retry_on_5xx_then_succeeds():
    route = respx.post(URL).mock(side_effect=[
        httpx.Response(503),                       # 第一次 5xx → 重试
        httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}),
    ])
    assert llm.hermes_complete("hi") == "ok"
    assert route.call_count == 2                    # 确实重试了一次

@respx.mock
def test_4xx_does_not_retry():
    route = respx.post(URL).mock(return_value=httpx.Response(400))
    with pytest.raises(httpx.HTTPStatusError):
        llm.hermes_complete("hi")
    assert route.call_count == 1                    # 4xx 不重试

@respx.mock
def test_stream_parses_sse_deltas():
    sse = (b'data: {"choices":[{"delta":{"content":"\xe4\xbd\xa0"}}]}\n\n'
           b'data: {"choices":[{"delta":{"content":"\xe5\xa5\xbd"}}]}\n\n'
           b'data: [DONE]\n\n')
    respx.post(URL).mock(return_value=httpx.Response(200, content=sse))
    assert "".join(llm.hermes_complete_stream("hi")) == "你好"
```

> `respx` 入 `requirements-dev`/`pyproject` 的 dev 组(见 C4)。同样可给 `hermes_responses_events`(`llm.py:81-105`)补一条 SSE 解析单测。

---

### C 组 · 生产化

#### C1 · docker-compose 一键拉起(P12)

四服务编排:SurrealDB(:8001)、后端(:3321)、前端(:3311 静态/或 Vite preview)、Hermes 网关(:8642 默认 + :8643 scribe3)。Hermes 镜像/启动方式 **需人工确认**(Hermes 是底座,见 MEMORY;其容器化方式由 Hermes 提供,这里给占位与挂载约定)。

```yaml
# docker-compose.yml(scribe3 根)
services:
  surreal:
    image: surrealdb/surrealdb:latest      # 版本对齐 surreal version 实测(MEMORY: 3.1.5)
    command: start --user ${SURREAL_USER:-root} --pass ${SURREAL_PASS:-root} --bind 0.0.0.0:8001 rocksdb:/data/scribe3.db
    ports: ["8001:8001"]
    volumes: ["surreal-data:/data"]

  backend:
    build: { context: ., dockerfile: Dockerfile }
    environment:
      SCRIBE3_SURREAL_URL: ws://surreal:8001/rpc
      SCRIBE3_SURREAL_USER: ${SURREAL_USER:-root}
      SCRIBE3_SURREAL_PASS: ${SURREAL_PASS:-root}
      HERMES_API: http://hermes:8642/v1
      HERMES_RESPONSES_API: http://hermes:8643/v1
      SCRIBE3_CORS_ORIGINS: ${SCRIBE3_CORS_ORIGINS:-http://127.0.0.1:3311}
    command: uvicorn scribe3.app:app --host 0.0.0.0 --port 3321
    ports: ["3321:3321"]
    depends_on: [surreal]

  frontend:
    build: { context: ./web, dockerfile: Dockerfile }
    environment:
      VITE_API_BASE: ${VITE_API_BASE:-http://127.0.0.1:3321}
    ports: ["3311:80"]
    depends_on: [backend]

  hermes:                                   # 占位:实际镜像/挂载需人工确认(Hermes 提供)
    image: hermes-agent:0.17.0              # 需人工确认
    volumes: ["~/.hermes:/root/.hermes"]    # profile/config/MCP 挂载,需人工确认
    ports: ["8642:8642", "8643:8643"]

volumes:
  surreal-data:
```

> 关键依赖说明:`SCRIBE3_SURREAL_URL` 后端已支持(`store.py:101` 读 `os.environ.get("SCRIBE3_SURREAL_URL", ...)`),凭证 `user/password` 当前**仅函数默认 `root/root`**(`store.py:100-101`),需补 `os.environ.get` 才能被 compose 注入(与安全枢纽 P08 交接,本枢纽给出 env 钩子位置)。

后端 `Dockerfile`(scribe3 根):

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 3321
CMD ["uvicorn", "scribe3.app:app", "--host", "0.0.0.0", "--port", "3321"]
```

前端 `web/Dockerfile`(多阶段:build → nginx 托管静态):

```dockerfile
# web/Dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE=http://127.0.0.1:3321
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

> 注:`VITE_API_BASE` 在前端是**构建期**注入(Vite 把 `import.meta.env` 编译进产物),故经 `ARG`/`ENV` 传入 build 阶段;若要运行期切换 base,需改用运行期 `window.__ENV__` 注入(留作进阶,需人工确认部署形态)。

#### C2 · GitHub Actions(pytest + build,P12)

```yaml
# .github/workflows/ci.yml
name: ci
on: { push: { branches: [main] }, pull_request: {} }

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      surreal:
        image: surrealdb/surrealdb:latest
        ports: ["8001:8001"]
        options: >-
          --health-cmd "true"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest scribe3/tests -q
        env:
          SCRIBE3_SURREAL_URL: ws://127.0.0.1:8001/rpc

  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: web } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: web/package-lock.json }
      - run: npm ci
      - run: npm run test
      - run: npm run build
```

> SurrealDB 服务容器的健康探针与启动命令 **需人工确认**(部分测试用内存 World 不需真库;真库测试需 `surreal start`)。CI 绿的判据:`pytest` 全过 + 前端 `vitest` 全过 + `vite build` 成功。

#### C3 · `.env.example`(P35)

两份(后端根 + 前端 `web/`),把当前散在代码的环境变量集中文档化:

```bash
# .env.example(scribe3 根 · 后端)
# SurrealDB(store.py:101 已读 URL;USER/PASS 待补 env 钩子,见 P08)
SCRIBE3_SURREAL_URL=ws://127.0.0.1:8001/rpc
SCRIBE3_SURREAL_USER=root
SCRIBE3_SURREAL_PASS=root
# Hermes 网关(llm.py:12/14)
HERMES_API=http://127.0.0.1:8642/v1
HERMES_RESPONSES_API=http://127.0.0.1:8643/v1
# Hermes API key(llm.py:18 读 API_SERVER_KEY,缺省回退 ~/.hermes/.env)
API_SERVER_KEY=
# CORS 白名单(app.py:25,逗号分隔;见 §6 与安全枢纽交接)
SCRIBE3_CORS_ORIGINS=http://127.0.0.1:3311
```

```bash
# web/.env.example(前端)
VITE_API_BASE=http://127.0.0.1:3321
```

变量来源核对(全部带 file:line):`SCRIBE3_SURREAL_URL`→`store.py:101`;`HERMES_API`/`HERMES_RESPONSES_API`→`llm.py:12/14`;`API_SERVER_KEY`→`llm.py:18`;`VITE_API_BASE`→新增(A2)。

#### C4 · `requirements.txt` / `pyproject.toml`(P48)

后端依赖当前隐式(`.venv` 里有但无清单)。固化运行期依赖(从代码 import 实证:`fastapi`、`uvicorn`、`httpx`、`surrealdb`、`pydantic`;`embed.py`/向量召回的具体 embedding 依赖 **需人工确认**):

```
# requirements.txt
fastapi>=0.115
uvicorn[standard]>=0.32
httpx>=0.27
surrealdb>=1.0          # 版本对齐 `surreal version` 与 surrealdb-py 实测,需人工确认
pydantic>=2.0
```

```
# requirements-dev.txt
-r requirements.txt
pytest>=8.0
respx>=0.21             # llm.py 单测 mock(B2)
```

或合并进 `pyproject.toml`:

```toml
# pyproject.toml(可选,替代两份 requirements)
[project]
name = "scribe3"
version = "0.3.0"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "httpx>=0.27", "surrealdb>=1.0", "pydantic>=2.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "respx>=0.21"]
```

> 精确版本号必须对实际 `.venv` 里已装版本核验后写入(红线:工具版本以二进制/`pip show` 为准,不照搬本文占位),否则标 **需人工确认**。

#### C5 · 迁移版本表(P49)

`store.apply_schema`(`store.py:115-119`)每次启动**无条件重跑** `migrations/*.surql` 全部文件,无"已应用版本"记录、无回滚。补一张 `_migration` 表,只跑未应用的:

```python
# scribe3/store.py(目标:apply_schema 带版本表)
def apply_schema(self, migrations_dir: str | None = None) -> None:
    d = Path(migrations_dir or Path(__file__).parent / "migrations")
    self._db.query("DEFINE TABLE IF NOT EXISTS _migration SCHEMALESS; "
                   "DEFINE FIELD IF NOT EXISTS applied_at ON _migration TYPE datetime;")
    applied = {r["id"] for r in (self._query("SELECT id FROM _migration") or [])}
    for f in sorted(d.glob("*.surql")):
        key = f"_migration:`{f.stem}`"
        if key in applied:
            continue
        self._db.query(f.read_text(encoding="utf-8"))
        self._db.query("CREATE type::thing('_migration', $name) SET applied_at = time::now()",
                       {"name": f.stem})
```

> 回滚:每个迁移可配对一个 `*.down.surql`,提供 `rollback(name)` 读对应 down 脚本执行——但"无条件重跑→按版本跳过"已消除 P49 的核心风险(重复 DEFINE 多为幂等,真正的隐患是未来非幂等迁移被重跑);down 脚本机制留作进阶。迁移写表 `_migration` 属注册表性质,与世界状态写分离,不破坏 `_execute_write` 不变量(参照 P23 对注册表写的豁免定性)。

---

### D 组 · 配置

#### D1 · MCP `setup_store` 带 work 参数(P30)

`mcp.py:259` 的 `db="main"` 硬编码使主编 agent 只能写 `main` 库。让库可经环境变量/参数注入,使每书一个 MCP 网关 profile 能指向自己的库:

```python
# scribe3/mcp.py(目标:setup_store / main 带 work)
def setup_store(ns: str = "scribe3", db: str | None = None):
    """连 NS=scribe3 + 幂等建 schema。db 缺省读环境变量 SCRIBE3_WORK,再回退 main。"""
    from scribe3.store import SurrealStore
    db = db or os.environ.get("SCRIBE3_WORK", "main")   # 多书:每 profile 设 SCRIBE3_WORK=<slug>
    store = SurrealStore(ns=ns, db=db)
    store.apply_schema()
    set_store(store)
    return store


def main() -> None:
    setup_store()        # db 由 SCRIBE3_WORK 决定
    mcp.run()
```

落地路径(择一,**需人工确认**取舍):
- **每书一 profile**(贴合 Hermes 多 profile 现状,05 文档已有 default+scribe3 两 profile):为每本书起一个 Hermes profile,其 `run_mcp.sh` 注入 `SCRIBE3_WORK=<slug>`,主编经该 profile 网关写对应库。
- **工具参数带 work**(更动态):给 `s3_*` 写工具签名加 `work` 参数,运行时按 work 取/建 store(类似后端 `_store_for`)——但需主编每次传对 work,且 MCP server 当前单 `_store` 全局态(`mcp.py` 的 `set_store`/`_store`),改为 per-work store 字典,改动面更大。

> 红线:无论哪种,MCP 写工具仍走 `commit_if_approved` → `_store.add_*` → `_execute_write`(`mcp.py:246` 等已是此形态),本枢纽只改"写哪个库",不改"是否过门控/是否经单一写点"。

---

## 4. TDD 实施计划(bite-sized)

> 顺序原则:**测试先行**(前端组件/后端校验/llm),**生产化项以"建文件 → 验证(`docker compose up` 起 / CI 绿)"表达**。每步独立可验,失败如实记录。

### 阶段 H-1 · 前端健壮性(A 组)
1. **ErrorBoundary**:先写 `errorBoundary.test.jsx`(渲染 throw 子组件 → 断言 `role="alert"` 降级 UI;`reset` 后恢复)→ 跑红 → 实现 `ErrorBoundary.jsx` + 改 `main.jsx` → 跑绿。
2. **api `handle` + useAsync**:先写 `api.test.js`(mock fetch 返 500 → 断言抛 `ApiError(status=500)`;返 200 → 返 body)与 `useAsync.test.jsx`(loading→error/data 三态)→ 跑红 → 实现 → 跑绿。
3. **BASE 外置**:`api.test.js` 断言读 `import.meta.env.VITE_API_BASE`(vitest 可 stub `import.meta.env`),缺省回退 `:3321` → 改 `api.js:2` → 绿。
4. **ProposalParser / SSE 分帧**(若前端有 JS 版):先写截断标记/分帧测例 → 抽纯函数 `parseSSELine` → 绿。
5. **toast/confirm + Modal a11y**:先写 `modal.test.jsx`(打开聚焦首元素、`Tab` 循环、`Esc` 关闭、关闭归还焦点)→ 实现 `Modal.jsx`/`Toast.jsx` → 绿;再把 `Library.jsx:18/19` 的 alert/confirm 换掉(组件测试断言不再调用 `window.confirm`)。

### 阶段 H-2 · 后端校验(A3)
6. **范围校验**:`test_app.py` 加 `GET /facts?chapter=0` 断言 422、`GET /recall?k=-1` 断言 422 → 跑红 → 加 `Query(ge=1)` → 绿。
7. **存在性 404**:`test_app.py` 加 `PATCH /facts/不存在` 断言 404、`DELETE /characters/不存在` 断言 404 → 跑红 → 加 `store.exists` + 端点 `HTTPException(404)` → 绿。(用现有 `tests/conftest.py` 注入的内存/真库 store 夹具。)

### 阶段 H-3 · llm 单测(B2)
8. `test_llm.py`:`respx` mock,先写 5xx-重试-成功 / 4xx-不重试 / stream-SSE-解析 三例 → 跑(`hermes_complete` 应直接绿,因重试已实现;断言 `call_count` 守护回归)→ stream 用例确认 SSE 解析正确。

### 阶段 H-4 · 生产化(C 组,建文件 → 验证)
9. **requirements / pyproject**(C4):核对 `.venv` 实际版本写入 → 验证 `pip install -r requirements.txt` 在干净环境成功。
10. **.env.example**(C3):建两份 → 验证 `cp .env.example .env` 后后端/前端按文档启动可连通。
11. **Dockerfile ×2 + docker-compose**(C1):建文件 → 验证 `docker compose up` 后 `curl http://127.0.0.1:3321/health` 返 `{"ok":true}`、前端 `:3311` 可打开、前端能打通后端(Hermes 服务若需人工确认,可先 compose 起 surreal+backend+frontend 三件,Hermes 用宿主已跑的网关)。
12. **CI**(C2):建 `.github/workflows/ci.yml` → push 验证 Actions 绿(backend pytest + frontend build/test 两 job)。
13. **迁移版本表**(C5):`test_migrate.py` 加"二次 `apply_schema` 不重跑已应用迁移"断言(可断言 `_migration` 行数稳定 / 非幂等探针迁移只执行一次)→ 跑红 → 改 `apply_schema` → 绿。

### 阶段 H-5 · 配置(D 组)
14. **MCP work 切库**(D1):`test_mcp.py` 断言 `setup_store(db="bookX")` 后 `_store._db` use 的是 `bookX`、`SCRIBE3_WORK=bookY` 环境下 `setup_store()` 落到 `bookY` → 改 `mcp.py:259/269` → 绿。

---

## 5. 验收标准

| # | 标准 | 验证方式 |
|---|---|---|
| AC1 | **前端不白屏** | 故意让某视图 throw,页面显示 `role="alert"` 降级卡 + "重试",其余 shell 仍在;`errorBoundary.test.jsx` 绿 |
| AC2 | **BASE 可配** | 设 `VITE_API_BASE=https://x` 构建,产物请求打到 `https://x`;不设时回退 `:3321`;`api.test.js` 绿 |
| AC3 | **失败可见** | 后端返 4xx/5xx 时前端不假成功,toast 报错(不再 `alert`);`api.test.js` 断言 `ApiError` |
| AC4 | **后端校验生效** | `chapter=0`/`k=-1` 返 422;`PATCH/DELETE` 不存在 id 返 404;`test_app.py` 新增用例绿 |
| AC5 | **关键路径有测试** | `npm run test`(ProposalParser/SSE/ErrorBoundary/api)+ `pytest`(llm 重试·SSE、app 校验、migrate 幂等)全绿 |
| AC6 | **CI 绿** | GitHub Actions backend + frontend 两 job 通过 |
| AC7 | **docker 一键起** | `docker compose up` 后 `/health` 200、前端可访问并打通后端 |
| AC8 | **配置外置齐备** | `.env.example`(后端+前端)、`requirements.txt`/`pyproject`、`Dockerfile`×2、`docker-compose.yml`、`ci.yml` 均存在且被上述验证覆盖 |
| AC9 | **多书写对库** | MCP `setup_store` 按 `SCRIBE3_WORK`/参数落到指定库;`test_mcp.py` 绿 |
| AC10 | **迁移不重跑** | 二次 `apply_schema` 跳过已应用迁移;`_migration` 表有记录;`test_migrate.py` 绿 |
| AC11 | **a11y 底线** | 模态 `role="dialog"`+`aria-modal`+focus trap+Esc+焦点归还;`modal.test.jsx` 绿 |

---

## 6. 风险与依赖

**总体:本枢纽各项大体独立、可并行推进**(前端 A 组、后端 A3、测试 B、生产化 C、配置 D 之间无强耦合),适合分阶段落地。具体风险/依赖:

- **R-CORS(与安全枢纽 F 交接)**:前端 BASE 外置(A2)后,跨域来源不再固定 `127.0.0.1`;后端 `app.py:25` 当前 `allow_origins=["*"]` 需收紧为**可配置白名单**(读 `SCRIBE3_CORS_ORIGINS`,逗号分隔)。这是 P22 的范畴,**本枢纽给出 env 钩子位置(`.env.example` 已列 `SCRIBE3_CORS_ORIGINS`、compose 已注入),具体收紧逻辑归 F**。否则"BASE 外置但 CORS 仍 `*`"会带 DNS rebinding 风险。
- **R-凭证 env 化(与 P08 交接)**:compose 注入 `SURREAL_USER/PASS` 要求 `store.py:100-101` 的 `user/password` 从函数默认改读 `os.environ.get`(当前仅默认 `root/root`)。本枢纽在 `.env.example`/compose 标出钩子,**实际改 store 构造函数归安全枢纽**;在此之前 compose 的 SurrealDB 仍是 `root/root`(本地可接受,暴露不可)。
- **R-Hermes 容器化(需人工确认)**:Hermes 是底座(非可替换 LLM 网关,见 MEMORY),其镜像/挂载方式由 Hermes 提供。compose 中 `hermes` 服务为占位;落地前需确认 Hermes 官方容器化方案,或在 compose 中只起 surreal+backend+frontend、Hermes 用宿主已跑的 :8642/:8643(`llm.py:12/14` 经 env 指向宿主)。
- **R-VITE 构建期注入**:`VITE_API_BASE` 是**构建期**编译进产物(A2 注),同一份镜像不能运行期换 base;若需"一镜像多环境",要改运行期注入(`window.__ENV__`),**需人工确认**部署形态后决定。
- **R-真库 CI(需人工确认)**:部分后端测试需真 SurrealDB(`tests/conftest.py` 的夹具形态决定),CI service 容器的启动/健康探针需按实测调通;纯内存 World 测试不受影响。
- **R-依赖版本**:`requirements`/compose 镜像 tag 的精确版本**必须对实测核验**(红线:版本以二进制/`pip show`/`surreal version` 为准),本文占位版本一律视为 **需人工确认**。
- **交付前提**:测试 + CI 是"交付他人/团队协作"的硬前提(03 §9 明确:单人本地手测可接受,交付他人则 Docker/CI/前端测试必要)。若 scribe3 维持"永久单机单用户",C/B 组优先级可降——但本枢纽的目标场景正是"推进到可交付"。

---

## 7. 闭环问题清单

| 编号 | 问题(出处) | 本枢纽处置 | 闭环 |
|---|---|---|---|
| **P09** | 无 React ErrorBoundary,任一异常白屏(`main.jsx:4`) | A1:`ErrorBoundary.jsx` + `main.jsx` 包裹;B-TDD 步1 | ✓ |
| **P10** | `BASE` 硬编码 `:3321`(`api.js:2`) | A2(a):`import.meta.env.VITE_API_BASE`;TDD 步3 | ✓ |
| **P11** | 前端零自动化测试 | B1:vitest + 关键路径(ProposalParser/SSE/TipTap/ErrorBoundary/api);`package.json` 加 `test` | ✓ |
| **P12** | 无 Dockerfile/CI/requirements | C1(Dockerfile×2 + compose)+ C2(Actions);TDD 步11-12 | ✓ |
| **P25** | 端点零存在性/范围校验,假成功(`app.py:81/102/128/154/182/189`,`store.py:259`) | A3:`Query(ge=1)` + `store.exists` + `HTTPException(404)`;TDD 步6-7 | ✓ |
| **P30** | MCP `setup_store(db="main")` 硬编码(`mcp.py:259`) | D1:`SCRIBE3_WORK`/参数注入;TDD 步14 | ✓ |
| **P35** | 无 `.env.example` | C3:后端+前端两份,变量带 file:line 溯源 | ✓ |
| **P36** | 无生产部署说明,前端硬编码使生产不可行 | A2(BASE 外置)+ C1(compose/Dockerfile)+ 部署经 compose 文档化 | ✓ |
| **P37** | `llm.py` 重试/SSE 无单测(`llm.py:41-105`) | B2:`test_llm.py` + `respx`(5xx重试/4xx不重试/SSE解析);TDD 步8 | ✓ |
| **P46** | 原生 `alert`/`confirm` 阻塞(`Library.jsx:18`,`CodexView.jsx:84`) | A4:`Toast.jsx`(toast + Promise confirm);TDD 步5 | ✓ |
| **P47** | 模态无 focus trap/aria(`shell.jsx`,`CommandPalette.jsx`) | A5:`Modal.jsx`(`role=dialog`+`aria-modal`+focus trap+Esc+焦点归还);TDD 步5 | ✓ |
| **P48** | 无 `requirements.txt`/`pyproject.toml` | C4:`requirements.txt`/`requirements-dev.txt` 或 `pyproject.toml` | ✓ |
| **P49** | 迁移无"已应用版本"表、无回滚(`store.py:115`) | C5:`_migration` 表 + 按版本跳过;TDD 步13 | ✓ |

**全部 13 项闭环**:P09✓ P10✓ P11✓ P12✓ P25✓ P30✓ P35✓ P36✓ P37✓ P46✓ P47✓ P48✓ P49✓

> 跨枢纽交接(本枢纽给钩子、不在此实现):**P22**(CORS 收紧)、**P08**(SurrealDB 凭证 env 化)归安全枢纽 F;**P04/P38**(数据获取缓存/React Query)归性能枢纽。标 **需人工确认**项:前端 ProposalParser/TipTap helper 的具体文件位置、Hermes 容器化方式、依赖精确版本、CI 真库探针、a11y 拖拽键盘交互细节。
