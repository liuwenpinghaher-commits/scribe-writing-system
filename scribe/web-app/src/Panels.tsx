import { useState } from "react";
import { api } from "./api";
import type { AgentSkill } from "./api";
import { Btn, State, useData, useToast } from "./common";

// ── 质量计分卡(GET /quality)──────────────────────────────
export function QualityCard({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.quality(work), [work, rev]);
  return (
    <>
      <div className="row end" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>质量计分卡</h3>
        <Btn onClick={reload} variant="ghost" className="sm">刷新</Btn>
      </div>
      <State loading={loading} error={error} empty={!data} emptyText="暂无数据" onRetry={reload}>
        {data && (
          <>
            <div className="qgrid">
              <Metric label="规模" value={`${data.chapters} 章`} sub={`${data.words.toLocaleString()} 字`} />
              <Metric label="一致性" value={data.consistency.score.toFixed(2)}
                sub={`${data.consistency.open_flags} 未决`} tone={data.consistency.score >= 0.8 ? "ok" : data.consistency.score >= 0.5 ? "warn" : "danger"} />
              <Metric label="伏笔回收" value={`${Math.round(data.foreshadow.payoff_rate * 100)}%`}
                sub={`${data.foreshadow.paid}/${data.foreshadow.planted}`} tone={data.foreshadow.payoff_rate >= 0.7 ? "ok" : "warn"} />
              <Metric label="AI腔密度" value={data.avg_slop_density.toFixed(2)}
                sub="越低越好" tone={data.avg_slop_density <= 1 ? "ok" : data.avg_slop_density <= 2 ? "warn" : "danger"} />
            </div>
            <div className="card" style={{ marginTop: 8 }}>
              <span className="muted small tnum">AI 用量:{data.cost.calls} 次 · {data.cost.tokens.toLocaleString()} token · ${data.cost.cost_usd}</span>
            </div>
            {data.weakest_chapters.length > 0 && (
              <>
                <div className="muted small" style={{ margin: "8px 0 4px", fontWeight: 600 }}>最弱章(AI腔最高)</div>
                {data.weakest_chapters.map((c) => (
                  <button key={c.seq} className="card clickable" style={{ padding: "6px 8px" }}
                    onClick={() => { location.hash = `#/work/${work}/ch/${c.seq}`; }} title="跳到该章">
                    <span className="badge">第 {c.seq} 章</span>
                    <span className="muted small tnum"> · AI腔 {c.slop_density.toFixed(2)} · {c.open_flags} 问题 · {c.words.toLocaleString()} 字</span>
                  </button>
                ))}
              </>
            )}
          </>
        )}
      </State>
    </>
  );
}

function Metric({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "ok" | "warn" | "danger" }) {
  const color = tone ? `var(--${tone === "danger" ? "danger" : tone})` : "var(--text-primary)";
  return (
    <div className="card metric" style={{ margin: 0 }}>
      <div className="muted small">{label}</div>
      <div className="tnum" style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      {sub && <div className="muted small">{sub}</div>}
    </div>
  );
}

// ── 关系图(GET /relations · 文本图)────────────────────────
// ponytail: 先用可读列表「A —关系→ B(第N章起)」,不上 SVG 力导向图;需要可视化再升级。
export function Relations({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.relations(work), [work, rev]);
  return (
    <State loading={loading} error={error} empty={!data?.length} emptyText="暂无实体关系(写几章后由摄入抽取)" onRetry={reload}>
      {data?.map((r) => (
        <div key={r.id} className="card" style={{ padding: "6px 8px" }}>
          <span className="t">{r.src_entity}</span>
          <span className="muted"> —{r.relation}→ </span>
          <span className="t">{r.dst_entity}</span>
          {r.valid_from_chapter != null && (
            <span className="muted small"> · 第{r.valid_from_chapter}章起{r.valid_to_chapter != null ? `→第${r.valid_to_chapter}章止` : ""}</span>
          )}
        </div>
      ))}
    </State>
  );
}

// ── 角色状态轨迹(GET /characters/{name}/states)───────────
export function CharStates({ work, name }: { work: string; name: string }) {
  const { data, loading, error, reload } = useData(() => api.charStates(work, name), [work, name]);
  return (
    <State loading={loading} error={error} empty={!data?.length} emptyText="暂无状态记录" onRetry={reload}>
      <div style={{ borderLeft: "2px solid var(--border)", paddingLeft: 8, marginTop: 4 }}>
        {data?.map((s) => (
          <div key={s.id} style={{ padding: "2px 0" }}>
            <span className="badge">第{s.chapter_seq}章</span>
            {s.change_type && <span className="muted small"> [{s.change_type}]</span>}
            <span className="small"> {s.state_desc}</span>
          </div>
        ))}
      </div>
    </State>
  );
}

