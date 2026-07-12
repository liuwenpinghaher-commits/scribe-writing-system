# Hermes 管理台入口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 设置中心接入 Hermes 官方 Dashboard(状态/一键启动/按域深链),网关卡片显示各自当前主模型;scribe3 不重建任何 Hermes 管理能力。

**Architecture:** 后端三端点(dashboard 探活/启动、model-summary 只读解析三份 config.yaml 的 model 节);前端网关分区顶部一张入口卡 + 状态卡主模型行。密钥不解析不返回;启动走 nohup+轮询铁律。

**Tech Stack:** FastAPI + React;spec:`docs/superpowers/specs/2026-07-12-hermes-dashboard-entry-design.md`。

**仓库纪律**:测试命令/台账登记/commit 规范/红线(不真启进程、不碰真实 ~/.hermes)同设置中心计划;后端 `scribe3/.venv/bin/python -m pytest`,前端 `cd scribe3/web && npx vitest run`。

---

### Task 1:后端 dashboard status/start 端点

**Files:** Modify `scribe3/settings.py`(REGISTRY 加 1 项)、`scribe3/app.py`、`scribe3/tests/test_consistency.py`;Test `scribe3/tests/test_gateway_api.py`(追加)

- [ ] Step 1 失败测试(test_gateway_api.py 追加,沿用 client fixture):

```python
def test_dashboard_status(client, monkeypatch):
    monkeypatch.setattr("httpx.get", lambda url, timeout: type("R", (), {"status_code": 200})())
    r = client.get("/gateway/dashboard/status")
    assert r.status_code == 200 and r.json()["online"] is True
    assert "9119" in r.json()["url"]


def test_dashboard_start_polls_and_reports(client, monkeypatch):
    ran = {}
    monkeypatch.setattr("os.path.isfile", lambda p: True)
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    monkeypatch.setattr("httpx.get", lambda url, timeout: type("R", (), {"status_code": 200})())
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/gateway/dashboard/start")
    assert r.status_code == 200 and r.json()["online"] is True
    assert "nohup" in ran["cmd"] and "dashboard --no-open" in ran["cmd"]


def test_dashboard_start_missing_bin_fails_fast(client, monkeypatch):
    ran = {}
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: ran.setdefault("cmd", a[0]))
    from scribe3 import settings as S
    S.put_setting("gateway.hermes_bin", "/nope/hermes")
    r = client.post("/gateway/dashboard/start")
    assert r.json()["online"] is False and "cmd" not in ran
```

- [ ] Step 2 跑红(404)
- [ ] Step 3 实现:REGISTRY 加 `Setting("gateway.dashboard_url", "gateway", "str", "http://127.0.0.1:9119", "hot", "Dashboard 地址", "官方管理台,hermes dashboard 默认端口")`;app.py 两端点(/gateway/restart 之后,探活语义/预检/nohup/30s 轮询与 gateway_restart 同型,cmd = `nohup {hermes} dashboard --no-open >> /tmp/scribe3-hermes-dashboard.log 2>&1 &`);台账登记 `("POST", "/gateway/dashboard/start")`(注释:拉起本机管理台进程,预检+轮询,不接受任何请求参数)
- [ ] Step 4 跑 `test_gateway_api.py + test_consistency.py + test_settings_gate.py` 绿
- [ ] Step 5 Commit `feat: Hermes Dashboard 探活与一键启动端点`

### Task 2:后端 model-summary(只读)

**Files:** Modify `scribe3/gateway_files.py`、`scribe3/app.py`;Test `scribe3/tests/test_gateway_files.py`(追加)

- [ ] Step 1 失败测试:

```python
def test_model_summary_three_gateways(home):
    # root 配置(写作 :8642)在 HERMES_HOME 根;profile 配置已由 home fixture 建
    (home / "config.yaml").write_text(
        "model:\n  provider: custom\n  base_url: https://x/v3\n  api_key: sk-root\n  default: doubao-seed-2.0-pro\n",
        encoding="utf-8")
    d = home / "profiles" / "scribe3"
    (d / "config.yaml").write_text(
        "model:\n  provider: custom\n  default: doubao-seed-2.0-pro\n", encoding="utf-8")
    from scribe3 import gateway_files as gf
    rows = gf.model_summary()
    by = {r["gateway"]: r for r in rows}
    assert by["default"]["default_model"] == "doubao-seed-2.0-pro"
    assert by["default"]["provider"] == "custom"
    assert by["scribe3_write"]["default_model"] is None   # 文件缺 model 节/不存在 → None,fail-soft
    assert "sk-root" not in str(rows)                      # 密钥绝不出现


def test_root_config_still_not_writable(home):
    from scribe3 import gateway_files as gf
    import pytest
    with pytest.raises(gf.NotAllowedError):
        gf.write_file("root/config.yaml", "x", base_sha256="")
```

