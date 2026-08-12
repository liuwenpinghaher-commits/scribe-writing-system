# Changefeed 多 worker 契约（GAP-18）

## 生产默认

- 单 uvicorn worker：`ChangefeedCacheWorker` 直接启动。
- 多 worker：设 `SCRIBE3_CHANGEFEED_LEADER_ELECTION=1`，仅 leader 轮询。

## Leader election

- 实现：`scribe3/changefeed_leader.py` 文件租约。
- 路径：`SCRIBE3_CHANGEFEED_LEADER_PATH` 或 `$SCRIBE3_DATA_DIR/changefeed_leader.lease`。
- TTL 默认 30s；租约失败 **fail-open** 为 leader（避免缓存永不失效）。

## 未启用 election 时

- `try_acquire_leader()` 恒返回 `is_leader=True`（单 worker 契约）。
- 文档声明：多机部署必须开 election 或保证单消费者。
