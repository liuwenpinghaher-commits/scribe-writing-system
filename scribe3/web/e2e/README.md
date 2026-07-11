# Scribe3 Web E2E 分档

本目录里的 Playwright 脚本按副作用分成三档。默认 `npm test` 只运行 Vitest,不运行任何会写真实作品的 e2e。

## e2e:readonly

只允许打开、切换、查看、搜索、读取 network payload。不得创建、编辑、删除、导入提交或保存真实作品。

运行命令:

```bash
npm run e2e:readonly
```

当前脚本:

- `e2e/qa_batchE.mjs`

## e2e:writes-with-snapshot

允许写入 `book_c256380e` 第 4 章,但必须先拍快照,脚本结束后恢复,并复核章正文、草稿和测试数据零残留。

运行命令:

```bash
npm run e2e:writes-with-snapshot
```

当前顺序:

```bash
node e2e/snapshot_ch4.mjs b2
node e2e/qa_b2.mjs
node e2e/qa_b2_restore.mjs
```

如果中间脚本失败,也要单独运行恢复命令:

```bash
node e2e/qa_b2_restore.mjs
```

## e2e:destructive-manual

删除、导入提交、迁移、真实张力写入、会影响多对象引用的脚本只允许人工单独运行。运行前必须记录目标 work、快照文件、恢复命令和复核命令。

运行命令:

```bash
npm run e2e:destructive-manual
```

该命令默认拒绝执行,用于防止破坏性脚本被误放进自动回归。需要运行具体脚本时,直接写明脚本名、目标作品和恢复方案。
