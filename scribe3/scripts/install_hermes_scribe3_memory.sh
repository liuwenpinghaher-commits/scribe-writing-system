#!/usr/bin/env bash
# 统一上下文与记忆系统 · Task 12:安装可选 scribe3-memory Hermes provider 插件。
#
# 做什么(且仅做什么):把 repo-owned 插件同步到 scribe3 profile 的 plugins 目录,然后
# 只运行 `hermes -p scribe3 plugins list` 列出确认。**默认不自动启用**——启用是独立显式命令
# (见下方提示 / README.md)。repo 是唯一真相源:每次同步都以 repo 覆盖目标目录。
#
# 用法:
#   bash scribe3/scripts/install_hermes_scribe3_memory.sh
#
# 环境:
#   HERMES_HOME 覆盖 ~/.hermes(升级演练/隔离用);HERMES_PROFILE 覆盖 scribe3。
set -u

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hermes_plugins/scribe3-memory"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PROFILE="${HERMES_PROFILE:-scribe3}"
DEST_DIR="$HERMES_HOME/profiles/$PROFILE/plugins/scribe3-memory"

echo "== scribe3-memory Hermes provider 安装 =="
echo "  源:      $SRC_DIR"
echo "  目标:    $DEST_DIR"

if [ ! -d "$SRC_DIR" ]; then
  echo "  ❌ 源插件目录不存在,终止。" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST_DIR")"
# 以 repo 为准覆盖同步(先清目标再复制,避免残留旧文件);排除 __pycache__。
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude='__pycache__' "$SRC_DIR/" "$DEST_DIR/"
else
  cp -R "$SRC_DIR/." "$DEST_DIR/"
  rm -rf "$DEST_DIR/__pycache__"
fi
echo "  ✅ 已同步插件到 profile。"

# 只列出确认,不启用(启用是独立显式动作)。
if command -v hermes >/dev/null 2>&1; then
  echo "== hermes -p $PROFILE plugins list =="
  hermes -p "$PROFILE" plugins list || echo "  ·  plugins list 失败(best-effort,可忽略)"
else
  echo "  ·  未找到 hermes CLI,跳过 plugins list。"
fi

cat <<EOF

下一步(默认未启用,需显式两步 + 设后端地址):
  export SCRIBE3_API_BASE=http://127.0.0.1:3320       # 指向 Scribe 后端(默认后端 3320)
  hermes -p $PROFILE plugins enable scribe3-memory
  hermes -p $PROFILE config set memory.provider scribe3-memory

未设 SCRIBE3_API_BASE 时 provider.is_available() 为 False,不介入任何会话。
EOF