- [ ] Step 2 跑红(AttributeError: model_summary)
- [ ] Step 3 实现 `gateway_files.model_summary()`:对 `[("default", HOME/config.yaml), ("scribe3", …), ("scribe3_write", …)]` 三份文件,逐行正则提取 `model:` 节下的 `provider:` 与 `default:`(不解析 api_key/base_url,不引入 yaml 库;文件缺失/无 model 节 → provider/default_model 为 None);写白名单 `_PROFILES/_NAMES` 完全不动。app.py 加 `GET /gateway/model-summary` 返回 `{"gateways": model_summary()}`(只读不登记)
- [ ] Step 4 跑 `test_gateway_files.py` 全绿
- [ ] Step 5 Commit `feat: 三网关主模型只读摘要(root 配置只读解析,写面不变)`

### Task 3:前端入口卡 + 主模型行

**Files:** Modify `scribe3/web/src/api.js`(3 方法:dashboardStatus/dashboardStart/gatewayModelSummary,raw 变体)、`scribe3/web/src/settings/GatewaySection.jsx`;Test `scribe3/web/src/settings/__tests__/gatewaySection.test.jsx`(追加)

- [ ] Step 1 失败测试(apiMock 补三方法):

```jsx
  it('管理台卡:未运行→启动按钮走确认;在线→深链按钮组', async () => {
    apiMock.dashboardStatus.mockResolvedValueOnce({ online: false, url: 'http://127.0.0.1:9119' })
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('Hermes 管理台')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: '启动管理台' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.dashboardStart).toHaveBeenCalled())
  })

  it('在线时渲染五个深链且带 profile 参数', async () => {
    apiMock.dashboardStatus.mockResolvedValue({ online: true, url: 'http://127.0.0.1:9119' })
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('模型与服务商')).toBeTruthy())
    const a = screen.getByRole('link', { name: '模型与服务商' })
    expect(a.getAttribute('href')).toBe('http://127.0.0.1:9119/models?profile=scribe3')
    expect(a.getAttribute('target')).toBe('_blank')
  })

  it('状态卡显示主模型行', async () => {
    apiMock.gatewayModelSummary.mockResolvedValue({ gateways: [
      { gateway: 'default', provider: 'custom', default_model: 'doubao-seed-2.0-pro' }] })
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText(/doubao-seed-2.0-pro/)).toBeTruthy())
  })
```

- [ ] Step 2 跑红
- [ ] Step 3 实现:api.js 三方法(jraw/postRaw);GatewaySection 顶部 `DashboardCard`(挂载拉 status;未运行:状态灰点+「启动管理台」→ConfirmDialog→dashboardStart→结果如实显示+重拉;在线:绿点+深链 `<a target="_blank" rel="noreferrer">`×5:模型与服务商 `/models?profile=scribe3`、Skills `/skills?profile=scribe3`、MCP `/mcp?profile=scribe3`、Cron `/cron`、会话 `/sessions?profile=scribe3`;卡底一行小字「管理台为机器级,侧边栏可切 profile;深链默认 scribe3」);StatusCard 每网关行加 `主模型:{provider} · {default_model}`(summary fail-soft 省略)
- [ ] Step 4 `npx vitest run src/settings/` + 全量绿
- [ ] Step 5 Commit `feat: Hermes 管理台入口卡(状态/启动/深链)+ 网关主模型行`

### Task 4:回归 + 真机验收 + 文档

- [ ] Step 1 后端全量 pytest 绿;前端全量 vitest 绿
- [ ] Step 2 真机(控制器亲自做):`GET /gateway/model-summary` 返回三网关真实主模型;启动真 Dashboard(经界面或 API)→ 状态灯绿 → 深链打开 Models 页可见 profile 切换器;截图留档
- [ ] Step 3 DEPLOY.md「设置中心」小节补一段:Hermes 深度管理(模型/skill/MCP/cron)走官方 Dashboard,入口在设置中心网关区;dashboard 进程与端口说明
- [ ] Step 4 Commit `docs: Hermes 管理台入口部署说明` + 汇报
