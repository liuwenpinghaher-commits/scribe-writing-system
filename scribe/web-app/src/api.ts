// 类型化领域 API 客户端。错误不静默:非 2xx 抛出,由调用方处理(修复审查 #3)。
const BASE = import.meta.env.VITE_API ?? "http://127.0.0.1:3320";
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
    throw new ApiError(0, "无法连接领域 API(:3320 未启动?)");
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

export interface PendingWrite {
  id: string; work_id: string; tool_name: string;
  args: Record<string, unknown>; status: string; created_at?: string;
}

export interface Work {
  id: string; title: string; genre?: string;
  chapter_count?: number; word_count?: number;
  new_insight_count?: number; pending_optionset_count?: number;
}
export interface Chapter { id?: string; seq: number; title?: string; status: string; volume_id?: string | null; snapshots?: Snapshot[]; }
export interface Snapshot { id: string; content: string; created_by: string; branch_label: string; is_human_locked?: number; }
export interface Intent { reader_feeling?: string; core_emotional_arc?: string; do_not_betray?: string[]; central_promise?: string; }
export interface Flag { id: string; error_class: string; detail?: string; severity?: string; }
export interface Foreshadow { id: string; summary: string; state: string; }
export interface ForeshadowStatus { id: string; summary: string; state: string; chapter?: number; importance?: string; echoes?: number[]; overdue?: boolean; promise?: string; ftype?: string; payoff_chapter?: number | null; }
export interface ExtractResult {
  characters: { name: string; motivation?: string }[];
  settings: { name: string; type?: string }[];
  foreshadows: { summary: string; chapter?: number }[];
}
export interface Setting { id?: string; name: string; type?: string; content?: string; fields?: Record<string, string>; }
export interface Motif { id?: string; name: string; metaphor_unfolding?: string; bound_theme?: string; material_echoes?: string[]; naming_logic?: string; }
export interface Material { id: string; type: string; title?: string; content?: string; tags?: string; status?: string; }
export interface CharacterT {
  id?: string; name: string; motivation?: string; voice?: string;
  voice_samples?: string[]; core_contradiction?: string; wound?: string;
  lie?: string; want?: string; need?: string; arc?: string; fear?: string;
}
export interface Insight { id: string; summary: string; suggested_action?: string; severity?: string; }
export interface Imagination { id: string; raw_text: string; status?: string; }
export interface OptionSet { id: string; decision_point: string; options: string; }
export interface Volume { id: string; seq: number; title?: string; arc_goal?: string; }
export interface Segment { id: string; seq: number; text: string; created_by: string; citation_refs?: string; }
export interface Annotation { id: string; seq: number; quote: string; note: string; target: string; created_at?: string; }
export interface Highlight { id: string; seq: number; quote: string; color: string; created_at?: string; }
export interface Draft { content: string; prev_content: string; }
export interface Verdict { status: "aligned" | "soft_deviation" | "hard_violation"; reason: string; red_lines: { text: string; level: string }[]; }
export type ChapterAction = "continue" | "rewrite" | "expand";
// P1 暴露:质量/关系/状态/编排/线程/记忆/技能
export interface Quality {
  chapters: number; words: number; avg_slop_density: number;
  foreshadow: { planted: number; paid: number; abandoned: number; payoff_rate: number };
  consistency: { open_flags: number; weighted: number; by_class: Record<string, number>; score: number };
  weakest_chapters: { seq: number; words: number; slop_density: number; open_flags: number }[];
  cost: { calls: number; tokens: number; cost_usd: number };
}
export interface Relation { id: string; src_entity: string; dst_entity: string; relation: string; valid_from_chapter?: number | null; valid_to_chapter?: number | null; src_type?: string; dst_type?: string; relation_category?: string; weight?: number; directed?: number; }
export interface QualitySnapshot { words?: number; slop_density?: number; consistency_score?: number; foreshadow_payoff?: number; vocab_richness?: number; repetition_rate?: number; cost_usd?: number; created_at?: string; scope?: string; chapter_seq?: number; }
export interface CharState { id: string; chapter_seq: number; state_desc?: string; change_type?: string; }
export interface ChapterTask { id: string; work_id: string; seq: number; status: string; detail?: string; updated_at: string; next: string[]; }
export interface Thread { id: string; trigger: string; topic: string; messages: string; status: string; resolution?: string; created_at: string; }
export interface AgentMemory { id: string; namespace: string; key: string; value: string; confidence: number; work_id?: string | null; updated_at: string; }
export interface AgentSkill { id: string; name: string; spec: string; status: string; created_by: string; approved_by_human: number; created_at: string; }
export type ImagStatus = "captured" | "structured" | "scheduled" | "used" | "obsolete";

