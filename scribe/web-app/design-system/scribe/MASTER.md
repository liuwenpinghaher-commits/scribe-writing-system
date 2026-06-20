# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Scribe — 人机协同长篇小说写作工作台
**Generated:** 2026-06-20 07:39:09
**Category:** Long-form Writing Workspace / Pro Editor Tool（非 Newsletter；工具自动分类有误，已人工纠正）
**Reference class:** Scrivener（binder/inspector）· Ulysses/iA Writer（专注阅读排版）· Sudowrite / NovelCrafter（AI 故事工具 + codex）· Linear（键盘优先、命令面板）· Google Docs（版本/建议）

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#7C3AED` | `--color-primary` |
| On Primary | `#FFFFFF` | `--color-on-primary` |
| Secondary | `#6366F1` | `--color-secondary` |
| Accent/CTA | `#0891B2` | `--color-accent` |
| Background | `#0F172A` | `--color-background` |
| Foreground | `#FFFFFF` | `--color-foreground` |
| Muted | `#171939` | `--color-muted` |
| Border | `rgba(255,255,255,0.08)` | `--color-border` |
| Destructive | `#DC2626` | `--color-destructive` |
| Ring | `#7C3AED` | `--color-ring` |

**Color Notes:** Editor violet + filter cyan on dark

### Typography（已纠正：工具误配希伯来字体；长篇写作工具应「UI 无衬线 + 正文衬线阅读」双轨）

- **UI / 标题字体:** Inter + Noto Sans SC（界面、菜单、按钮、侧栏）
- **正文 / 阅读字体:** Source Serif 4 + Noto Serif SC（章节正文、diff、阅读视图 —— 长文阅读衬线更省力，对标 iA Writer / Medium）
- **数字（用量/字数/版本号）:** tabular-nums，避免跳动
- **Mood:** editorial, calm, high-readability, 中英混排, professional

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@400;600&display=swap');
/* --font-ui: 'Inter','Noto Sans SC',system-ui,sans-serif;
   --font-prose: 'Source Serif 4','Noto Serif SC',Georgia,serif; */
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #0891B2;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #7C3AED;
  border: 2px solid #7C3AED;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #0F172A;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #7C3AED;
  outline: none;
  box-shadow: 0 0 0 3px #7C3AED20;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Minimalism & Swiss Style

**Keywords:** Clean, simple, spacious, functional, white space, high contrast, geometric, sans-serif, grid-based, essential

**Best For:** Enterprise apps, dashboards, documentation sites, SaaS platforms, professional tools

**Key Effects:** Subtle hover (200-250ms), smooth transitions, sharp shadows if any, clear type hierarchy, fast loading

### Page Pattern（已纠正：这是应用工作台，不是落地页）

**Pattern Name:** 三栏工作台 Binder · Editor · Inspector（Scrivener 范式）

- **左栏 Navigator:** 作品切换器（折叠）+ 卷/章大纲树（状态点、⚠ 角标、拖拽排序）
- **中栏 Editor（专注圣地）:** 北极星常驻条 → 草稿/diff 裁决 → 段落阅读视图；一次只暴露「当前写作动作」，不堆叠导航
- **右栏 Inspector（上下文 Tab）:** 主编札记(置顶) · 设定圣经 · 伏笔 · 一致性 · 素材 · 脉络/质量 · 主编对话/讨论线程 · 记忆与技能
- **全局:** ⌘K 命令面板（暴露所有动作，不止跳转）· ⌘I 捕获想象 · ⌘⇧F 专注 · ? 快捷键帮助 · SSE 主动刷新

---

## Anti-Patterns (Do NOT Use)

- ❌ Complex signup
- ❌ No preview

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
