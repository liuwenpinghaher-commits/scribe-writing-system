/**
 * ForeshadowDetailPage.tsx — 承诺线全页详情(点击进入,占满中区,不再底部挤一条)。
 * 富字段(承诺/类型/想要效果/读者预知/回收效果/关联实体)+ 节点编辑器(Promise→Progress→Payoff,
 * 每节点写 guidance/隐蔽度/效果)+ 健康校验(≥2铺垫/悬空/超期/红鲱鱼待澄清)+ 推进/回收/放弃 + 跳转。
 */
import { useState } from "react";
import { ChevronLeft, Plus, X } from "lucide-react";
import { api, type ForeshadowStatus } from "@/api";
import { useData, useToast } from "@/common";
import { DetailHeader, Section, Row, Block, InlineText, Val } from "@/components/detail";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TYPES, EFFECTS, KINDS, KIND_LABEL, colorOf } from "./foreshadowConst";

function Chips({ value, options, onPick, colored }: {
  value: string; options: readonly string[]; onPick: (v: string) => void; colored?: boolean;
}) {
  return (
    <div className="flex gap-1 flex-wrap py-1">
      {options.map((t) => {
        const on = value === t;
        return (
          <button key={t} onClick={() => onPick(t)}
            className={`text-[11px] px-2 py-0.5 rounded-md border transition-colors ${on ? (colored ? "text-white" : "bg-primary text-primary-foreground border-primary") : "text-muted-foreground border-border hover:border-foreground"}`}
            style={on && colored ? { background: colorOf(t), borderColor: colorOf(t) } : undefined}>{t}</button>
        );
      })}
    </div>
  );
}

/** 健康校验:从一条承诺线推出写作护栏提示 */
function healthOf(r: ForeshadowStatus): { ok: boolean; text: string }[] {
  const beats = r.beats ?? [];
  const setups = beats.filter((b) => b.kind === "plant" || b.kind === "reinforce").length || (r.echoes?.length ? r.echoes.length + 1 : 1);
  const paid = r.state === "paid";
  const out: { ok: boolean; text: string }[] = [];
  if (paid) out.push({ ok: setups >= 2, text: setups >= 2 ? `回收前有 ${setups} 处铺垫(达标)` : `回收只有 ${setups} 处铺垫(建议 ≥2,三次法则更佳)` });
  else out.push({ ok: false, text: "尚未回收" });
  if (r.overdue) out.push({ ok: false, text: "⚠ 超期未回收(开太久)" });
  if (!paid && r.state !== "abandoned" && !(beats.some((b) => b.kind === "payoff"))) out.push({ ok: false, text: "悬空:还没有回收计划(加一个 payoff 节点)" });
  if (r.ftype === "红鲱鱼" && !beats.some((b) => b.kind === "twist" || b.kind === "misdirect")) out.push({ ok: false, text: "红鲱鱼:还没安排澄清/转折,别让假线索烂尾" });
  return out;
}

