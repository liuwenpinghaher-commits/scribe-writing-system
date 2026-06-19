// 类型化领域 API 客户端。错误不静默:非 2xx 抛出,由调用方处理(修复审查 #3)。
const BASE = import.meta.env.VITE_API ?? "http://127.0.0.1:8801";
const OWNER = "u1"; // 本地开发固定 owner;鉴权由上层自建(工程9)
const H = { "X-Owner-Id": OWNER, "Content-Type": "application/json" };

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(BASE + path, { headers: H, ...init });
  } catch {
    throw new ApiError(0, "无法连接领域 API(:8801 未启动?)");
  }
  if (!r.ok) {
    let detail = `${r.status}`;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch { /* ignore */ }
    throw new ApiError(r.status, String(detail));
  }
  return (await r.json()) as T;
}
const post = <T>(p: string, body?: unknown) =>
  req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined });
const put = <T>(p: string, body: unknown) =>
  req<T>(p, { method: "PUT", body: JSON.stringify(body) });

export interface Work {
  id: string; title: string; genre?: string;
  chapter_count?: number; word_count?: number;
  new_insight_count?: number; pending_optionset_count?: number;
}
export interface Chapter { id?: string; seq: number; title?: string; status: string; volume_id?: string | null; snapshots?: Snapshot[]; }
export interface Snapshot { id: string; content: string; created_by: string; branch_label: string; is_human_locked?: number; }
export interface Intent { reader_feeling?: string; core_emotional_arc?: string; do_not_betray?: string; central_promise?: string; }
export interface Flag { id: string; error_class: string; detail?: string; severity?: string; }
export interface Foreshadow { id: string; summary: string; state: string; }
export interface Setting { id?: string; name: string; type?: string; content?: string; }
export interface Material { id: string; type: string; title?: string; content?: string; tags?: string; status?: string; }
export interface CharacterT { id?: string; name: string; motivation?: string; }
export interface Insight { id: string; summary: string; suggested_action?: string; severity?: string; }
export interface Imagination { id: string; raw_text: string; status?: string; }
export interface OptionSet { id: string; decision_point: string; options: string; }
export interface Volume { id: string; seq: number; title?: string; arc_goal?: string; }
export interface Segment { id: string; seq: number; text: string; created_by: string; citation_refs?: string; }
export interface Draft { content: string; prev_content: string; }
export interface Verdict { status: "aligned" | "soft_deviation" | "hard_violation"; reason: string; red_lines: { text: string; level: string }[]; }
export type ChapterAction = "continue" | "rewrite" | "expand";

