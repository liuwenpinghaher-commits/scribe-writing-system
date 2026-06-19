#!/usr/bin/env python
"""LoRA 训练 PoC(CPU 可跑)—— 证明整条 LoRA 训练流程真的能执行并产出 adapter。

用极小模型在 CPU 上做真实 LoRA 微调(真梯度下降),保存 adapter 并重新加载验证。
生产级文风个性化仍需 GPU + 强开源模型(见 tools/lora_finetune.py),但"LoRA 训练能否执行"
这件事由本脚本实证:能。
"""
import sys
from pathlib import Path

import torch
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODEL = "sshleifer/tiny-gpt2"   # 极小模型,CPU 秒级
OUT = str(Path(__file__).resolve().parent.parent / "out" / "lora-poc")


def _texts():
    # 优先用系统导出的作者训练样本;不足则用合成文风样本(证明流程)
    try:
        from scribe_mcp.db import Database
        from scribe_mcp.personalize import export_training_data
        db = Database(str(Path(__file__).resolve().parent.parent / "scribe.db"))
        data = export_training_data(db, "u1")
        ts = [d["output"] for d in data if len(d["output"]) > 10]
        if ts:
            return ts[:32]
    except Exception:
        pass
    return [
        "他把烟摁灭在窗台上,火星溅了一下。",
        "楼下传来铁门合拢的闷响,他没有回头。",
        "雨把街灯泡成一团团昏黄,他走得很慢。",
        "她没有解释,只把外套领子竖了起来。",
    ] * 4


def main():
    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(MODEL)
    lora = LoraConfig(task_type="CAUSAL_LM", r=8, lora_alpha=16, lora_dropout=0.0,
                      target_modules=["c_attn"])  # gpt2 注意力投影
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    texts = _texts()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=5e-3)
    model.train()
    losses = []
    for epoch in range(3):
        for t in texts:
            enc = tok(t, return_tensors="pt", truncation=True, max_length=64)
            out = model(**enc, labels=enc["input_ids"])
            out.loss.backward()
            opt.step(); opt.zero_grad()
            losses.append(float(out.loss))
    first, last = sum(losses[:4]) / 4, sum(losses[-4:]) / 4
    print(f"训练步数={len(losses)}  起始loss≈{first:.4f}  结束loss≈{last:.4f}  下降={'是' if last < first else '否'}")

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT)
    files = [p.name for p in Path(OUT).iterdir()]
    assert any("adapter_model" in f for f in files), "adapter 权重未生成"
    assert "adapter_config.json" in files, "adapter 配置未生成"
    print(f"✅ LoRA adapter 已保存 → {OUT}  文件:{files}")

    # 重新加载验证 adapter 可用
    base = AutoModelForCausalLM.from_pretrained(MODEL)
    merged = PeftModel.from_pretrained(base, OUT)
    print("✅ adapter 重新加载成功:", type(merged).__name__)
    assert last < first, "loss 未下降,训练未真正生效"
    print("✅ LoRA 训练流程端到端执行成功(CPU,PoC 规模)。")


if __name__ == "__main__":
    main()
