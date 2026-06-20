import { useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  RadialBarChart,
  RadialBar,
} from "recharts";
import { BarChart3, TrendingUp } from "lucide-react";
import { api } from "@/api";
import type { Quality, QualitySnapshot } from "@/api";
import { useData } from "@/common";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";

// ── 图表颜色配置 ──
const trendConfig: ChartConfig = {
  slop_density: { label: "AI腔密度", color: "var(--chart-5)" },
  consistency_score: { label: "一致性分", color: "var(--chart-1)" },
  foreshadow_payoff: { label: "伏笔回收率", color: "var(--chart-2)" },
};

const weakConfig: ChartConfig = {
  slop_density: { label: "AI腔密度", color: "var(--chart-5)" },
};

const radialConfig: ChartConfig = {
  consistency: { label: "一致性", color: "var(--chart-1)" },
  foreshadow: { label: "伏笔回收", color: "var(--chart-2)" },
  slop: { label: "AI腔(低为优)", color: "var(--chart-5)" },
};

// ── 格式化工具 ──
function pct(v: number | undefined) {
  if (v == null) return "—";
  return (v * 100).toFixed(1) + "%";
}
function num(v: number | undefined, digits = 2) {
  if (v == null) return "—";
  return v.toFixed(digits);
}
function shortDate(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// ── 大数字卡 ──
function MetricCard({
  label,
  value,
  sub,
  good,
}: {
  label: string;
  value: string;
  sub?: string;
  good?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardDescription className="text-xs">{label}</CardDescription>
      </CardHeader>
      <CardContent>
        <p
          className={[
            "text-3xl font-semibold tabular-nums leading-none",
            good === true
              ? "text-primary"
              : good === false
              ? "text-destructive"
              : "text-foreground",
          ].join(" ")}
        >
          {value}
        </p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── 质量趋势卡 ──
function TrendCard({ snapshots }: { snapshots: QualitySnapshot[] }) {
  const data = snapshots.map((s, i) => ({
    idx: shortDate(s.created_at) || `#${i + 1}`,
    slop_density: +(s.slop_density ?? 0).toFixed(4),
    consistency_score: +(s.consistency_score ?? 0).toFixed(3),
    foreshadow_payoff: +(s.foreshadow_payoff ?? 0).toFixed(3),
  }));

  return (
    <Card className="col-span-2">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <TrendingUp size={14} className="text-primary" />
          质量趋势
        </CardTitle>
        <CardDescription className="text-xs">随时间的 AI腔密度 / 一致性 / 伏笔回收率</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={trendConfig} className="h-52 w-full">
          <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} />
            <XAxis
              dataKey="idx"
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Area
              type="monotone"
              dataKey="slop_density"
              stroke="var(--chart-5)"
              fill="var(--chart-5)"
              fillOpacity={0.15}
              strokeWidth={1.5}
              dot={data.length <= 6 ? { r: 3 } : false}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="consistency_score"
              stroke="var(--chart-1)"
              fill="var(--chart-1)"
              fillOpacity={0.12}
              strokeWidth={1.5}
              dot={data.length <= 6 ? { r: 3 } : false}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="foreshadow_payoff"
              stroke="var(--chart-2)"
              fill="var(--chart-2)"
              fillOpacity={0.12}
              strokeWidth={1.5}
              dot={data.length <= 6 ? { r: 3 } : false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

// ── 每章 AI腔分布卡 ──
function SlopBarCard({ quality }: { quality: Quality }) {
  const chapters = quality.weakest_chapters;
  const data = [...chapters]
    .sort((a, b) => a.seq - b.seq)
    .map((c) => ({
      ch: `第${c.seq}章`,
      slop_density: +c.slop_density.toFixed(4),
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">每章 AI腔分布</CardTitle>
        <CardDescription className="text-xs">slop_density 分布(最弱章节)</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={weakConfig} className="h-44 w-full">
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.4} />
            <XAxis
              dataKey="ch"
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="slop_density" fill="var(--chart-5)" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}

// ── 最弱章排行卡 ──
function WeakestChaptersCard({
  quality,
  work,
}: {
  quality: Quality;
  work: string;
}) {
  const sorted = [...quality.weakest_chapters].sort(
    (a, b) => b.slop_density - a.slop_density
  );
  const top = sorted.slice(0, 8);

  const jump = (seq: number) => {
    location.hash = `#/work/${work}/write/ch/${seq}`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">最弱章排行</CardTitle>
        <CardDescription className="text-xs">按 AI腔密度降序;点击跳转</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1 pt-0">
        {top.length === 0 ? (
          <p className="text-xs text-muted-foreground py-3 text-center">暂无数据</p>
        ) : (
          top.map((c) => {
            const pctVal = (c.slop_density * 100).toFixed(1);
            const barW = Math.min(100, c.slop_density * 500);
            return (
              <button
                key={c.seq}
                onClick={() => jump(c.seq)}
                className="group flex w-full items-center gap-2 rounded px-2 py-1.5 text-left transition-colors hover:bg-accent"
              >
                <span className="w-12 shrink-0 text-xs text-muted-foreground tabular-nums">
                  第{c.seq}章
                </span>
                <div className="relative flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 rounded-full bg-destructive/70"
                    style={{ width: `${barW}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-xs tabular-nums text-destructive/80 font-medium">
                  {pctVal}%
                </span>
                {c.open_flags > 0 && (
                  <span className="shrink-0 rounded bg-destructive/10 px-1 text-[10px] text-destructive">
                    {c.open_flags}条
                  </span>
                )}
              </button>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

// ── 当下分径向卡 ──
function RadialScoreCard({ quality }: { quality: Quality }) {
  const { consistency, foreshadow, avg_slop_density } = quality;

  // 径向图数据:值归一化到 0-100 用于展示
  const radialData = [
    {
      name: "一致性",
      value: Math.round(consistency.score * 100),
      fill: "var(--chart-1)",
    },
    {
      name: "伏笔回收",
      value: Math.round(foreshadow.payoff_rate * 100),
      fill: "var(--chart-2)",
    },
    {
      name: "AI腔(低优)",
      // 越低越好:展示为 (1-density) * 100
      value: Math.max(0, Math.round((1 - avg_slop_density) * 100)),
      fill: "var(--chart-5)",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">当下综合分</CardTitle>
        <CardDescription className="text-xs">一致性 / 伏笔回收 / 干净度</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={radialConfig} className="h-44 w-full">
          <RadialBarChart
            data={radialData}
            innerRadius={30}
            outerRadius={80}
            startAngle={90}
            endAngle={-270}
          >
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent nameKey="name" hideLabel />}
            />
            <RadialBar dataKey="value" background isAnimationActive={false} />
          </RadialBarChart>
        </ChartContainer>
        {/* 数字摘要 */}
        <div className="mt-2 grid grid-cols-3 gap-1 text-center">
          <div>
            <p className="text-lg font-semibold tabular-nums text-primary">
              {pct(consistency.score)}
            </p>
            <p className="text-[10px] text-muted-foreground">一致性</p>
          </div>
          <div>
            <p className="text-lg font-semibold tabular-nums text-primary">
              {pct(foreshadow.payoff_rate)}
            </p>
            <p className="text-[10px] text-muted-foreground">伏笔回收</p>
          </div>
          <div>
            <p className="text-lg font-semibold tabular-nums text-destructive">
              {num(avg_slop_density, 3)}
            </p>
            <p className="text-[10px] text-muted-foreground">AI腔密度</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── 顶部统计条 ──
function StatsStrip({ quality }: { quality: Quality }) {
  const { cost, foreshadow, consistency, chapters, words } = quality;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <MetricCard
        label="章节数"
        value={String(chapters)}
        sub={`${words.toLocaleString()} 字`}
      />
      <MetricCard
        label="伏笔数"
        value={`${foreshadow.paid}/${foreshadow.planted}`}
        sub={`回收率 ${pct(foreshadow.payoff_rate)}`}
        good={foreshadow.payoff_rate >= 0.5}
      />
      <MetricCard
        label="一致性"
        value={pct(consistency.score)}
        sub={`${consistency.open_flags} 条待处理`}
        good={consistency.score >= 0.7}
      />
      <MetricCard
        label="分析成本"
        value={`$${cost.cost_usd.toFixed(3)}`}
        sub={`${cost.calls} 次调用 · ${cost.tokens.toLocaleString()} tokens`}
      />
    </div>
  );
}

// ── 主视图 ──
export function InsightView({ work }: { work: string }) {
  const quality = useData(() => api.quality(work), [work]);
  const history = useData(() => api.qualityHistory(work), [work]);
  const [analyzing, setAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await api.analyzeWork(work);
      quality.reload();
      history.reload();
    } finally {
      setAnalyzing(false);
    }
  };

  const loading = quality.loading || history.loading;
  const error = quality.error || history.error;

  // 空状态判断:无章节或无快照
  const isEmpty =
    !loading &&
    !error &&
    (quality.data == null ||
      (quality.data.words === 0 && (history.data == null || history.data.length === 0)));

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* 顶部工具条 */}
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 py-2">
        <span className="text-sm font-medium text-foreground">质量仪表盘</span>
        <div className="flex-1" />
        <button
          className="rounded-md border border-border bg-background px-3 py-1 text-xs text-foreground transition-colors hover:bg-accent disabled:opacity-50"
          disabled={analyzing}
          onClick={handleAnalyze}
        >
          {analyzing ? "分析中…" : "重新分析全书"}
        </button>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-auto px-4 py-4">
        <StateBoundary
          loading={loading}
          error={error}
          empty={isEmpty}
          onRetry={() => { quality.reload(); history.reload(); }}
          emptyNode={
            <div className="flex h-full min-h-64 items-center justify-center">
              <Empty
                icon={<BarChart3 />}
                title="还没有质量数据"
                hint="写几章并定稿，或点「分析全书」让主编扫描全部章节"
                action={{
                  label: analyzing ? "分析中…" : "分析全书",
                  onClick: handleAnalyze,
                }}
              />
            </div>
          }
        >
          {quality.data && (
            <div className="space-y-4">
              {/* 顶部统计条 */}
              <StatsStrip quality={quality.data} />

              {/* 图表网格 */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {/* 质量趋势:占满两列 */}
                {history.data && history.data.length > 0 ? (
                  <TrendCard snapshots={history.data} />
                ) : (
                  <Card className="col-span-2">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-sm">
                        <TrendingUp size={14} className="text-primary" />
                        质量趋势
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="py-6 text-center text-xs text-muted-foreground">
                        分析后将显示趋势图
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* 每章 AI腔分布 */}
                {quality.data.weakest_chapters.length > 0 ? (
                  <SlopBarCard quality={quality.data} />
                ) : (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">每章 AI腔分布</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="py-6 text-center text-xs text-muted-foreground">
                        暂无章节数据
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* 最弱章排行 */}
                <WeakestChaptersCard quality={quality.data} work={work} />

                {/* 当下分 */}
                <RadialScoreCard quality={quality.data} />
              </div>
            </div>
          )}
        </StateBoundary>
      </div>
    </div>
  );
}
