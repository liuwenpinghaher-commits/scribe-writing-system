.PHONY: e2e-det e2e-frontend e2e-real test-mcp test-web-readonly test-baseline

test-mcp:           ## MCP 写门控/假绿回归(PR 最低)
	scribe3/.venv/bin/python -m pytest scribe3/tests/test_mcp.py -q

test-web-readonly:  ## Codex 只读 + chief 种子(PR 前端最低)
	cd scribe3/web && npm test -- src/views/CodexView.readonly.test.jsx src/lib/hermesRunIntent.test.js

test-baseline: test-mcp test-web-readonly  ## 文档 PR_TEST_BASELINE 默认集

e2e-det:            ## 确定性档:六类失效模式(秒级,不烧网关,进 CI)
	scribe3/.venv/bin/python -m pytest scribe3/tests/e2e -q

e2e-frontend:       ## 前端 L2 冒烟:独立临时后端(不碰生产,进 CI)
	scripts/e2e_ci.sh

e2e-real:           ## 真调档:真网关完整旅程(本机需 Hermes 凭证)
	scripts/e2e_real.sh
