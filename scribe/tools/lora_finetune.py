#!/usr/bin/env python
"""LoRA 微调(作者文风个性化)· 内核2 第三档。

【状态】就绪、未在本环境执行 —— 需要 GPU + 开源模型权重(如 Hermes-4 / Qwen / Llama)。
火山 doubao 是闭源 API,无法做权重微调;故本脚本在有 GPU 的机器上运行。
依赖(GPU 机器): pip install "transformers>=4.44" peft trl accelerate datasets bitsandbytes

用法(GPU 机器):
  1) python tools/export_training_data.py <owner_id> data/<owner>-sft.jsonl   # 本机即可
  2) python tools/lora_finetune.py data/<owner>-sft.jsonl <base_model> out/lora-<owner>
  3) 用 vLLM/llama.cpp 加载 base+LoRA 起 OpenAI 兼容服务,把 Hermes custom provider 的
     base_url 指到它(见 工程3),即获得"懂你文风"的本地模型。
"""
import sys


def main(jsonl_path: str, base_model: str, out_dir: str):
    # 延迟导入:仅 GPU 机器需要这些重依赖
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    assert torch.cuda.is_available(), "需要 GPU;本脚本不在 CPU/闭源 API 环境运行。"

    tok = AutoTokenizer.from_pretrained(base_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    def fmt(ex):
        # 指令微调模板:instruction + input → output(作者认可正文/文风范本)
        prompt = f"{ex['instruction']}\n\n{ex['input']}\n\n正文:\n"
        return {"text": prompt + ex["output"] + tok.eos_token}

    ds = load_dataset("json", data_files=jsonl_path, split="train").map(fmt)

    model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.bfloat16,
                                                 device_map="auto")
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                      task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
    cfg = SFTConfig(output_dir=out_dir, num_train_epochs=3, per_device_train_batch_size=1,
                    gradient_accumulation_steps=8, learning_rate=2e-4, bf16=True,
                    logging_steps=10, save_strategy="epoch", max_seq_length=2048,
                    warmup_ratio=0.03)
    trainer = SFTTrainer(model=model, train_dataset=ds, peft_config=lora,
                         processing_class=tok, args=cfg)
    trainer.train()
    trainer.save_model(out_dir)
    print(f"LoRA adapter 已保存 → {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
