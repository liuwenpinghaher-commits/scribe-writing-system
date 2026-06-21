/**
 * InScenePanel.tsx — 写作台右栏「本章在场」面板:让相关性注入可见可控。
 * 主编写第 N 章时会重点参考"在场"的实体(开着伏笔关联 / 近章点名 / 钉住);
 * ●=本章在场、○=不在场(灰);点图钉强制钉住(总在场)。所见即注入。
 */
import { api, type CharacterT } from "./api";
import { useData, useToast } from "./common";
import { Pin, PinOff } from "lucide-react";

export function InScenePanel({ work, seq, rev }: { work: string; seq: number | null; rev: number }) {
  const rel = useData(() => (seq ? api.relevant(work, seq) : Promise.resolve({ characters: [] as CharacterT[] })), [work, seq, rev]);
  const all = useData(() => api.characters(work), [work, rev]);
  const relNames = new Set((rel.data?.characters ?? []).map((c) => c.name));
  const toast = useToast();
  const toggle = async (c: CharacterT) => {
    try { await api.pinCharacter(work, c.name, !c.pinned); all.reload(); rel.reload(); toast(c.pinned ? "已取消钉住" : "已钉住·本章起总在场"); }
    catch (e) { toast(String(e), "err"); }
  };
  const chars = [...(all.data ?? [])].sort((a, b) => Number(relNames.has(b.name)) - Number(relNames.has(a.name)));
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[11px] text-muted-foreground leading-relaxed">
        主编写{seq ? `第${seq}章` : "本章"}时重点参考<b className="text-foreground">在场</b>的实体(开着伏笔关联/近章点名/钉住)。●在场 ○不在场;图钉=强制在场。
      </p>
      <div className="flex flex-col">
        {chars.length === 0 && <span className="text-xs text-muted-foreground/60 py-2">还没有角色</span>}
        {chars.map((c) => {
          const inScene = relNames.has(c.name);
          return (
            <div key={c.id ?? c.name} className={`flex items-center gap-1.5 py-1 ${inScene ? "" : "opacity-45"}`}
              style={{ borderBottom: "1px solid color-mix(in srgb, var(--border) 50%, transparent)" }}>
              <span className="text-xs" style={{ color: inScene ? "var(--accent)" : "var(--muted-foreground)" }}>{inScene ? "●" : "○"}</span>
              <span className="text-sm text-foreground truncate flex-1">{c.name}
                {c.aliases?.length ? <span className="text-[10px] text-muted-foreground"> ({c.aliases.join("/")})</span> : null}
              </span>
              <button onClick={() => toggle(c)} title={c.pinned ? "取消钉住" : "钉住(总在场)"}
                className={`w-6 h-6 inline-flex items-center justify-center rounded hover:bg-accent ${c.pinned ? "text-primary" : "text-muted-foreground/50"}`}>
                {c.pinned ? <Pin size={13} fill="currentColor" /> : <PinOff size={13} />}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
