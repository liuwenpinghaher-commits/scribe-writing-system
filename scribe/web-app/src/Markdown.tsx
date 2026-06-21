/**
 * Markdown.tsx — 主编回复的 markdown 富格式渲染。
 * react-markdown + remark-gfm(表格/删除线/任务列表),手工映射元素样式(项目无 typography 插件)。
 * 流式中 children 增量变化,react-markdown 会随每帧重渲,部分 markdown 也能优雅降级。
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "./lib/utils";

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("text-sm leading-relaxed break-words", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          del: ({ children }) => <del className="opacity-70">{children}</del>,
          h1: ({ children }) => <h1 className="text-base font-bold mt-3 mb-1.5 first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="text-[0.95rem] font-bold mt-2.5 mb-1 first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1 first:mt-0">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-border pl-3 my-2 text-muted-foreground italic">{children}</blockquote>
          ),
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="underline text-primary hover:opacity-80">{children}</a>
          ),
          hr: () => <hr className="my-2.5 border-border" />,
          code: ({ className: cls, children }) => {
            const block = /language-/.test(cls || "");
            return block ? (
              <code className="block p-2 my-2 rounded-md bg-foreground/10 text-xs font-mono overflow-x-auto whitespace-pre">{children}</code>
            ) : (
              <code className="px-1 py-0.5 rounded bg-foreground/10 text-[0.85em] font-mono">{children}</code>
            );
          },
          pre: ({ children }) => <pre className="my-0">{children}</pre>,
          table: ({ children }) => (
            <div className="overflow-x-auto my-2"><table className="border-collapse text-xs w-full">{children}</table></div>
          ),
          th: ({ children }) => <th className="border border-border px-2 py-1 font-semibold text-left">{children}</th>,
          td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
