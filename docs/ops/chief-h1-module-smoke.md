# 主编 H1 能力模型 · demo 冒烟清单

设计：`docs/plans/2026-08-11-chief-module-generation-skill-vs-mcp.md`  
公网：`https://tonglu.example.com`

## 前置

1. 登录 demo 作者账号  
2. 打开有章作品 → 章工作台  

## 检查项

1. **种子点名**  
   - 大纲 tab「让主编写大纲」→ 输入/气泡含 `s3_patch_chapter_plan` 且含禁止 `s3_save_chapter` 完脚手架  
2. **resolve 正向**  
   ```bash
   curl -sS -X POST 'https://tonglu.example.com/api/orchestration/resolve?work=main' \
     -H 'Content-Type: application/json' -H "Cookie: …" \
     -d '{"message":"请更新第1章大纲并使用工具 s3_patch_chapter_plan 提交写入提案","chapter":1,"phase":"outline","activate":true}'
   ```  
   期望：`package.domain==chapter.outline`、`use_world_write_run==true`、`write_tools` 含 plan、`instruction_suffix` 非空  
3. **resolve 负向评分卡**  
   message=`请帮我解读本章评分卡` → domain=`aux.scorecard`（或非 intent.northstar）、无 `s3_set_intent` write  
4. **负向经验**  
   message=`经验复盘六格` → 非 `chapter.beats` 写  
5. **GATE-B 只读**  
   MetaPane 写前齐套可见 B1/B2/B3（不要求本步改阈值）  
6. **辅助面文案**  
   评分卡/简报/经验复盘标明只读派生；CTA 导向大纲/伏笔/意图，不出现「生成评分卡」

## 非目标

- outline/beats 硬 Hermes profile（PR-H）  
- assemble envelope 裁剪（PR-6）  
- 全章 LLM 重写文学分  