export function ForeshadowDetailPage({ work, fid, nowCh, onBack }: {
  work: string; fid: string; nowCh: number; onBack: () => void;
}) {
  const fs = useData(() => api.foreshadowsStatus(work), [work, fid]);
  const row = fs.data?.find((r) => r.id === fid);
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  // 富字段本地态(行加载后初始化一次)
  const [f, setF] = useState<Record<string, string>>({});
  const [aud, setAud] = useState(false);
  const [loaded, setLoaded] = useState(false);
  if (row && !loaded) {
    setF({ summary: row.summary || "", promise: row.promise || "", ftype: row.ftype || "伏笔",
      intended_effect: row.intended_effect || "", payoff_effect: row.payoff_effect || "", links: (row.links || []).join("、") });
    setAud(!!row.audience_knows); setLoaded(true);
  }
  // 节点编辑
  const [bCh, setBCh] = useState(String(nowCh));
  const [bKind, setBKind] = useState("reinforce");
  const [bGuide, setBGuide] = useState("");
  const [bSub, setBSub] = useState("");
  const [bEff, setBEff] = useState("");
  const [opCh, setOpCh] = useState(String(nowCh));

  if (!row) return <div className="p-6 text-sm text-muted-foreground">承诺线不存在或已删除。<button className="underline ml-1" onClick={onBack}>返回</button></div>;

  const opChN = Number(opCh) || nowCh;
  const dirty = loaded && (f.summary !== (row.summary || "") || f.promise !== (row.promise || "") || f.ftype !== (row.ftype || "伏笔")
    || f.intended_effect !== (row.intended_effect || "") || f.payoff_effect !== (row.payoff_effect || "")
    || f.links !== (row.links || []).join("、") || aud !== !!row.audience_knows);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF((o) => ({ ...o, [k]: e.target.value }));
  const act = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try { await fn(); toast(msg); fs.reload(); } catch (e) { toast(String(e)); } finally { setBusy(false); }
  };
  const saveFields = () => act(() => api.editForeshadow(work, fid, {
    summary: f.summary, promise: f.promise, ftype: f.ftype, intended_effect: f.intended_effect,
    audience_knows: aud, payoff_effect: f.payoff_effect,
    links: f.links.split(/[，,、\s]+/).map((s) => s.trim()).filter(Boolean),
  }), "承诺已更新");
  const addBeat = () => {
    const ch = Number(bCh); if (!ch) { toast("填章号"); return; }
    act(() => api.addForeshadowBeat(work, fid, { chapter: ch, kind: bKind, guidance: bGuide.trim(), subtlety: Number(bSub) || 0, effect: bEff.trim() }), "已加节点")
      .then(() => { setBGuide(""); setBEff(""); setBSub(""); });
  };
  const jump = (ch?: number | null) => { if (ch) location.hash = `#/work/${work}/ch/${ch}`; };
  const beats = [...(row.beats ?? [])].sort((a, b) => a.chapter - b.chapter);
  const open = row.state !== "paid" && row.state !== "abandoned";

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 h-11 shrink-0 px-3 border-b border-border">
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={onBack}><ChevronLeft size={14} />返回</Button>
        <span className="text-xs text-muted-foreground">承诺线详情</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl px-5 py-4 flex flex-col gap-0.5">
          <DetailHeader kicker={`承诺线 · ${f.ftype || "伏笔"}`}>
            <InlineText big v={f.summary || ""} on={set("summary")} ph="简称(泳道名)" />
          </DetailHeader>

          <Section title="承诺" action={dirty ? <Button size="sm" className="h-6 text-[11px]" disabled={busy} onClick={saveFields}>保存承诺</Button> : undefined}>
            <Block label="对读者的承诺"><InlineText multiline v={f.promise || ""} on={set("promise")} ph="读者被引导期待什么(灵魂)" /></Block>
            <Row label="类型"><Chips value={f.ftype || "伏笔"} options={TYPES} colored onPick={(v) => setF((o) => ({ ...o, ftype: v }))} /></Row>
            <Row label="想要效果"><Chips value={f.intended_effect || ""} options={EFFECTS} onPick={(v) => setF((o) => ({ ...o, intended_effect: v }))} /></Row>
            <Row label="读者预知">
              <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
                <input type="checkbox" checked={aud} onChange={(e) => setAud(e.target.checked)} />
                <span className="text-muted-foreground">读者提前知道(=戏剧反讽:读者知、角色不知,Hitchcock 式悬念)</span>
              </label>
            </Row>
            <Block label="回收要达到的效果"><InlineText multiline v={f.payoff_effect || ""} on={set("payoff_effect")} ph="如:揭示时让读者重读前文细节而恍然" /></Block>
            <Row label="关联实体"><InlineText v={f.links || ""} on={set("links")} ph="角色/设定名,逗号分隔(写到 TA 时自动提醒本伏笔)" /></Row>
          </Section>

          <Section title="节点 · Promise→Progress→Payoff">
            {beats.length === 0 && <Val muted>还没有节点。埋设/强化/回收各是一个节点,每个写清"此处怎么写、达到什么效果"。</Val>}
            {beats.map((b, i) => (
              <div key={i} className="grid items-start gap-2 py-1" style={{ gridTemplateColumns: "76px 1fr", borderBottom: "1px solid color-mix(in srgb, var(--border) 55%, transparent)" }}>
                <button className="text-xs text-left text-foreground hover:text-primary pt-1" onClick={() => jump(b.chapter)} title="跳到该章">
                  <span className="font-semibold">{KIND_LABEL[b.kind] || b.kind}</span> 第{b.chapter}章
                </button>
                <div className="text-sm">
                  {b.guidance || <span className="text-muted-foreground/50">（无引导）</span>}
                  <span className="text-[11px] text-muted-foreground">{b.subtlety ? ` · 隐蔽度${b.subtlety}` : ""}{b.effect ? ` · 效果:${b.effect}` : ""}</span>
                </div>
              </div>
            ))}
            {/* 加节点 */}
            <div className="rounded-lg border border-border p-2.5 mt-2 flex flex-col gap-1.5 bg-muted/20">
              <div className="flex items-center gap-1.5 flex-wrap">
                {KINDS.map((k) => (
                  <button key={k.key} onClick={() => setBKind(k.key)}
                    className={`text-[11px] px-2 py-0.5 rounded-md border transition-colors ${bKind === k.key ? "bg-primary text-primary-foreground border-primary" : "text-muted-foreground border-border hover:border-foreground"}`}>{k.label}</button>
                ))}
                <span className="text-xs text-muted-foreground ml-1">第</span>
                <Input value={bCh} onChange={(e) => setBCh(e.target.value)} className="h-7 w-12 text-xs" />
                <span className="text-xs text-muted-foreground">章</span>
                {(bKind === "plant" || bKind === "reinforce") && <>
                  <span className="text-xs text-muted-foreground ml-1">隐蔽度</span>
                  <Input value={bSub} onChange={(e) => setBSub(e.target.value)} className="h-7 w-12 text-xs" placeholder="1-5" />
                </>}
              </div>
              <Input value={bGuide} onChange={(e) => setBGuide(e.target.value)} placeholder="此处具体怎么写(如:藏在渡叔擦灯的动作里,别点破)" className="h-7 text-xs" />
              <div className="flex items-center gap-1.5">
                <Input value={bEff} onChange={(e) => setBEff(e.target.value)} placeholder="想要的局部效果(如:读者起疑但说不出哪里不对)" className="h-7 text-xs flex-1" />
                <Button size="sm" className="h-7 text-xs gap-1" onClick={addBeat} disabled={busy}><Plus size={12} />加节点</Button>
              </div>
            </div>
          </Section>

          <Section title="健康校验">
            {healthOf(row).map((h, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs px-2 py-0.5">
                <span style={{ color: h.ok ? "var(--accent)" : "#dc2626" }}>{h.ok ? "✓" : "•"}</span>
                <span className={h.ok ? "text-muted-foreground" : "text-foreground"}>{h.text}</span>
              </div>
            ))}
          </Section>

          <Section title="进度 / 操作">
            <Row label="当前"><Val muted>
              埋第{row.chapter}章{row.echoes?.length ? ` · 强化${row.echoes.join("/")}` : ""}{row.payoff_chapter ? ` · 回收第${row.payoff_chapter}章` : ` · ${row.state}`}
            </Val></Row>
            <div className="flex items-center gap-1.5 px-2 pt-2 flex-wrap">
              <span className="text-xs text-muted-foreground">操作章</span>
              <Input value={opCh} onChange={(e) => setOpCh(e.target.value)} className="h-7 w-14 text-xs" />
              {open && <>
                <Button size="sm" variant="outline" className="h-7 text-xs" disabled={busy} onClick={() => act(() => api.addForeshadowEcho(work, fid, opChN), "已记进展")}>在此推进</Button>
                <Button size="sm" className="h-7 text-xs" disabled={busy} onClick={() => act(() => api.payoffForeshadow(work, fid, opChN), "已回收 ★")}>在此回收 ★</Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground" disabled={busy} onClick={() => act(() => api.advanceForeshadow(work, fid, "abandon"), "已放弃")}>放弃</Button>
              </>}
              <Button size="sm" variant="ghost" className="h-7 text-xs ml-auto" onClick={() => jump(row.chapter)}>跳到埋设章</Button>
            </div>
          </Section>
          <div className="h-6" />
        </div>
      </div>
    </div>
  );
}

