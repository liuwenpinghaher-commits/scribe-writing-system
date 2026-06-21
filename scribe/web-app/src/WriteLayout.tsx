/**
 * WriteLayout.tsx — 写作台,基于共享 WorkspaceShell。
 * 左轨=大纲;中区=正文;右轨能力=主编对话/设定圣经/伏笔/一致性/素材/脉络质量/记忆技能。
 * 「与主编对话」即右轨一个能力(渲染 Conversation);划词「讨论这段」自动开对话并带入引文。
 */
import { useState } from "react";
import { ListTree, MessagesSquare, BookMarked, Sparkles, ShieldAlert, Package, Activity, Brain, Users } from "lucide-react";
import { api } from "./api";
import { useData } from "./common";
import { Navigator } from "./Navigator";
import { Center } from "./Center";
import { Conversation } from "./Conversation";
import { Right } from "./Right";
import { InScenePanel } from "./InScenePanel";
import { WorkspaceShell, useStrPref, type RailCap } from "./WorkspaceShell";

export function WriteLayout({ work, rev, bump, title, seq, setSeq }: {
  work: string; rev: number; bump: () => void; title: string;
  seq: number | null; setSeq: (s: number | null) => void;
}) {
  const [leftActive, setLeftActive] = useStrPref("scribe.write.left", "outline");
  const [rightActive, setRightActive] = useStrPref("scribe.write.right", "");
  const [quote, setQuote] = useState("");

  const insights = useData(() => api.insights(work), [work, rev]);
  const pend = useData(() => api.pendingWrites(work), [work, rev]);
  const fores = useData(() => api.foreshadows(work), [work, rev]);
  const flags = useData(() => api.flags(work), [work, rev]);
  const chatBadge = (insights.data?.length ?? 0) + (pend.data?.length ?? 0);
  const foreBadge = fores.data?.filter((f) => f.state === "planted" || f.state === "triggered").length ?? 0;
  const flagBadge = flags.data?.length ?? 0;

  const discuss = (text: string) => { setQuote(text); setRightActive("chat"); };
  const goChat = () => setRightActive("chat");

  const pad = (node: React.ReactNode) => <div className="h-full overflow-auto p-3">{node}</div>;
  const inspector = (active: string) => () => pad(<Right work={work} rev={rev} bump={bump} active={active} />);

  const leftCaps: RailCap[] = [
    { key: "outline", label: "大纲树", icon: ListTree,
      render: () => pad(<Navigator work={work} rev={rev} bump={bump} currentSeq={seq} setSeq={setSeq} />) },
  ];
  const rightCaps: RailCap[] = [
    { key: "chat", label: "主编对话", icon: MessagesSquare, badge: chatBadge,
      render: () => pad(<Conversation work={work} rev={rev} bump={bump} quote={quote} onQuoteUsed={() => setQuote("")} />) },
    { key: "inscene", label: "本章在场", icon: Users,
      render: () => pad(<InScenePanel work={work} seq={seq} rev={rev} />) },
    { key: "bible", label: "设定圣经", icon: BookMarked, render: inspector("bible") },
    { key: "foreshadow", label: "伏笔", icon: Sparkles, badge: foreBadge, render: inspector("foreshadow") },
    { key: "flags", label: "一致性", icon: ShieldAlert, badge: flagBadge, render: inspector("flags") },
    { key: "material", label: "素材", icon: Package, render: inspector("material") },
    { key: "pulse", label: "脉络·质量", icon: Activity, render: inspector("pulse") },
    { key: "agent", label: "记忆·技能", icon: Brain, render: inspector("agent") },
  ];

  return (
    <WorkspaceShell ns="write"
      center={
        <div className="center-inner">
          <Center key={work} work={work} title={title} rev={rev} bump={bump} currentSeq={seq}
            onDiscuss={discuss} onGoChat={goChat} />
        </div>
      }
      left={{ caps: leftCaps, active: leftActive, onActive: setLeftActive }}
      right={{ caps: rightCaps, active: rightActive, onActive: setRightActive }}
    />
  );
}
