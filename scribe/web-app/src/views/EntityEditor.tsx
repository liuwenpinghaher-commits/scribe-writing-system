/**
 * EntityEditor.tsx — 实体全字段详情/编辑表单(设定库 2.0 核心)。
 * 把每类实体该有的能力全展现:可见标签 + 字段分组 + 保存反馈(skill §8 表单规范)。
 * 人物:身份/内核(wound/lie/fear/want/need)/核心矛盾/声音样本/弧光;
 * 设定:基本 + 力量体系结构化字段(cost/limitations/会出什么乱子);母题:隐喻网四件套。
 */
import { useState } from "react";
import { Loader2, Check, X, MessageSquareQuote, Plus } from "lucide-react";
import { api, type CharacterT, type Setting, type Motif } from "@/api";
import { useData, useToast } from "@/common";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

/** 人物附加:出场章节(出场追踪)+ 状态轨迹 Progressions(逐章变化,绑定生效章) */
function CharExtras({ work, name }: { work: string; name: string }) {
  const app = useData(() => api.appearances(work, name), [work, name]);
  const states = useData(() => api.charStates(work, name), [work, name]);
  const [seq, setSeq] = useState("");
  const [desc, setDesc] = useState("");
  const [adding, setAdding] = useState(false);
  const toast = useToast();
  const add = async () => {
    const n = Number(seq);
    if (!n || !desc.trim()) { toast("填生效章 + 状态描述"); return; }
    setAdding(true);
    try { await api.addCharState(work, name, n, desc.trim()); setSeq(""); setDesc(""); states.reload(); toast("已加状态"); }
    catch (e) { toast(String(e)); } finally { setAdding(false); }
  };
  return (
    <div className="flex flex-col gap-2.5">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1">出场 / 状态轨迹</div>
      <div className="text-xs text-muted-foreground">
        出场:{app.data?.chapters?.length ? app.data.chapters.map((c) => `第${c}章`).join("、") : "—"}
      </div>
      <div className="flex flex-col gap-1">
        {(states.data ?? []).map((s) => (
          <div key={s.id ?? s.chapter_seq} className="text-xs flex gap-1.5">
            <span className="shrink-0 text-muted-foreground">第{s.chapter_seq}章:</span>
            <span>{s.state_desc}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5 items-center">
        <Input value={seq} onChange={(e) => setSeq(e.target.value)} placeholder="章" className="h-7 text-xs w-12" />
        <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="该章起的新状态(如:左眼又瞎一分)" className="h-7 text-xs flex-1"
          onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={add} disabled={adding}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
        </Button>
      </div>
    </div>
  );
}

export type EntityKind = "character" | "setting" | "motif";

// 点击进入编辑、平时纯展示(Notion 式)。失焦/Esc 回展示,Enter 提交单行。
type ChangeFn = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
const focusEnd = (el: HTMLInputElement | HTMLTextAreaElement | null) => {
  if (!el) return; el.focus();
  const n = el.value.length; try { el.setSelectionRange(n, n); } catch { /* */ }
};
function InlineText({ v, on, ph, multiline, rows, big }: {
  v: string; on: ChangeFn; ph?: string; multiline?: boolean; rows?: number; big?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const sz = big ? "text-2xl font-bold text-foreground" : "text-sm";
  if (editing) {
    const cls = `w-full bg-transparent rounded-md px-2 py-1.5 outline-none transition-colors focus:bg-muted focus:ring-1 focus:ring-ring/30 placeholder:text-muted-foreground/40 ${sz}`;
    return multiline
      ? <textarea ref={focusEnd} value={v} onChange={on} placeholder={ph} rows={rows ?? 3} onBlur={() => setEditing(false)}
          onKeyDown={(ev) => { if (ev.key === "Escape") (ev.target as HTMLTextAreaElement).blur(); }}
          className={cls + " resize-none leading-relaxed"} />
      : <input ref={focusEnd} value={v} onChange={on} placeholder={ph} onBlur={() => setEditing(false)}
          onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === "Escape") (ev.target as HTMLInputElement).blur(); }}
          className={cls} />;
  }
  return (
    <div onClick={() => setEditing(true)} title="点击编辑"
      className={`px-2 py-1.5 rounded-md cursor-text hover:bg-muted/40 transition-colors min-h-[34px] flex items-center ${sz}`}>
      {v
        ? <span className={multiline ? "whitespace-pre-wrap" : "truncate"}>{v}</span>
        : <span className={`text-muted-foreground/35 font-normal truncate ${big ? "text-2xl" : "text-sm"}`}>{ph || "添加…"}</span>}
    </div>
  );
}

/** 标签左/值右一行(短字段),底部细分隔线 */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid grid-cols-[88px_1fr] items-center gap-2 border-b border-border/30">
      <span className="text-xs text-muted-foreground select-none">{label}</span>
      {children}
    </label>
  );
}
/** 标签上/值下整行(多行/长字段) */
function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col border-b border-border/30 pb-1">
      <span className="text-xs text-muted-foreground select-none pt-0.5">{label}</span>
      {children}
    </label>
  );
}
function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2.5 mt-5 mb-1">
        <span className="text-xs font-bold uppercase tracking-wider text-foreground/55 whitespace-nowrap">{title}</span>
        <div className="flex-1 h-px bg-border/70" />
      </div>
      {children}
    </div>
  );
}