/** 新建承诺线(全页表单,与详情同风格) */
export function ForeshadowCreatePage({ work, nowCh, onBack, onCreated }: {
  work: string; nowCh: number; onBack: () => void; onCreated: (id: string) => void;
}) {
  const [summary, setSummary] = useState("");
  const [promise, setPromise] = useState("");
  const [ftype, setFtype] = useState("伏笔");
  const [effect, setEffect] = useState("");
  const [aud, setAud] = useState(false);
  const [links, setLinks] = useState("");
  const [ch, setCh] = useState(String(nowCh));
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const save = async () => {
    if (!summary.trim()) { toast("填简称"); return; }
    setBusy(true);
    try {
      const r = await api.plantForeshadow(work, summary.trim(), Number(ch) || nowCh, {
        promise: promise.trim(), ftype, intended_effect: effect, audience_knows: aud,
        links: links.split(/[，,、\s]+/).map((s) => s.trim()).filter(Boolean),
      });
      toast("已埋设"); onCreated(r.foreshadow_id);
    } catch (e) { toast(String(e)); } finally { setBusy(false); }
  };
  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 h-11 shrink-0 px-3 border-b border-border">
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={onBack}><ChevronLeft size={14} />返回</Button>
        <span className="text-xs text-muted-foreground">新建承诺线</span>
        <button onClick={onBack} className="ml-auto text-muted-foreground hover:text-foreground"><X size={14} /></button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl px-5 py-4 flex flex-col gap-0.5">
          <DetailHeader kicker="新承诺线">
            <InlineText big v={summary} on={(e) => setSummary(e.target.value)} ph="简称(泳道名,如:渡叔的左眼)" />
          </DetailHeader>
          <Section title="承诺">
            <Block label="对读者的承诺"><InlineText multiline v={promise} on={(e) => setPromise(e.target.value)} ph="读者被引导期待什么" /></Block>
            <Row label="类型"><Chips value={ftype} options={TYPES} colored onPick={setFtype} /></Row>
            <Row label="想要效果"><Chips value={effect} options={EFFECTS} onPick={setEffect} /></Row>
            <Row label="读者预知">
              <label className="flex items-center gap-2 text-sm py-1 cursor-pointer">
                <input type="checkbox" checked={aud} onChange={(e) => setAud(e.target.checked)} />
                <span className="text-muted-foreground">读者提前知道(=戏剧反讽)</span>
              </label>
            </Row>
            <Row label="关联实体"><InlineText v={links} on={(e) => setLinks(e.target.value)} ph="角色/设定名,逗号分隔" /></Row>
            <Row label="埋设章">
              <div className="flex items-center gap-1.5 py-1">
                <Input value={ch} onChange={(e) => setCh(e.target.value)} className="h-7 w-16 text-xs" />
                <Button size="sm" className="h-7 text-xs ml-1" onClick={save} disabled={busy}>埋设</Button>
              </div>
            </Row>
          </Section>
        </div>
      </div>
    </div>
  );
}
