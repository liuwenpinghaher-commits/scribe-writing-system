.PHONY: e2e-det e2e-frontend e2e-real e2e-quality-real e2e-craft-gates test-mcp test-web-readonly test-baseline test-author-paths test-craft check-clean

check-clean:        ## 全仓敏感信息零命中扫描(IP/域名/本地家目录/私钥)
	@! grep -rnI -E '82\.157\.130\.140|10\.144\.144\.[12]|qing\.blue|/home/chris|/home/ubuntu|/Users/miaoma|13601092810|13301042810|(^|[^a-zA-Z0-9_-])(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|LTAI[a-zA-Z0-9]{12,}|AIza[0-9A-Za-z_-]{30,})' \
	  --exclude=Makefile --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=.pytest_cache . \
	  && echo "ZERO_SENSITIVE_HITS"

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
	  scribe3/tests/test_craft.py \
	  scribe3/tests/test_craft_rule.py \
	  scribe3/tests/test_content_quality.py -q

e2e-det:            ## 确定性档:六类失效模式(秒级,不烧网关,进 CI)
	scribe3/.venv/bin/python -m pytest scribe3/tests/e2e -q

e2e-frontend:       ## 前端 L2 冒烟:独立临时后端(不碰生产,进 CI)
	scripts/e2e_ci.sh

e2e-real:           ## 真调档:仅 Hermes 连通冒烟 full_journey(≠质量验收)
	scripts/e2e_real.sh

e2e-quality-real:   ## 本机真调:参考→合同→正文→十维三轴→作者裁决(非 CI mock)
	cd scribe3/web && node e2e/quality_reference_author_journey.mjs

e2e-craft-gates:    ## 反面书必须红(卫生轨对照);需本机 work 或默认 book_b4e72480
	scribe3/.venv/bin/python -m scribe3.tools.craft_gate_cli --work book_b4e72480 --expect-fail