// ── 讨论线程(GET /threads + resolve)──────────────────────
export function Threads({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.threads(work), [work, rev]);
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const resolve = async (tid: string) => { await api.resolveThread(work, tid); toast("议题已归档"); reload(); };
  const count = data?.length ?? 0;
  return (
    <div style={{ marginTop: 10 }}>
      <button className="ghost sm" onClick={() => setOpen((o) => !o)} aria-expanded={open} style={{ width: "100%", textAlign: "left" }}>
        历史议题 {count > 0 ? `(${count})` : ""} {open ? "▾" : "▸"}
      </button>
      {open && (
        <State loading={loading} error={error} empty={!count} emptyText="暂无讨论线程" onRetry={reload}>
          {data?.map((t) => {
            let n = 0; try { n = JSON.parse(t.messages || "[]").length; } catch { /* */ }
            return (
              <div key={t.id} className="card" style={{ padding: "6px 8px" }}>
                <div className="small"><span className="badge">{t.status}</span> {t.topic}</div>
                <div className="row end" style={{ justifyContent: "space-between", marginTop: 4 }}>
                  <span className="muted small">{t.trigger} · {n} 条对话</span>
                  {t.status === "open" && <Btn onClick={() => resolve(t.id)} variant="ghost" className="sm">归档</Btn>}
                </div>
              </div>
            );
          })}
        </State>
      )}
    </div>
  );
}

// ── 跨会话记忆 + 自我优化技能(须人审批门)────────────────
const NS: { key: string; label: string }[] = [
  { key: "", label: "全部" }, { key: "semantic", label: "语义" }, { key: "episodic", label: "情节" },
  { key: "session", label: "会话" }, { key: "working", label: "工作" }, { key: "meta", label: "元" },
];
const SKILL_STATUS: Record<string, string> = { proposed: "待审批", approved: "已批准", active: "启用中", retired: "已退役" };

export function AgentPanel({ work, rev }: { work: string; rev: number }) {
  const [ns, setNs] = useState("");
  const mem = useData(() => api.agentMemory(work, ns || undefined), [work, rev, ns]);
  const skills = useData(() => api.agentSkills(work), [work, rev]);
  const toast = useToast();
  const [skillName, setSkillName] = useState("");

  const propose = async () => {
    if (!skillName.trim()) return;
    await api.proposeSkill(work, skillName.trim()); setSkillName(""); toast("已提议技能(待你审批)"); skills.reload();
  };
  const act = async (s: AgentSkill, action: "approve" | "activate" | "retire") => {
    await api.actSkill(work, s.id, action); toast(`技能已${action === "approve" ? "批准" : action === "activate" ? "启用" : "退役"}`); skills.reload();
  };

  return (
    <>
      <h3 style={{ marginTop: 4 }}>跨会话记忆</h3>
      <div className="tabs" role="tablist" aria-label="记忆命名空间">
        {NS.map((n) => (
          <button key={n.key} role="tab" aria-selected={ns === n.key} className="sm" onClick={() => setNs(n.key)}>{n.label}</button>
        ))}
      </div>
      <State loading={mem.loading} error={mem.error} empty={!mem.data?.length}
        emptyText="暂无记忆(置信 ≥0.8 才入库)" onRetry={mem.reload}>
        {mem.data?.map((m) => {
          let v = m.value; try { const o = JSON.parse(m.value); v = typeof o === "object" ? JSON.stringify(o) : String(o); } catch { /* */ }
          return (
            <div key={m.id} className="card" style={{ padding: "6px 8px" }}>
              <div className="small"><span className="badge">{m.namespace}</span> <b>{m.key}</b></div>
              <div className="muted small" style={{ marginTop: 2 }}>{v.slice(0, 80)}{v.length > 80 ? "…" : ""}</div>
              <div className="muted small tnum">置信 {m.confidence.toFixed(2)}{m.work_id ? " · 本书" : " · 跨书"}</div>
            </div>
          );
        })}
      </State>

      <h3>自我优化技能 <span className="muted small" style={{ textTransform: "none", letterSpacing: 0 }}>· 须你审批才生效</span></h3>
      <div className="row" style={{ marginBottom: 8 }}>
        <input aria-label="提议技能名" value={skillName} placeholder="提议一个技能(如:卷尾自动摘要)…"
          onChange={(e) => setSkillName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") propose(); }} />
        <Btn onClick={propose} variant="ghost" className="sm">提议</Btn>
      </div>
      <State loading={skills.loading} error={skills.error} empty={!skills.data?.length}
        emptyText="暂无技能。AI 提议的技能会停在「待审批」,由你放行。" onRetry={skills.reload}>
        {skills.data?.map((s) => {
          const approved = s.approved_by_human === 1;
          const tone = s.status === "active" ? "var(--ok)" : s.status === "proposed" ? "var(--warn)" : "var(--accent)";
          return (
            <div key={s.id} className="card" style={{ borderLeft: `3px solid ${tone}` }}>
              <div className="small">
                <b>{s.name}</b>
                <span className="badge" style={{ marginLeft: 6 }}>{SKILL_STATUS[s.status] || s.status}</span>
                {!approved && <span className="badge" style={{ marginLeft: 4, color: "var(--warn)", background: "color-mix(in srgb, var(--warn) 16%, transparent)" }}>未审批</span>}
              </div>
              <div className="row" style={{ marginTop: 6, flexWrap: "wrap" }}>
                {s.status === "proposed" && <Btn onClick={() => act(s, "approve")} className="sm">批准</Btn>}
                {(s.status === "proposed" || s.status === "approved") && <Btn onClick={() => act(s, "activate")} variant="ghost" className="sm">启用</Btn>}
                {s.status !== "retired" && <Btn onClick={() => act(s, "retire")} variant="ghost" className="sm">退役</Btn>}
              </div>
            </div>
          );
        })}
      </State>
    </>
  );
}