export const api = {
  works: () => req<Work[]>("/works"),
  createWork: (title: string) => post<{ work_id: string }>("/works", { title }),
  intent: (w: string) => req<Intent>(`/works/${w}/author-intent`),
  saveIntent: (w: string, reader_feeling: string, do_not_betray: string[], core_emotional_arc = "") =>
    put<{ ok: boolean }>(`/works/${w}/author-intent`, { reader_feeling, do_not_betray, core_emotional_arc }),
  chapters: (w: string) => req<Chapter[]>(`/works/${w}/chapters`),
  chapter: (w: string, seq: number) => req<Chapter>(`/works/${w}/chapters/${seq}`),
  addChapter: (w: string, seq: number, title: string, volume_id?: string) =>
    put<{ chapter_id: string }>(`/works/${w}/chapters`, { seq, title, volume_id }),
  saveProse: (w: string, seq: number, content: string, lock: boolean) =>
    post<{ snapshot_id: string }>(`/works/${w}/chapters/${seq}/prose`, { content, lock }),
  feedback: (w: string, seq: number, nl_critique: string) =>
    post<{ feedback_id: string }>(`/works/${w}/chapters/${seq}/feedback`, { nl_critique }),
  check: (w: string, seq: number) => post<{ new_flags: number }>(`/works/${w}/chapters/${seq}/check`),
  settings: (w: string) => req<Setting[]>(`/works/${w}/settings`),
  characters: (w: string) => req<CharacterT[]>(`/works/${w}/characters`),
  foreshadows: (w: string) => req<Foreshadow[]>(`/works/${w}/foreshadows`),
  flags: (w: string) => req<Flag[]>(`/works/${w}/consistency-flags`),
  insights: (w: string) => req<Insight[]>(`/works/${w}/insights?status=new`),
  actInsight: (w: string, id: string, act: "ack" | "dismiss") =>
    post<{ ok: boolean }>(`/works/${w}/insights/${id}/${act}`),
  review: (w: string) => post<{ new_insights: number }>(`/works/${w}/proactive-review`),
  imaginations: (w: string) => req<Imagination[]>(`/works/${w}/imaginations`),
  capture: (w: string, raw_text: string) =>
    post<{ imagination_id: string }>(`/works/${w}/imaginations`, { raw_text }),
  optionSets: (w: string) => req<OptionSet[]>(`/works/${w}/option-sets`),
  choose: (w: string, oid: string, chosen: string) =>
    post<{ chosen: string }>(`/works/${w}/option-sets/${oid}/choose`, { chosen_option_id: chosen }),
  generateOptions: (w: string, decision_point: string, n = 3) =>
    post<{ option_set_id: string }>(`/works/${w}/option-sets/generate`, { decision_point, n }),
  critique: (w: string, seq: number, content = "", revise = true) =>
    post<{ rounds: { critique: { overall: number; pass: boolean; worst_dims: string[]; issues: string[] } }[]; improved: boolean; final: string; first_overall: number; last_overall: number }>(`/works/${w}/chapters/${seq}/critique`, { content, revise }),
  chat: (message: string) => post<{ content: string }>("/chat", { message }),
  // P1 新增
  volumes: (w: string) => req<Volume[]>(`/works/${w}/volumes`),
  createVolume: (w: string, seq: number, title: string) =>
    post<{ volume_id: string }>(`/works/${w}/volumes`, { seq, title }),
  segments: (w: string, seq: number) => req<Segment[]>(`/works/${w}/chapters/${seq}/segments`),
  rebuildSegments: (w: string, seq: number) =>
    post<{ segments: number }>(`/works/${w}/chapters/${seq}/segments/rebuild`),
  action: (w: string, seq: number, action: ChapterAction, instruction = "") =>
    post<Draft>(`/works/${w}/chapters/${seq}/actions/${action}`, { instruction }),
  // F 流式生成:逐字回调,返回完整草稿;可用 AbortSignal 取消
  streamAction: async (w: string, seq: number, action: ChapterAction, instruction: string,
                       onDelta: (s: string) => void, signal?: AbortSignal): Promise<Draft> => {
    const r = await fetch(`${BASE}/works/${w}/chapters/${seq}/actions/${action}/stream`,
      { method: "POST", headers: H, body: JSON.stringify({ instruction }), signal });
    if (!r.ok || !r.body) throw new ApiError(r.status, "流式连接失败");
    const reader = r.body.getReader(); const dec = new TextDecoder();
    let buf = ""; let result: Draft = { content: "", prev_content: "" };
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n"); buf = parts.pop() ?? "";
      for (const p of parts) {
        const line = p.trim(); if (!line.startsWith("data:")) continue;
        try {
          const ev = JSON.parse(line.slice(5).trim());
          if (ev.delta) onDelta(ev.delta);
          if (ev.done) result = { content: ev.content, prev_content: ev.prev_content };
        } catch { /* ignore */ }
      }
    }
    return result;
  },
  branches: (w: string, seq: number) =>
    req<{ label: string; content: string; created_by: string; locked: number }[]>(`/works/${w}/chapters/${seq}/branches`),
  createBranch: (w: string, seq: number, label: string, content: string) =>
    post<{ snapshot_id: string }>(`/works/${w}/chapters/${seq}/branches`, { label, content }),
  mergeBranch: (w: string, seq: number, label: string) =>
    post<{ merged: string }>(`/works/${w}/chapters/${seq}/branches/${encodeURIComponent(label)}/merge`),
  intentCheck: (w: string, seq: number) => post<Verdict>(`/works/${w}/chapters/${seq}/intent-check`),
  pref: (w: string, source: string, polarity = "+", signal?: unknown) =>
    post<{ signal_id: string }>(`/works/${w}/preference`, { source, polarity, signal }),
  // P3 裁决
  impact: (w: string, name: string) =>
    req<{ seq: number; title?: string; snippet: string }[]>(`/works/${w}/impact?name=${encodeURIComponent(name)}`),
  setStatus: (w: string, seq: number, status: "draft" | "done" | "revising") =>
    post<{ status: string }>(`/works/${w}/chapters/${seq}/status`, { status }),
  moveChapter: (w: string, seq: number, direction: "up" | "down") =>
    post<{ moved: boolean }>(`/works/${w}/chapters/${seq}/move/${direction}`),
  addSetting: (w: string, name: string, type_ = "设定", description = "") =>
    post<{ setting_id: string }>(`/works/${w}/settings`, { name, type_, description }),
  addCharacter: (w: string, name: string, motivation = "") =>
    post<{ character_id: string }>(`/works/${w}/characters`, { name, motivation }),
  memory: (w: string) => req<{ global: string; chapters: { seq: number; summary_text: string }[] }>(`/works/${w}/memory`),
  timeline: (w: string) => req<{ chapter_seq: number; description: string }[]>(`/works/${w}/timeline`),
  cost: (w: string) => req<{ calls: number; tokens: number; cost_usd: number }>(`/works/${w}/cost`),
  materials: (w: string) => req<Material[]>(`/works/${w}/materials`),
  addMaterial: (w: string, content: string, type = "snippet", scope = "work") =>
    post<{ material_id: string }>(`/works/${w}/materials`, { content, type, scope }),
  processMaterial: (w: string, mid: string) =>
    post<{ summary: string; tags: string[] }>(`/works/${w}/materials/${mid}/process`),
  distillMaterial: (w: string, mid: string, target: "setting" | "exemplar") =>
    post<{ ok?: boolean }>(`/works/${w}/materials/${mid}/distill`, { target }),
  deleteMaterial: (w: string, mid: string) =>
    req<{ ok: boolean }>(`/works/${w}/materials/${mid}`, { method: "DELETE" }),
  resolveFlag: (w: string, fid: string, action: "confirm" | "dismiss" | "fix") =>
    post<{ status: string }>(`/works/${w}/consistency-flags/${fid}/${action}`),
  advanceForeshadow: (w: string, fid: string, action: "trigger" | "pay" | "abandon") =>
    post<{ state: string }>(`/works/${w}/foreshadows/${fid}/${action}`),
};
