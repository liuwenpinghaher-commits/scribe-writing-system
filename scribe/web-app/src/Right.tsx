import { useRef, useState } from "react";
import { Stethoscope, Send } from "lucide-react";
import { api } from "./api";
import { Btn, State, errMsg, useData, useToast } from "./common";

type Tab = "bible" | "foreshadow" | "flags" | "material" | "pulse";

export function Right({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  return (
    <>
      <Insights work={work} rev={rev} />
      <Sidebar work={work} rev={rev} />
      <Chat work={work} bump={bump} />
    </>
  );
}

function Insights({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.insights(work), [work, rev]);
  const toast = useToast();
  const act = async (id: string, a: "ack" | "dismiss") => { await api.actInsight(work, id, a); reload(); };
  const intentional = async (id: string) => {
    await api.actInsight(work, id, "dismiss");
    await api.pref(work, "intentional", "+").catch(() => {}); // "这是故意的"→品味回流
    toast("已记:这是故意的"); reload();
  };
  const review = async () => { const r = await api.review(work); toast(`体检完成,新增 ${r.new_insights} 条札记`); reload(); };
  return (
    <>
      <div className="row end" style={{ justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>主编札记</h2>
        <Btn onClick={review} variant="ghost" className="sm"><Stethoscope size={14} /> 全文体检</Btn>
      </div>
      <State loading={loading} error={error} empty={!data?.length} emptyText="暂无札记。点「全文体检」让主编主动揪问题。" onRetry={reload}>
        {data?.map((x) => {
          const c = x.severity === "critical" ? "var(--danger)" : x.severity === "major" ? "var(--warn)" : "var(--accent)";
          return (
            <div key={x.id} className="card" style={{ borderLeft: `3px solid ${c}` }}>
              <div>{x.summary}</div>
              {x.suggested_action && <div className="muted small">建议:{x.suggested_action}</div>}
              <div className="row" style={{ marginTop: 6, flexWrap: "wrap" }}>
                <Btn onClick={() => act(x.id, "ack")} variant="ghost" className="sm">知道了</Btn>
                <Btn onClick={() => intentional(x.id)} variant="ghost" className="sm">这是故意的</Btn>
                <Btn onClick={() => act(x.id, "dismiss")} variant="ghost" className="sm">忽略</Btn>
              </div>
            </div>
          );
        })}
      </State>
    </>
  );
}

function Sidebar({ work, rev }: { work: string; rev: number }) {
  const [tab, setTab] = useState<Tab>("bible");
  const [local, setLocal] = useState(0); // 裁决后本地刷新
  const fo = useData(() => api.foreshadows(work), [work, rev, local]);
  const fl = useData(() => api.flags(work), [work, rev, local]);
  const toast = useToast();
  const bump = () => setLocal((n) => n + 1);
  const onFore = async (fid: string, a: "trigger" | "pay" | "abandon") => {
    try { await api.advanceForeshadow(work, fid, a); toast("伏笔已推进"); bump(); }
    catch (e) { toast(errMsg(e), "err"); }
  };
  const onFlag = async (fid: string, a: "confirm" | "dismiss" | "fix") => {
    await api.resolveFlag(work, fid, a); toast(a === "dismiss" ? "已标记误报" : "已确认"); bump();
  };
  const bible = useData(async () => {
    const [chs, st] = await Promise.all([api.characters(work), api.settings(work)]);
    const desc = (c?: string) => { try { return JSON.parse(c || "{}").description || ""; } catch { return ""; } };
    return [
      ...chs.map((c) => ({ kind: "char" as const, k: "角色", name: c.name, body: c.motivation || "", type: "" })),
      ...st.map((s) => ({ kind: "set" as const, k: s.type ?? "设定", name: s.name, body: desc(s.content), type: s.type ?? "设定" })),
    ];
  }, [work, rev]);
  const tabs: [Tab, string, number][] = [
    ["bible", "设定圣经", 0], ["foreshadow", "伏笔", fo.data?.length ?? 0],
    ["flags", "一致性", fl.data?.length ?? 0], ["material", "素材", 0], ["pulse", "脉络", 0],
  ];
  return (
    <>
      <div className="tabs" role="tablist" aria-label="设定与门槛">
        {tabs.map(([t, label, n]) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}>
            {label}{n > 0 && <span className={"dot " + (t === "flags" ? "note" : "opt")}>{n}</span>}
          </button>
        ))}
      </div>
      <div style={{ maxHeight: "32vh", overflow: "auto" }}>
        {tab === "foreshadow" && (
          <State loading={fo.loading} error={fo.error} empty={!fo.data?.length} emptyText="暂无未了结伏笔" onRetry={fo.reload}>
            {fo.data?.map((x) => (
              <div key={x.id} className="card">
                <div><span className="badge">{x.state}</span> {x.summary}</div>
                <div className="row" style={{ marginTop: 6, flexWrap: "wrap" }}>
                  {x.state === "planted" && <Btn onClick={() => onFore(x.id, "trigger")} variant="ghost" className="sm">触发</Btn>}
                  {x.state === "triggered" && <Btn onClick={() => onFore(x.id, "pay")} variant="ghost" className="sm">回收</Btn>}
                  <Btn onClick={() => onFore(x.id, "abandon")} variant="ghost" className="sm">放弃</Btn>
                </div>
              </div>
            ))}
          </State>
        )}
        {tab === "flags" && (
          <State loading={fl.loading} error={fl.error} empty={!fl.data?.length} emptyText="无一致性问题 ✓" onRetry={fl.reload}>
            {fl.data?.map((x) => (
              <div key={x.id} className="card">
                <div><span className="badge" style={{ background: "#3a2330", color: "var(--warn)" }}>{x.error_class}</span> {x.detail}</div>
                <div className="row" style={{ marginTop: 6, flexWrap: "wrap" }}>
                  <Btn onClick={() => onFlag(x.id, "confirm")} variant="ghost" className="sm">确认真错</Btn>
                  <Btn onClick={() => onFlag(x.id, "fix")} variant="ghost" className="sm">已修</Btn>
                  <Btn onClick={() => onFlag(x.id, "dismiss")} variant="ghost" className="sm">误报</Btn>
                </div>
              </div>
            ))}
          </State>
        )}
        {tab === "material" && <Materials work={work} />}
        {tab === "pulse" && <Pulse work={work} rev={rev} />}
        {tab === "bible" && (
          <>
            <BibleAdd work={work} onAdded={bible.reload} />
            <State loading={bible.loading} error={bible.error} empty={!bible.data?.length} emptyText="还没有设定/角色,在上方添加" onRetry={bible.reload}>
              {bible.data?.map((x, i) => (
                <BibleItem key={i} work={work} item={x} onSaved={bible.reload} />
              ))}
            </State>
          </>
        )}
      </div>
    </>
  );
}


function BibleItem({ work, item, onSaved }: {
  work: string; item: { kind: "char" | "set"; k: string; name: string; body: string; type: string };
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(item.body);
  const [impact, setImpact] = useState<{ seq: number; title?: string; snippet: string }[] | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);
  const toast = useToast();
  const save = async () => {
    if (item.kind === "char") await api.addCharacter(work, item.name, body.trim());
    else await api.addSetting(work, item.name, item.type || "设定", body.trim());
    setOpen(false); toast("已保存"); onSaved();
  };
  const loadImpact = async () => {
    if (impact) { setImpact(null); return; }
    setLoadingImpact(true);
    try { setImpact(await api.impact(work, item.name)); } finally { setLoadingImpact(false); }
  };
  const jump = (seq: number) => { location.hash = `#/work/${work}/ch/${seq}`; };
  return (
    <div className="card">
      <button className="ghost sm" style={{ border: 0, padding: 0, width: "100%", textAlign: "left" }}
        onClick={() => { setBody(item.body); setOpen((o) => !o); }} aria-expanded={open}>
        <span className="badge">{item.k}</span> {item.name}
        {item.body && !open && <span className="muted small"> · {item.body.slice(0, 18)}{item.body.length > 18 ? "…" : ""}</span>}
      </button>
      {open && (
        <div style={{ marginTop: 6 }}>
          <textarea rows={2} value={body} onChange={(e) => setBody(e.target.value)}
            placeholder={item.kind === "char" ? "动机/性格…" : "设定描述…"} />
          <div className="row" style={{ marginTop: 4, flexWrap: "wrap" }}>
            <Btn onClick={save} variant="ghost" className="sm">保存</Btn>
            <Btn onClick={loadImpact} variant="ghost" className="sm">
              {item.kind === "char" ? "出场时间线" : "影响章节"}{impact ? " ▾" : " ▸"}
            </Btn>
          </div>
          {loadingImpact && <div className="muted small" style={{ marginTop: 4 }}>查找中…</div>}
          {impact && (
            <div style={{ marginTop: 4 }}>
              {impact.length === 0 && <div className="muted small">暂无章节引用「{item.name}」</div>}
              {impact.map((c) => (
                <button key={c.seq} className="card clickable" style={{ padding: "6px 8px" }}
                  onClick={() => jump(c.seq)} title="跳到该章">
                  <span className="badge">第 {c.seq} 章</span> {c.title || "无题"}
                  <div className="muted small">{c.snippet}…</div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Pulse({ work, rev }: { work: string; rev: number }) {
  const mem = useData(() => api.memory(work), [work, rev]);
  const tl = useData(() => api.timeline(work), [work, rev]);
  const cost = useData(() => api.cost(work), [work, rev]);
  return (
    <>
      {cost.data && (
        <div className="card"><span className="muted small">AI 用量:{cost.data.calls} 次 · {cost.data.tokens.toLocaleString()} token · ${cost.data.cost_usd}</span></div>
      )}
      <h3>全书主线记忆</h3>
      <State loading={mem.loading} error={mem.error} empty={!mem.data?.global && !mem.data?.chapters?.length} emptyText="写几章后自动沉淀" onRetry={mem.reload}>
        {mem.data?.global && <div className="card"><div className="seg">{mem.data.global}</div></div>}
        {mem.data?.chapters?.slice(-6).map((c) => (
          <div key={c.seq} className="card" style={{ padding: "6px 8px" }}>
            <span className="badge">第{c.seq}章</span> <span className="small">{c.summary_text}</span>
          </div>
        ))}
      </State>
      <h3>时间线</h3>
      <State loading={tl.loading} error={tl.error} empty={!tl.data?.length} emptyText="暂无事件" onRetry={tl.reload}>
        {tl.data?.slice(-12).map((t, i) => (
          <div key={i} className="muted small" style={{ padding: "2px 0" }}>第{t.chapter_seq}章 · {t.description}</div>
        ))}
      </State>
    </>
  );
}

function Materials({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.materials(work), [work]);
  const [text, setText] = useState("");
  const toast = useToast();
  const add = async () => { if (!text.trim()) return; await api.addMaterial(work, text.trim()); setText(""); toast("素材已存"); reload(); };
  const proc = async (mid: string) => { await api.processMaterial(work, mid); toast("已提炼摘要+标签"); reload(); };
  const distill = async (mid: string) => { await api.distillMaterial(work, mid, "setting"); toast("已提炼为设定"); reload(); };
  const del = async (mid: string) => { await api.deleteMaterial(work, mid); reload(); };
  return (
    <>
      <div className="row" style={{ marginBottom: 8 }}>
        <textarea rows={2} aria-label="新素材" value={text} placeholder="粘贴/记下素材(灵感、设定、句子)…"
          onChange={(e) => setText(e.target.value)} />
        <Btn onClick={add} variant="ghost" className="sm">存</Btn>
      </div>
      <State loading={loading} error={error} empty={!data?.length} emptyText="还没有素材" onRetry={reload}>
        {data?.map((m) => {
          let txt = ""; try { txt = JSON.parse(m.content || "{}").text || ""; } catch { /* */ }
          let tags: string[] = []; try { tags = JSON.parse(m.tags || "[]"); } catch { /* */ }
          return (
            <div key={m.id} className="card">
              <div className="small">{txt.slice(0, 70)}{txt.length > 70 ? "…" : ""}</div>
              {tags.length > 0 && <div className="muted small">{tags.map((t, i) => <span key={i} className="badge" style={{ marginRight: 4 }}>{t}</span>)}</div>}
              <div className="row" style={{ marginTop: 4, flexWrap: "wrap" }}>
                {m.status !== "processed" && <Btn onClick={() => proc(m.id)} variant="ghost" className="sm">提炼摘要</Btn>}
                <Btn onClick={() => distill(m.id)} variant="ghost" className="sm">→设定</Btn>
                <Btn onClick={() => del(m.id)} variant="ghost" className="sm">删</Btn>
              </div>
            </div>
          );
        })}
      </State>
    </>
  );
}

function BibleAdd({ work, onAdded }: { work: string; onAdded: () => void }) {
  const [kind, setKind] = useState<"char" | "set">("char");
  const [name, setName] = useState("");
  const toast = useToast();
  const add = async () => {
    const n = name.trim(); if (!n) return;
    if (kind === "char") await api.addCharacter(work, n); else await api.addSetting(work, n);
    setName(""); toast(kind === "char" ? "已加角色" : "已加设定"); onAdded();
  };
  return (
    <div className="row" style={{ marginBottom: 8 }}>
      <select value={kind} onChange={(e) => setKind(e.target.value as "char" | "set")}
        aria-label="类型" style={{ width: 76, flex: "0 0 auto" }}>
        <option value="char">角色</option><option value="set">设定</option>
      </select>
      <input aria-label="名称" value={name} placeholder={kind === "char" ? "角色名…" : "设定名…"}
        onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
      <Btn onClick={add} variant="ghost" className="sm">加</Btn>
    </div>
  );
}

interface Card { type: string; title: string; options?: string[] }
// 从主编回复抽取 ```scribe-card JSON 块 → {正文文本, 卡片[]}
function parseCards(text: string): { text: string; cards: Card[] } {
  const cards: Card[] = [];
  const clean = text.replace(/```scribe-card\s*([\s\S]*?)```/g, (_m, body) => {
    try { const c = JSON.parse(body.trim()); if (c && c.title) cards.push(c); } catch { /* */ }
    return "";
  }).trim();
  return { text: clean, cards };
}

function ChiefCard({ card, onPick }: { card: Card; onPick: (opt: string) => void }) {
  const color = card.type === "hard_conflict" ? "var(--danger)" : card.type === "suggestion" ? "var(--warn)" : "var(--accent)";
  const icon = card.type === "hard_conflict" ? "⚠ 硬冲突" : card.type === "suggestion" ? "💡 建议" : "⌖ 待定夺";
  return (
    <div className="card" style={{ borderLeft: `3px solid ${color}` }}>
      <b style={{ color }}>{icon}</b> <span>{card.title}</span>
      {card.options && card.options.length > 0 && (
        <div className="row" style={{ marginTop: 6, flexWrap: "wrap" }}>
          {card.options.map((o, i) => <Btn key={i} variant="ghost" className="sm" onClick={() => onPick(o)}>{o}</Btn>)}
        </div>
      )}
    </div>
  );
}

function Chat({ work, bump }: { work: string; bump: () => void }) {
  const [msgs, setMsgs] = useState<{ who: "me" | "ai"; text: string; cards?: Card[] }[]>([]);
  const [input, setInput] = useState(""); const [busy, setBusy] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const send = async (raw?: string) => {
    const m = (raw ?? input).trim(); if (!m || busy) return;
    setInput(""); setMsgs((x) => [...x, { who: "me", text: m }]); setBusy(true);
    try {
      const r = await api.chat(`(当前书 work_id=${work})${m}`);
      const { text, cards } = parseCards(r.content);
      setMsgs((x) => [...x, { who: "ai", text: text || "(见下方卡片)", cards }]);
    } catch (e) {
      setMsgs((x) => [...x, { who: "ai", text: "出错:" + errMsg(e) }]);
    } finally {
      setBusy(false); bump();
      setTimeout(() => boxRef.current?.scrollTo(0, 1e9), 0);
    }
  };
  return (
    <>
      <h3>主编对话</h3>
      <div className="chat">
        <div className="msgs" ref={boxRef} aria-live="polite">
          {msgs.length === 0 && <div className="empty">和主编(火山 doubao)聊聊这本书。遇决策/冲突会给可操作卡片。</div>}
          {msgs.map((m, i) => (
            <div key={i}>
              <div className={"bub " + m.who}>{m.text}</div>
              {m.cards?.map((c, j) => <ChiefCard key={j} card={c} onPick={(o) => send(`我选:${o}`)} />)}
            </div>
          ))}
          {busy && <div className="bub ai thinking">主编思考中…</div>}
        </div>
        <div className="row" style={{ marginTop: 6 }}>
          <input aria-label="对主编说" value={input} placeholder="说点什么…" disabled={busy}
            onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") send(); }} />
          <Btn onClick={() => send()}><Send size={15} /> 发</Btn>
        </div>
      </div>
    </>
  );
}
