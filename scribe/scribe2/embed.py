# 复用 fastembed,本地 CPU,中文优先多语模型
_model = None
_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # 512 维,中文优化

def _m():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model

def embed(texts: list[str]) -> list[list[float]]:
    return [list(map(float, v)) for v in _m().embed(texts)]

def dim() -> int:
    return len(embed(["probe"])[0])