export const api = {
  works: () => req<Work[]>("/works"),
  createWork: (title: string) => post<{ work_id: string }>("/works", { title }),
  deleteWork: (w: string) => req<{ ok: boolean }>(`/works/${w}`, { method: "DELETE" }),
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
  plantForeshadow: (w: string, summary: string, chapter: number,
    opts: { importance?: string; promise?: string; ftype?: string } = {}) =>
    post<{ foreshadow_id: string }>(`/works/${w}/foreshadows`, {
      summary, chapter, importance: opts.importance ?? "normal",
      promise: opts.promise ?? "", ftype: opts.ftype ?? "伏笔",
    }),
  payoffForeshadow: (w: string, fid: string, chapter: number) =>
    post<{ state: string; payoff_chapter: number }>(`/works/${w}/foreshadows-status/${fid}/payoff`, { chapter }),
  editForeshadow: (w: string, fid: string, fields: { summary?: string; promise?: string; ftype?: string }) =>
    post<{ ok: boolean }>(`/works/${w}/foreshadows-status/${fid}/edit`, fields),
  flags: (w: string) => req<Flag[]>(`/works/${w}/consistency-flags`),
  insights: (w: string) => req<Insight[]>(`/works/${w}/insights?status=new`),
  actInsight: (w: string, id: string, act: "ack" | "dismiss") =>
    post<{ ok: boolean }>(`/works/${w}/insights/${id}/${act}`),
  review: (w: string) => post<{ new_insights: number }>(`/works/${w}/proactive-review`),
  pendingWrites: (w: string) => req<PendingWrite[]>(`/works/${w}/pending-writes`),
  approvePending: (w: string, id: string) =>
    post<{ status: string }>(`/works/${w}/pending-writes/${id}/approve`),
  rejectPending: (w: string, id: string) =>
    post<{ status: string }>(`/works/${w}/pending-writes/${id}/reject`),
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
  // B1 主编对话走 hermes：流式回复（tool=工具调用提示 / delta=回复片段 / done=完整回复+thread_id）
  streamChat: async (
    w: string, message: string,
    onEvent: (ev: { delta?: string; tool?: string; tool_args?: string }) => void,
    thread_id?: string, model?: string, signal?: AbortSignal,
  ): Promise<{ content: string; thread_id?: string }> => {
    const r = await fetch(`${BASE}/works/${w}/chat/stream`,
      { method: "POST", headers: H, body: JSON.stringify({ message, thread_id, model }), signal });
    if (!r.ok || !r.body) throw new ApiError(r.status, "对话流式连接失败");
    const reader = r.body.getReader(); const dec = new TextDecoder();
    let buf = ""; let result: { content: string; thread_id?: string } = { content: "" };
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n"); buf = parts.pop() ?? "";
      for (const p of parts) {
        const line = p.trim(); if (!line.startsWith("data:")) continue;
        try {
          const ev = JSON.parse(line.slice(5).trim());
          if (ev.error) throw new ApiError(502, ev.error);
          if (ev.done) result = { content: ev.content, thread_id: ev.thread_id };
          else onEvent(ev);
        } catch (e) { if (e instanceof ApiError) throw e; /* ignore parse */ }
      }
    }
    return result;
  },
  // P1 新增
  volumes: (w: string) => req<Volume[]>(`/works/${w}/volumes`),
  createVolume: (w: string, seq: number, title: string) =>
    post<{ volume_id: string }>(`/works/${w}/volumes`, { seq, title }),
  segments: (w: string, seq: number) => req<Segment[]>(`/works/${w}/chapters/${seq}/segments`),
  rebuildSegments: (w: string, seq: number) =>
    post<{ segments: number }>(`/works/${w}/chapters/${seq}/segments/rebuild`),
  // 划词交互:批注 / 高亮 / 段级改写
  annotations: (w: string, seq: number) => req<Annotation[]>(`/works/${w}/chapters/${seq}/annotations`),
  allAnnotations: (w: string) => req<Annotation[]>(`/works/${w}/annotations`),
  addAnnotation: (w: string, seq: number, quote: string, note: string, target: string) =>
    post<{ annotation_id: string }>(`/works/${w}/chapters/${seq}/annotations`, { quote, note, target }),
  delAnnotation: (w: string, id: string) =>
    req<{ ok: boolean }>(`/works/${w}/annotations/${id}`, { method: "DELETE" }),
  highlights: (w: string, seq: number) => req<Highlight[]>(`/works/${w}/chapters/${seq}/highlights`),
  addHighlight: (w: string, seq: number, quote: string, color: string) =>
    post<{ highlight_id: string }>(`/works/${w}/chapters/${seq}/highlights`, { quote, color }),
  delHighlight: (w: string, id: string) =>
    req<{ ok: boolean }>(`/works/${w}/highlights/${id}`, { method: "DELETE" }),
  rewritePassage: (w: string, seq: number, passage: string, instruction: string) =>
    post<{ rewritten: string }>(`/works/${w}/chapters/${seq}/rewrite-passage`, { passage, instruction }),
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
  addSetting: (w: string, name: string, type_ = "设定", description = "", fields: Record<string, string> = {}) =>
    post<{ setting_id: string }>(`/works/${w}/settings`, { name, type_, description, fields }),
  addCharacter: (w: string, name: string, motivation = "", extra: Partial<CharacterT> = {}) =>
    post<{ character_id: string }>(`/works/${w}/characters`, { name, motivation, ...extra }),
  motifs: (w: string) => req<Motif[]>(`/works/${w}/motifs`),
  addMotif: (w: string, m: Motif) => post<{ motif_id: string }>(`/works/${w}/motifs`, m),
  // Progressions:人物状态轨迹(charStates 见上方 P1 既有方法)
  addCharState: (w: string, character: string, chapter_seq: number, state_desc: string, change_type = "add") =>
    post<{ state_id: string }>(`/works/${w}/char-states`, { character, chapter_seq, state_desc, change_type }),
  // PlotThread:伏笔全状态(echoes/超期)
  foreshadowsStatus: (w: string) => req<ForeshadowStatus[]>(`/works/${w}/foreshadows-status`),
  addForeshadowEcho: (w: string, fid: string, chapter: number) =>
    post<{ echoes: number[] }>(`/works/${w}/foreshadows-status/${fid}/echo`, { chapter }),
  // 出场追踪
  appearances: (w: string, name: string) =>
    req<{ name: string; chapters: number[] }>(`/works/${w}/entities/${encodeURIComponent(name)}/appearances`),
  // AI 抽取设定(候选,不落库)
  extractEntities: (w: string, seq: number) =>
    post<ExtractResult>(`/works/${w}/chapters/${seq}/extract-entities`),
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
  // ── P1 暴露:质量 / 关系 / 角色状态 / 编排 / 深检 / 摄入 ──
  quality: (w: string) => req<Quality>(`/works/${w}/quality`),
  relations: (w: string) => req<Relation[]>(`/works/${w}/relations`),
  charStates: (w: string, name: string) => req<CharState[]>(`/works/${w}/characters/${encodeURIComponent(name)}/states`),
  task: (w: string, seq: number) => req<ChapterTask>(`/works/${w}/chapters/${seq}/task`),
  advanceTask: (w: string, seq: number, to: string, detail = "") =>
    post<ChapterTask>(`/works/${w}/chapters/${seq}/task/advance`, { to, detail }),
  deepCheck: (w: string, seq: number) => post<{ new_flags: number }>(`/works/${w}/chapters/${seq}/deep-check`),
  ingest: (w: string, seq: number) => post<Record<string, unknown>>(`/works/${w}/chapters/${seq}/ingest`),
  // ── P1 暴露:讨论线程 / 想象状态 ──
  threads: (w: string, status?: string) => req<Thread[]>(`/works/${w}/threads${status ? `?status=${status}` : ""}`),
  resolveThread: (w: string, tid: string) => post<{ ok: boolean }>(`/works/${w}/threads/${tid}/resolve`),
  setImagStatus: (w: string, iid: string, status: ImagStatus) =>
    post<{ status: string }>(`/works/${w}/imaginations/${iid}/status/${status}`),
  // ── P1 暴露:跨会话记忆 / 自我优化技能(须人审批)──
  agentMemory: (w: string, namespace?: string) =>
    req<AgentMemory[]>(`/works/${w}/agent-memory${namespace ? `?namespace=${namespace}` : ""}`),
  writeAgentMemory: (w: string, namespace: string, key: string, value: Record<string, unknown>, confidence = 1, scope: "owner" | "work" = "owner") =>
    post<{ memory_id: string | null; stored: boolean }>(`/works/${w}/agent-memory`, { namespace, key, value, confidence, scope }),
  agentSkills: (w: string, status?: string) =>
    req<AgentSkill[]>(`/works/${w}/agent-skills${status ? `?status=${status}` : ""}`),
  proposeSkill: (w: string, name: string, spec: Record<string, unknown> = {}) =>
    post<{ skill_id: string }>(`/works/${w}/agent-skills`, { name, spec }),
  actSkill: (w: string, sid: string, action: "approve" | "activate" | "retire") =>
    post<{ status: string }>(`/works/${w}/agent-skills/${sid}/${action}`),
  // ── P2 新增:质量历史 / 全书分析 ──
  analyzeWork: (w: string) => post<{ analyzed: number; relations: number; events: number; states: number }>(`/works/${w}/analyze`),
  qualityHistory: (w: string, scope = "global") => req<QualitySnapshot[]>(`/works/${w}/quality/history?scope=${scope}`),
};
