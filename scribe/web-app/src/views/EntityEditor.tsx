/**
 * EntityEditor.tsx — 实体全字段详情/编辑表单(设定库 2.0 核心)。
 * 把每类实体该有的能力全展现:可见标签 + 字段分组 + 保存反馈(skill §8 表单规范)。
 * 人物:身份/内核(wound/lie/fear/want/need)/核心矛盾/声音样本/弧光;
 * 设定:基本 + 力量体系结构化字段(cost/limitations/会出什么乱子);母题:隐喻网四件套。
 */
import { useState } from "react";
import { Loader2, Check, X } from "lucide-react";
import { api, type CharacterT, type Setting, type Motif } from "@/api";
import { useToast } from "@/common";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

export type EntityKind = "character" | "setting" | "motif";

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium text-foreground">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-muted-foreground">{hint}</span>}
    </label>
  );
}
function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2.5">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground border-b border-border pb-1">{title}</div>
      {children}
    </div>
  );
}

export function EntityEditor({ work, kind, entity, onSaved, onClose }: {
  work: string; kind: EntityKind; entity?: CharacterT | Setting | Motif | null;
  onSaved: () => void; onClose: () => void;
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
        <span className="text-sm font-medium">{editing ? `编辑${title}` : `新增${title}`}{editing && `：${f.name}`}</span>
        <button onClick={onClose} className="w-6 h-6 rounded inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"><X size={14} /></button>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-4">
        <Field label="名称 *"><Input value={f.name} onChange={set("name")} className="h-8 text-sm" placeholder={`${title}名`} /></Field>

        {kind === "character" && <>
          <Group title="身份">
            <Field label="动机"><Input value={f.motivation} onChange={set("motivation")} className="h-8 text-sm" placeholder="他想要什么" /></Field>
          </Group>
          <Group title="声音(防 OOC 命门)">
            <Field label="声音指纹" hint="用词/句式/口头禅,如:极静、短句、不解释"><Input value={f.voice} onChange={set("voice")} className="h-8 text-sm" /></Field>
            <Field label="声音样本" hint="每行一句代表性台词,写到该角色时原样供 AI 参考"><Textarea rows={3} value={f.voice_samples} onChange={set("voice_samples")} className="text-sm resize-none" placeholder={"三不渡，是规矩。\n你欠的，水替你还。\n上船，别回头。"} /></Field>
          </Group>
          <Group title="内核(立体之本)">
            <Field label="核心矛盾" hint="一组内在对冲,如:守规矩的执念↔为孩子愿破规矩"><Input value={f.core_contradiction} onChange={set("core_contradiction")} className="h-8 text-sm" /></Field>
            <Field label="创伤 wound" hint="造成错误信念的过去"><Input value={f.wound} onChange={set("wound")} className="h-8 text-sm" /></Field>
            <Field label="错误信念 lie"><Input value={f.lie} onChange={set("lie")} className="h-8 text-sm" /></Field>
            <Field label="恐惧 fear"><Input value={f.fear} onChange={set("fear")} className="h-8 text-sm" /></Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="外在目标 want"><Input value={f.want} onChange={set("want")} className="h-8 text-sm" /></Field>
              <Field label="内在需求 need"><Input value={f.need} onChange={set("need")} className="h-8 text-sm" /></Field>
            </div>
          </Group>
          <Group title="弧光">
            <Field label="弧线" hint="从起点态→终点态如何改变"><Textarea rows={2} value={f.arc} onChange={set("arc")} className="text-sm resize-none" /></Field>
          </Group>
        </>}

        {kind === "setting" && <>
          <div className="grid grid-cols-2 gap-2">
            <Field label="类型" hint="力量体系 / place / faction / item / lore…"><Input value={f.type} onChange={set("type")} className="h-8 text-sm" /></Field>
          </div>
          <Field label="描述"><Textarea rows={3} value={f.description} onChange={set("description")} className="text-sm resize-none" /></Field>
          <Group title="规则·代价与限制(力量体系;判据2:带代价+会出什么乱子)">
            <Field label="代价 cost" hint="用了要付什么,如:破规一次左眼瞎一分"><Input value={f.cost} onChange={set("cost")} className="h-8 text-sm" /></Field>
            <Field label="限制 limitations" hint="不能做什么"><Input value={f.limitations} onChange={set("limitations")} className="h-8 text-sm" /></Field>
            <Field label="会出什么乱子" hint="推不出乱子的规则就不够好"><Input value={f.trouble_it_causes} onChange={set("trouble_it_causes")} className="h-8 text-sm" /></Field>
          </Group>
        </>}

        {kind === "motif" && <>
          <Field label="隐喻展开" hint="天地为炉,万物为铜…"><Textarea rows={2} value={f.metaphor_unfolding} onChange={set("metaphor_unfolding")} className="text-sm resize-none" /></Field>
          <Field label="绑定主题句" hint="这本书在说什么"><Textarea rows={2} value={f.bound_theme} onChange={set("bound_theme")} className="text-sm resize-none" /></Field>
          <Field label="物质回声" hint="贯穿全书的反复画面,逗号分隔:长明灯、河面浮炭…"><Input value={f.material_echoes} onChange={set("material_echoes")} className="h-8 text-sm" /></Field>
          <Field label="命名逻辑" hint="如:主角给儿子取名'炭'"><Input value={f.naming_logic} onChange={set("naming_logic")} className="h-8 text-sm" /></Field>
        </>}
      </div>
      <div className="flex justify-end gap-2 p-2.5 border-t border-border">
        <Button variant="ghost" size="sm" onClick={onClose}>取消</Button>
        <Button size="sm" className="gap-1" onClick={save} disabled={saving || !f.name.trim()}>
          {saving ? <Loader2 size={13} className="animate-spin" /> : done ? <Check size={13} /> : null}
          {editing ? "保存" : "新增"}
        </Button>
      </div>
    </div>
  );
}
