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
import { InlineText, Row, Block, Section, DetailHeader } from "@/components/detail";

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
    <Section title="出场 / 状态轨迹">
      <div className="text-xs text-muted-foreground px-2 py-1">
        出场:{app.data?.chapters?.length ? app.data.chapters.map((c) => `第${c}章`).join("、") : "—"}
      </div>
      <div className="flex flex-col gap-0.5 px-2">
        {(states.data ?? []).map((s) => (
          <div key={s.id ?? s.chapter_seq} className="text-xs flex gap-1.5">
            <span className="shrink-0 text-muted-foreground">第{s.chapter_seq}章:</span>
            <span>{s.state_desc}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5 items-center px-1 pt-1.5">
        <Input value={seq} onChange={(e) => setSeq(e.target.value)} placeholder="章" className="h-7 text-xs w-12" />
        <Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="该章起的新状态(如:左眼又瞎一分)" className="h-7 text-xs flex-1"
          onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={add} disabled={adding}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
        </Button>
      </div>
    </Section>
  );
}

/** 实体关系:列出与本实体相关的关系 + 手动加(直接进关系图谱,两模块打通) */
function EntityRelations({ work, name }: { work: string; name: string }) {
  const rels = useData(() => api.entityRelations(work, name), [work, name]);
  const [dst, setDst] = useState("");
  const [rel, setRel] = useState("");
  const [adding, setAdding] = useState(false);
  const toast = useToast();
  const add = async () => {
    if (!dst.trim() || !rel.trim()) { toast("填对象 + 关系"); return; }
    setAdding(true);
    try { await api.addRelation(work, name, dst.trim(), rel.trim()); setDst(""); setRel(""); rels.reload(); toast("已加关系(已进关系图谱)"); }
    catch (e) { toast(String(e)); } finally { setAdding(false); }
  };
  return (
    <Section title="关系(进关系图谱)">
      <div className="flex flex-col gap-1 px-2 py-1">
        {(rels.data ?? []).map((r, i) => (
          <div key={r.id ?? i} className="text-xs flex gap-1.5">
            <span className="text-muted-foreground">{r.src_entity === name ? "→" : "←"}</span>
            <span className="font-medium text-foreground">{r.src_entity === name ? r.dst_entity : r.src_entity}</span>
            <span className="text-muted-foreground">· {r.relation}</span>
          </div>
        ))}
        {(rels.data ?? []).length === 0 && <span className="text-xs text-muted-foreground/50">还没有关系</span>}
      </div>
      <div className="flex gap-1.5 items-center px-1 pt-1">
        <Input value={dst} onChange={(e) => setDst(e.target.value)} placeholder="对象(另一实体名)" className="h-7 text-xs flex-1" />
        <Input value={rel} onChange={(e) => setRel(e.target.value)} placeholder="关系(师徒/宿敌…)" className="h-7 text-xs w-28"
          onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={add} disabled={adding}>{adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}</Button>
      </div>
    </Section>
  );
}

/** 实体线·节点编辑(统一线模型):给角色/母题/设定排 引入/发展/复现/兑现 节点,喂泳道+逐章注入主编 */
const _BEAT_KINDS = [{ k: "intro", l: "引入" }, { k: "develop", l: "发展" }, { k: "reinforce", l: "复现" }, { k: "payoff", l: "兑现" }];
const _beatLabel = (k: string) => _BEAT_KINDS.find((x) => x.k === k)?.l || k;
function EntityBeats({ work, etype, name }: { work: string; etype: string; name: string }) {
  const beats = useData(() => api.entityBeats(work, etype, name), [work, etype, name]);
  const [ch, setCh] = useState("");
  const [kind, setKind] = useState("develop");
  const [guide, setGuide] = useState("");
  const [eff, setEff] = useState("");
  const [adding, setAdding] = useState(false);
  const toast = useToast();
  const add = async () => {
    const n = Number(ch);
    if (!n || !guide.trim()) { toast("填生效章 + 本章怎么处理"); return; }
    setAdding(true);
    try { await api.addEntityBeat(work, { etype, entity: name, chapter: n, kind, guidance: guide.trim(), effect: eff.trim() }); setCh(""); setGuide(""); setEff(""); beats.reload(); toast("已加节点"); }
    catch (e) { toast(String(e)); } finally { setAdding(false); }
  };
  return (
    <Section title="线·节点(逐章发展,写到该章会注入主编)">
      {(beats.data ?? []).map((b, i) => (
        <div key={b.id ?? i} className="grid items-start gap-2 py-0.5 px-2" style={{ gridTemplateColumns: "72px 1fr" }}>
          <span className="text-xs text-foreground pt-0.5"><span className="font-semibold">{_beatLabel(b.kind)}</span> 第{b.chapter}章</span>
          <span className="text-sm">{b.guidance || <span className="text-muted-foreground/50">（无引导）</span>}{b.effect ? <span className="text-[11px] text-muted-foreground"> · 效果:{b.effect}</span> : null}</span>
        </div>
      ))}
      {(beats.data ?? []).length === 0 && <div className="text-xs text-muted-foreground/50 px-2 py-1">还没有节点。排上引入/发展/兑现,主编写到该章就照做。</div>}
      <div className="flex items-center gap-1.5 px-1 pt-1.5 flex-wrap">
        {_BEAT_KINDS.map((x) => (
          <button key={x.k} onClick={() => setKind(x.k)}
            className={`text-[11px] px-2 py-0.5 rounded-md border transition-colors ${kind === x.k ? "bg-primary text-primary-foreground border-primary" : "text-muted-foreground border-border hover:border-foreground"}`}>{x.l}</button>
        ))}
        <span className="text-xs text-muted-foreground ml-1">第</span>
        <Input value={ch} onChange={(e) => setCh(e.target.value)} className="h-7 w-12 text-xs" />
        <span className="text-xs text-muted-foreground">章</span>
      </div>
      <div className="flex items-center gap-1.5 px-1 pt-1">
        <Input value={guide} onChange={(e) => setGuide(e.target.value)} placeholder="本章具体怎么处理(如:第三次质疑执念)" className="h-7 text-xs flex-1" />
        <Input value={eff} onChange={(e) => setEff(e.target.value)} placeholder="想要效果" className="h-7 text-xs w-24" onKeyDown={(e) => { if (e.key === "Enter") add(); }} />
        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={add} disabled={adding}>{adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}</Button>
      </div>
    </Section>
  );
}

export type EntityKind = "character" | "setting" | "motif";

export function EntityEditor({ work, kind, entity, onSaved, onClose, onDiscuss, defaultType }: {
  work: string; kind: EntityKind; entity?: CharacterT | Setting | Motif | null;
  onSaved: () => void; onClose: () => void; onDiscuss?: (kind: EntityKind, name: string) => void; defaultType?: string;
}) {
  const e = (entity ?? {}) as Record<string, unknown>;
  const initStr = (k: string) => (typeof e[k] === "string" ? (e[k] as string) : "");
  const [f, setF] = useState<Record<string, string>>(() => {
    const o: Record<string, string> = { name: initStr("name") };
    if (kind === "character") {
      for (const k of ["motivation", "voice", "core_contradiction", "wound", "lie", "fear", "want", "need", "arc"]) o[k] = initStr(k);
      o.voice_samples = Array.isArray(e.voice_samples) ? (e.voice_samples as string[]).join("\n") : "";
      o.aliases = Array.isArray(e.aliases) ? (e.aliases as string[]).join("、") : "";
    } else if (kind === "setting") {
      o.type = initStr("type") || defaultType || "设定"; o.description = initStr("content") || initStr("description");
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
          aliases: f.aliases.split(/[，,、\s]+/).map((s) => s.trim()).filter(Boolean),
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
          <DetailHeader kicker={title}>
            <InlineText v={f.name} on={set("name")} ph={`${title}名`} big />
          </DetailHeader>

          {kind === "character" && <>
            <Section title="身份">
              <Row label="动机"><InlineText v={f.motivation} on={set("motivation")} ph="他想要什么" /></Row>
              <Row label="别名"><InlineText v={f.aliases} on={set("aliases")} ph="老渡、摆渡的(逗号分隔;注入/相关性会识别)" /></Row>
            </Section>
            <Section title="声音(防 OOC 命门)">
              <Row label="声音指纹"><InlineText v={f.voice} on={set("voice")} ph="用词/句式/口头禅,如:极静、短句、不解释" /></Row>
              <Block label="声音样本"><InlineText multiline v={f.voice_samples} on={set("voice_samples")} rows={3} ph={"每行一句代表性台词(写到该角色时原样供 AI 参考):\n三不渡，是规矩。\n上船，别回头。"} /></Block>
            </Section>
            <Section title="内核(立体之本)">
              <Row label="核心矛盾"><InlineText v={f.core_contradiction} on={set("core_contradiction")} ph="一组内在对冲,如:守规矩的执念↔为孩子愿破规矩" /></Row>
              <Row label="创伤 wound"><InlineText v={f.wound} on={set("wound")} ph="造成错误信念的过去" /></Row>
              <Row label="错误信念 lie"><InlineText v={f.lie} on={set("lie")} ph="因创伤而信的谎" /></Row>
              <Row label="恐惧 fear"><InlineText v={f.fear} on={set("fear")} ph="最怕发生的事" /></Row>
              <Row label="外在目标 want"><InlineText v={f.want} on={set("want")} ph="角色以为自己要的" /></Row>
              <Row label="内在需求 need"><InlineText v={f.need} on={set("need")} ph="其实真正需要的" /></Row>
            </Section>
            <Section title="弧光">
              <Block label="弧线"><InlineText multiline v={f.arc} on={set("arc")} ph="从起点态→终点态如何改变" /></Block>
            </Section>
            {editing && <div className="pt-2"><CharExtras work={work} name={(entity as CharacterT).name} /></div>}
          </>}

          {kind === "setting" && <>
            <div className="pt-1.5">
              <Row label="类型"><InlineText v={f.type} on={set("type")} ph="力量体系 / place / faction / item / lore…" /></Row>
              <Block label="描述"><InlineText multiline v={f.description} on={set("description")} rows={3} ph="这个设定是什么" /></Block>
            </div>
            <Section title="规则·代价与限制(力量体系)">
              <Row label="代价 cost"><InlineText v={f.cost} on={set("cost")} ph="用了要付什么,如:破规一次左眼瞎一分" /></Row>
              <Row label="限制"><InlineText v={f.limitations} on={set("limitations")} ph="不能做什么" /></Row>
              <Row label="会出什么乱子"><InlineText v={f.trouble_it_causes} on={set("trouble_it_causes")} ph="推不出乱子的规则就不够好" /></Row>
            </Section>
          </>}

          {kind === "motif" && <div className="pt-1.5">
            <Block label="隐喻展开"><InlineText multiline v={f.metaphor_unfolding} on={set("metaphor_unfolding")} ph="天地为炉,万物为铜…" /></Block>
            <Block label="绑定主题句"><InlineText multiline v={f.bound_theme} on={set("bound_theme")} ph="这本书在说什么" /></Block>
            <Row label="物质回声"><InlineText v={f.material_echoes} on={set("material_echoes")} ph="反复画面,逗号分隔:长明灯、河面浮炭…" /></Row>
            <Row label="命名逻辑"><InlineText v={f.naming_logic} on={set("naming_logic")} ph="如:主角给儿子取名'炭'" /></Row>
          </div>}

          {editing && <EntityBeats work={work} etype={kind} name={f.name} />}
          {editing && <EntityRelations work={work} name={f.name} />}
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