export function EntityEditor({ work, kind, entity, onSaved, onClose, onDiscuss }: {
  work: string; kind: EntityKind; entity?: CharacterT | Setting | Motif | null;
  onSaved: () => void; onClose: () => void; onDiscuss?: (kind: EntityKind, name: string) => void;
}) {
  const e = (entity ?? {}) as Record<string, unknown>;
  const initStr = (k: string) => (typeof e[k] === "string" ? (e[k] as string) : "");
  const [f, setF] = useState<Record<string, string>>(() => {
    const o: Record<string, string> = { name: initStr("name") };
    if (kind === "character") {
      for (const k of ["motivation", "voice", "core_contradiction", "wound", "lie", "fear", "want", "need", "arc"]) o[k] = initStr(k);
      o.voice_samples = Array.isArray(e.voice_samples) ? (e.voice_samples as string[]).join("\n") : "";
    } else if (kind === "setting") {
      o.type = initStr("type") || "设定"; o.description = initStr("content") || initStr("description");
      const ff = (e.fields as Record<string, string>) ?? {};
      o.cost = ff.cost ?? ""; o.limitations = ff.limitations ?? ""; o.trouble_it_causes = ff.trouble_it_causes ?? "";
    } else {
      for (const k of ["metaphor_unfolding", "bound_theme", "naming_logic"]) o[k] = initStr(k);
      o.material_echoes = Array.isArray(e.material_echoes) ? (e.material_echoes as string[]).join("、") : "";
    }
    return o;
  });
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const toast = useToast();
  const set = (k: string) => (ev: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setF((o) => ({ ...o, [k]: ev.target.value }));
  const editing = !!(entity && (entity as { name?: string }).name);

  const save = async () => {
    if (!f.name.trim()) { toast("名称必填"); return; }
    setSaving(true);
    try {
      if (kind === "character") {
        await api.addCharacter(work, f.name.trim(), f.motivation.trim(), {
          voice: f.voice.trim(),
          voice_samples: f.voice_samples.split("\n").map((s) => s.trim()).filter(Boolean),
          core_contradiction: f.core_contradiction.trim(), wound: f.wound.trim(),
          lie: f.lie.trim(), fear: f.fear.trim(), want: f.want.trim(), need: f.need.trim(), arc: f.arc.trim(),
        });
      } else if (kind === "setting") {
        const fields: Record<string, string> = {};
        if (f.cost.trim()) fields.cost = f.cost.trim();
        if (f.limitations.trim()) fields.limitations = f.limitations.trim();
        if (f.trouble_it_causes.trim()) fields.trouble_it_causes = f.trouble_it_causes.trim();
        await api.addSetting(work, f.name.trim(), f.type.trim() || "设定", f.description.trim(), fields);
      } else {
        await api.addMotif(work, {
          name: f.name.trim(), metaphor_unfolding: f.metaphor_unfolding.trim(),
          bound_theme: f.bound_theme.trim(), naming_logic: f.naming_logic.trim(),
          material_echoes: f.material_echoes.split(/[，,、\n]/).map((s) => s.trim()).filter(Boolean),
        });
      }
      setDone(true); toast(editing ? "已更新" : "已新增"); onSaved();
      setTimeout(() => setDone(false), 1200);
    } catch (err) { toast(String(err)); } finally { setSaving(false); }
  };

  const title = kind === "character" ? "角色" : kind === "setting" ? "设定" : "母题";
  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span className="text-xs font-medium text-muted-foreground">{editing ? `${title}详情` : `新增${title}`}</span>
        <button onClick={onClose} className="w-6 h-6 rounded inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"><X size={14} /></button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl px-5 py-4 flex flex-col gap-0.5">
          {/* 文档头:类型小标 + 大标题(点击编辑) */}
          <div className="pb-3 mb-1 border-b border-border">
            <div className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground/50 px-2 mb-0.5">{title}</div>
            <InlineText v={f.name} on={set("name")} ph={`${title}名`} big />
          </div>

          {kind === "character" && <>
            <Group title="身份">
              <Row label="动机"><InlineText v={f.motivation} on={set("motivation")} ph="他想要什么" /></Row>
            </Group>
            <Group title="声音(防 OOC 命门)">
              <Row label="声音指纹"><InlineText v={f.voice} on={set("voice")} ph="用词/句式/口头禅,如:极静、短句、不解释" /></Row>
              <Block label="声音样本"><InlineText multiline v={f.voice_samples} on={set("voice_samples")} rows={3} ph={"每行一句代表性台词(写到该角色时原样供 AI 参考):\n三不渡，是规矩。\n上船，别回头。"} /></Block>
            </Group>
            <Group title="内核(立体之本)">
              <Row label="核心矛盾"><InlineText v={f.core_contradiction} on={set("core_contradiction")} ph="一组内在对冲,如:守规矩的执念↔为孩子愿破规矩" /></Row>
              <Row label="创伤 wound"><InlineText v={f.wound} on={set("wound")} ph="造成错误信念的过去" /></Row>
              <Row label="错误信念 lie"><InlineText v={f.lie} on={set("lie")} ph="因创伤而信的谎" /></Row>
              <Row label="恐惧 fear"><InlineText v={f.fear} on={set("fear")} ph="最怕发生的事" /></Row>
              <Row label="外在目标 want"><InlineText v={f.want} on={set("want")} ph="角色以为自己要的" /></Row>
              <Row label="内在需求 need"><InlineText v={f.need} on={set("need")} ph="其实真正需要的" /></Row>
            </Group>
            <Group title="弧光">
              <Block label="弧线"><InlineText multiline v={f.arc} on={set("arc")} ph="从起点态→终点态如何改变" /></Block>
            </Group>
            {editing && <div className="pt-2"><CharExtras work={work} name={(entity as CharacterT).name} /></div>}
          </>}

          {kind === "setting" && <>
            <div className="pt-1.5">
              <Row label="类型"><InlineText v={f.type} on={set("type")} ph="力量体系 / place / faction / item / lore…" /></Row>
              <Block label="描述"><InlineText multiline v={f.description} on={set("description")} rows={3} ph="这个设定是什么" /></Block>
            </div>
            <Group title="规则·代价与限制(力量体系)">
              <Row label="代价 cost"><InlineText v={f.cost} on={set("cost")} ph="用了要付什么,如:破规一次左眼瞎一分" /></Row>
              <Row label="限制"><InlineText v={f.limitations} on={set("limitations")} ph="不能做什么" /></Row>
              <Row label="会出什么乱子"><InlineText v={f.trouble_it_causes} on={set("trouble_it_causes")} ph="推不出乱子的规则就不够好" /></Row>
            </Group>
          </>}

          {kind === "motif" && <div className="pt-1.5">
            <Block label="隐喻展开"><InlineText multiline v={f.metaphor_unfolding} on={set("metaphor_unfolding")} ph="天地为炉,万物为铜…" /></Block>
            <Block label="绑定主题句"><InlineText multiline v={f.bound_theme} on={set("bound_theme")} ph="这本书在说什么" /></Block>
            <Row label="物质回声"><InlineText v={f.material_echoes} on={set("material_echoes")} ph="反复画面,逗号分隔:长明灯、河面浮炭…" /></Row>
            <Row label="命名逻辑"><InlineText v={f.naming_logic} on={set("naming_logic")} ph="如:主角给儿子取名'炭'" /></Row>
          </div>}
        </div>
      </div>
      <div className="flex items-center gap-2 p-2.5 border-t border-border">
        {editing && onDiscuss && (
          <Button variant="ghost" size="sm" className="gap-1 text-xs mr-auto" onClick={() => onDiscuss(kind, f.name)}>
            <MessageSquareQuote size={13} /> 与主编讨论这个
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={onClose} className={editing && onDiscuss ? "" : "ml-auto"}>取消</Button>
        <Button size="sm" className="gap-1" onClick={save} disabled={saving || !f.name.trim()}>
          {saving ? <Loader2 size={13} className="animate-spin" /> : done ? <Check size={13} /> : null}
          {editing ? "保存" : "新增"}
        </Button>
      </div>
    </div>
  );
}
