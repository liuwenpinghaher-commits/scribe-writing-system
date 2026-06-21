/**
 * CodexChat.tsx — 设定库里的「与主编聊设定」窗口。
 * 复用主编 agentic 对话(走 /chat/stream,主编自带 scribe2 工具):
 * 可对话式查/建/改设定——「九原渡有哪些母题?」「给柳娘补三条声音样本」「新建力量体系三不渡,代价是…」。
 * 主编读工具自动答,写工具(建/改)经 B3 审批落库。
 */
import { useEffect, useRef, useState } from "react";
import { Loader2, Send, Sparkles } from "lucide-react";
import { api } from "@/api";
import { errMsg, useToast } from "@/common";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/Markdown";
import { cn } from "@/lib/utils";

interface Msg { role: "user" | "editor"; content: string; tool?: string }

const SUGGESTIONS = [
  "这本书有哪些母题?够不够撑起主题?",
  "帮我给主角补三条声音样本(根据已写正文)",
  "新建力量体系「三不渡」,写清代价和会出什么乱子",
  "渡叔的核心矛盾够尖锐吗?帮我深化",
];

export function CodexChat({ work, onChanged }: { work: string; onChanged?: () => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [hint, setHint] = useState("");
  const toast = useToast();
  const bottomRef = useRef<HTMLDivElement>(null);
  const threadRef = useRef<string | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, thinking]);

  const send = async (text0?: string) => {
    const text = (text0 ?? input).trim();
    if (!text || thinking) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", content: text }, { role: "editor", content: "" }]);
    setThinking(true); setHint("");
    let wrote = false;
    try {
      const r = await api.streamChat(work, text, (ev) => {
        if (ev.tool) {
          if (/upsert|add_|set_|plant|advance|create/.test(ev.tool)) wrote = true;
          setHint(`主编正在${/list|get|search|appearances/.test(ev.tool) ? "查" : "改"}设定…`);
          setMsgs((m) => {
            const last = m[m.length - 1];
            if (!last || last.role !== "editor") return m;
            return [...m.slice(0, -1), { ...last, tool: ev.tool }];
          });
        }
        if (ev.delta) {
          setHint("");
          setMsgs((m) => {
            const last = m[m.length - 1];
            if (!last || last.role !== "editor") return m;
            return [...m.slice(0, -1), { ...last, content: last.content + ev.delta }];
          });
        }
      }, threadRef.current);
      threadRef.current = r.thread_id ?? threadRef.current;
      setMsgs((m) => {
        const last = m[m.length - 1];
        if (!last || last.role !== "editor") return m;
        return [...m.slice(0, -1), { ...last, content: r.content || last.content }];
      });
      if (wrote) onChanged?.();  // 主编改了设定 → 刷新列表
    } catch (e) {
      toast(errMsg(e), "err");
      setMsgs((m) => m.slice(0, -2));
    } finally { setThinking(false); }
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {msgs.length === 0 ? (
          <div className="flex flex-col gap-3 pt-2">
            <div className="flex items-center gap-2 text-sm text-foreground">
              <Sparkles size={15} className="text-primary" /> 与主编聊设定
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              让主编帮你查、建、改任何设定。它会调真实数据回答,改动经审批落库。试试:
            </p>
            <div className="flex flex-col gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="text-left text-xs rounded-md border border-border px-2.5 py-1.5 text-muted-foreground hover:text-foreground hover:border-primary transition-colors">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {msgs.map((m, i) => {
              if (m.role === "editor" && !m.content && !m.tool) return null;
              const isUser = m.role === "user";
              return (
                <div key={i} className={cn("flex flex-col", isUser ? "items-end" : "items-start")}>
                  {m.tool && <span className="text-[10px] text-muted-foreground mb-0.5">🔧 {m.tool.replace("mcp_scribe2_", "")}</span>}
                  <div className={cn("max-w-[88%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
                    isUser ? "bg-primary text-primary-foreground rounded-br-sm" : "bg-muted text-foreground rounded-bl-sm")}>
                    {isUser ? <span className="whitespace-pre-wrap">{m.content}</span> : <Markdown>{m.content}</Markdown>}
                  </div>
                </div>
              );
            })}
            {thinking && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 size={13} className="animate-spin" /> {hint || "主编思考中…"}
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2 p-2.5 border-t border-border">
        <Input ref={inputRef} value={input} placeholder="让主编查/建/改设定…（Enter 发送）" className="h-8 text-sm"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          disabled={thinking} />
        <Button size="sm" className="h-8 shrink-0" onClick={() => send()} disabled={thinking || !input.trim()}>
          <Send size={14} />
        </Button>
      </div>
    </div>
  );
}
