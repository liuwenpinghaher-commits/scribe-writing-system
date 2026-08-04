#!/usr/bin/env bash
# 在服务器上预下载 BGE 中文 embedding 模型到数据目录（容器只读缓存、无需公网）。
# 用法：
#   bash deploy/prod/scripts/prefetch_embed_model.sh
# 依赖：已有 prod-backend 镜像（或 python 环境装了 fastembed）。
set -euo pipefail

DATA_DIR="${SCRIBE3_DATA_DIR:-/opt/scribe3/data}"
HF_DIR="${DATA_DIR}/models/hf"
FE_DIR="${DATA_DIR}/models/fastembed"
IMAGE="${SCRIBE3_BACKEND_IMAGE:-prod-backend:latest}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-0}"

mkdir -p "$HF_DIR" "$FE_DIR"

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "==> docker $IMAGE 预拉 BAAI/bge-small-zh-v1.5 → $DATA_DIR/models"
  docker run --rm \
    -e HF_ENDPOINT \
    -e HF_HOME=/models/hf \
    -e FASTEMBED_CACHE_PATH=/models/fastembed \
    -e HF_HUB_DISABLE_XET \
    -e HF_HUB_ENABLE_HF_TRANSFER \
    -v "${HF_DIR}:/models/hf" \
    -v "${FE_DIR}:/models/fastembed" \
    "$IMAGE" \
    python -c 'from fastembed import TextEmbedding
m=TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
v=list(m.embed(["ok"]))[0]
print("dim", len(v), "ok")'
else
  echo "==> 无镜像 $IMAGE，使用本机 python" >&2
  export HF_HOME="$HF_DIR" FASTEMBED_CACHE_PATH="$FE_DIR"
  python3 -c 'from fastembed import TextEmbedding
m=TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
v=list(m.embed(["ok"]))[0]
print("dim", len(v), "ok")'
fi

du -sh "$HF_DIR" "$FE_DIR" || true
echo "prefetch done"
