.PHONY: e2e-det e2e-frontend e2e-real e2e-craft-gates test-mcp test-web-readonly test-baseline test-author-paths test-craft

test-mcp:           ## MCP 写门控/假绿回归(PR 最低)
	scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q

test-web-readonly:  ## Codex 只读 + chief 种子(PR 前端最低)
	cd scribe3/web && npm test -- src/views/CodexView.readonly.test.jsx src/lib/hermesRunIntent.test.js

test-baseline: test-mcp test-web-readonly  ## 文档 PR_TEST_BASELINE 默认集

test-author-paths:  ## 作者主路径:MCP/emergency/P0 素材结构
	scribe3/.venv/bin/python -m pytest \
	  scribe3/tests/test_mcp.py \
	  scribe3/tests/test_emergency_rest_write.py \
	  scribe3/tests/test_p0_author_paths.py -q

test-craft:         ## 工艺卫生 + 内容质量单测(闸绿≠质量过)
	scribe3/.venv/bin/python -m pytest \
	  scribe3/tests/test_craft_compliance_gates.py \
	  scribe3/tests/test_content_quality.py -q

e2e-det:            ## 确定性档:六类失效模式(秒级,不烧网关,进 CI)
	scribe3/.venv/bin/python -m pytest scribe3/tests/e2e -q

e2e-frontend:       ## 前端 L2 冒烟:独立临时后端(不碰生产,进 CI)
	scripts/e2e_ci.sh

e2e-real:           ## 真调档:仅 Hermes 连通冒烟 full_journey(≠质量验收)
	scripts/e2e_real.sh

e2e-craft-gates:    ## 反面书必须红(卫生轨对照);需本机 work 或默认 book_b4e72480
	scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work book_b4e72480 --expect-fail
