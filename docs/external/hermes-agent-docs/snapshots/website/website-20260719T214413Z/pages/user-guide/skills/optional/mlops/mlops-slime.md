# Slime Rl Training
Provides guidance for LLM post-training with RL using slime, a Megatron+SGLang framework. Use when training GLM models, implementing custom data generation workflows, or needing tight Megatron-LM integration for RL scaling.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Optional — install with `hermes skills install official/mlops/slime`  |  
| Path  | `optional-skills/mlops/slime`  |  
| Version  | `1.0.0`  |  
| Author  | Orchestra Research  |  
| License  | MIT  |  
| Dependencies  |  `sglang-router>=0.2.3`, `ray`, `torch>=2.0.0`, `transformers>=4.40.0`  |  
| Platforms  | linux, macos  |  
| Tags  |  `Reinforcement Learning`, `Megatron-LM`, `SGLang`, `GRPO`, `Post-Training`, `GLM`  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# slime: LLM Post-Training Framework for RL Scaling
slime is an LLM post-training framework from Tsinghua's THUDM team, powering GLM-4.5, GLM-4.6, and GLM-4.7. It connects Megatron-LM for training with SGLang for high-throughput rollout generation.
## When to Use slime[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#when-to-use-slime "Direct link to When to Use slime")
**Choose slime when you need:**
  * Megatron-LM native training with SGLang inference
  * Custom data generation workflows with flexible data buffers
  * Training GLM, Qwen3, DeepSeek V3, or Llama 3 models
  * Research-grade framework with production backing (Z.ai)

**Consider alternatives when:**
  * You need enterprise-grade stability features → use **miles**
  * You want flexible backend swapping → use **verl**
  * You need PyTorch-native abstractions → use **torchforge**

## Key Features[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#key-features "Direct link to Key Features")
  * **Training** : Megatron-LM with full parallelism support (TP, PP, DP, SP)
  * **Rollout** : SGLang-based high-throughput generation with router
  * **Data Buffer** : Flexible prompt management and sample storage
  * **Models** : GLM-4.x, Qwen3, DeepSeek V3/R1, Llama 3

## Architecture Overview[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#architecture-overview "Direct link to Architecture Overview")

```
┌─────────────────────────────────────────────────────────┐  
│                    Data Buffer                          │  
│ - Prompt initialization and management                  │  
│ - Custom data generation and filtering                  │  
│ - Rollout sample storage                                │  
└─────────────┬───────────────────────────┬───────────────┘  
              │                           │  
┌─────────────▼───────────┐ ┌─────────────▼───────────────┐  
│ Training (Megatron-LM)  │ │ Rollout (SGLang + Router)   │  
│ - Actor model training  │ │ - Response generation       │  
│ - Critic (optional)     │ │ - Reward/verifier output    │  
│ - Weight sync to rollout│ │ - Multi-turn support        │  
└─────────────────────────┘ └─────────────────────────────┘  

```

## Installation[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#installation "Direct link to Installation")

```
# Recommended: Docker  
docker pull slimerl/slime:latest  
docker run --rm --gpus all --ipc=host --shm-size=16g \  
  -it slimerl/slime:latest /bin/bash  
  
# Inside container  
cd /root/slime && pip install -e . --no-deps  

```

### From Source[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#from-source "Direct link to From Source")

```
git clone https://github.com/THUDM/slime.git  
cd slime  
pip install -r requirements.txt  
pip install -e .  

```

## Quick Start: GRPO Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#quick-start-grpo-training "Direct link to Quick Start: GRPO Training")

```
# Source model configuration  
source scripts/models/qwen3-4B.sh  
  
# Launch training  
python train.py \  
    --actor-num-nodes 1 \  
    --actor-num-gpus-per-node 4 \  
    --rollout-num-gpus 4 \  
    --advantage-estimator grpo \  
    --use-kl-loss --kl-loss-coef 0.001 \  
    --rollout-batch-size 32 \  
    --n-samples-per-prompt 8 \  
    --global-batch-size 256 \  
    --num-rollout 3000 \  
    --prompt-data /path/to/data.jsonl \  
    ${MODEL_ARGS[@]} ${CKPT_ARGS[@]}  

```

* * *
## Workflow 1: Standard GRPO Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#workflow-1-standard-grpo-training "Direct link to Workflow 1: Standard GRPO Training")
Use this workflow for training reasoning models with group-relative advantages.
### Prerequisites Checklist[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#prerequisites-checklist "Direct link to Prerequisites Checklist")
  * Docker environment or Megatron-LM + SGLang installed
  * Model checkpoint (HuggingFace or Megatron format)
  * Training data in JSONL format

### Step 1: Prepare Data[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#step-1-prepare-data "Direct link to Step 1: Prepare Data")

```
# data.jsonl format  
{"prompt": "What is 2 + 2?", "label": "4"}  
{"prompt": "Solve: 3x = 12", "label": "x = 4"}  

```

Or with chat format:

```
{  
    "prompt": [  
        {"role": "system", "content": "You are a math tutor."},  
        {"role": "user", "content": "What is 15 + 27?"}  
    ],  
    "label": "42"  
}  

```

### Step 2: Configure Model[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#step-2-configure-model "Direct link to Step 2: Configure Model")
Choose a pre-configured model script:

```
# List available models  
ls scripts/models/  
# glm4-9B.sh, qwen3-4B.sh, qwen3-30B-A3B.sh, deepseek-v3.sh, llama3-8B.sh, ...  
  
# Source your model  
source scripts/models/qwen3-4B.sh  

```

### Step 3: Launch Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#step-3-launch-training "Direct link to Step 3: Launch Training")

```
python train.py \  
    --actor-num-nodes 1 \  
    --actor-num-gpus-per-node 8 \  
    --rollout-num-gpus 8 \  
    --advantage-estimator grpo \  
    --use-kl-loss \  
    --kl-loss-coef 0.001 \  
    --prompt-data /path/to/train.jsonl \  
    --input-key prompt \  
    --label-key label \  
    --apply-chat-template \  
    --rollout-batch-size 32 \  
    --n-samples-per-prompt 8 \  
    --global-batch-size 256 \  
    --num-rollout 3000 \  
    --save-interval 100 \  
    --eval-interval 50 \  
    ${MODEL_ARGS[@]}  

```

### Step 4: Monitor Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#step-4-monitor-training "Direct link to Step 4: Monitor Training")
  * Check TensorBoard: `tensorboard --logdir outputs/`
  * Verify reward curves are increasing
  * Monitor GPU utilization across nodes

* * *
## Workflow 2: Asynchronous Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#workflow-2-asynchronous-training "Direct link to Workflow 2: Asynchronous Training")
Use async mode for higher throughput by overlapping rollout and training.
### When to Use Async[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#when-to-use-async "Direct link to When to Use Async")
  * Large models with long generation times
  * High GPU idle time in synchronous mode
  * Sufficient memory for buffering

### Launch Async Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#launch-async-training "Direct link to Launch Async Training")

```
python train_async.py \  
    --actor-num-nodes 1 \  
    --actor-num-gpus-per-node 8 \  
    --rollout-num-gpus 8 \  
    --advantage-estimator grpo \  
    --async-buffer-size 4 \  
    --prompt-data /path/to/train.jsonl \  
    ${MODEL_ARGS[@]}  

```

### Async-Specific Parameters[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#async-specific-parameters "Direct link to Async-Specific Parameters")

```
--async-buffer-size 4        # Number of rollouts to buffer  
--update-weights-interval 2  # Sync weights every N rollouts  

```

* * *
## Workflow 3: Multi-Turn Agentic Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#workflow-3-multi-turn-agentic-training "Direct link to Workflow 3: Multi-Turn Agentic Training")
Use this workflow for training agents with tool use or multi-step reasoning.
### Prerequisites[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#prerequisites "Direct link to Prerequisites")
  * Custom generate function for multi-turn logic
  * Tool/environment interface

### Step 1: Define Custom Generate Function[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#step-1-define-custom-generate-function "Direct link to Step 1: Define Custom Generate Function")

```
# custom_generate.py  
async def custom_generate(args, samples, evaluation=False):  
    """Multi-turn generation with tool calling."""  
    for sample in samples:  
        conversation = sample.prompt  
  
        for turn in range(args.max_turns):  
            # Generate response  
            response = await generate_single(conversation)  
  
            # Check for tool call  
            tool_call = extract_tool_call(response)  
            if tool_call:  
                tool_result = execute_tool(tool_call)  
                conversation.append({"role": "assistant", "content": response})  
                conversation.append({"role": "tool", "content": tool_result})  
            else:  
                break  
  
        sample.response = response  
        sample.reward = compute_reward(sample)  
  
    return samples  

```

### Step 2: Launch with Custom Function[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#step-2-launch-with-custom-function "Direct link to Step 2: Launch with Custom Function")

```
python train.py \  
    --custom-generate-function-path custom_generate.py \  
    --max-turns 5 \  
    --prompt-data /path/to/agent_data.jsonl \  
    ${MODEL_ARGS[@]}  

```

See `examples/search-r1/` for a complete multi-turn search example.
* * *
## Configuration Reference[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#configuration-reference "Direct link to Configuration Reference")
### Three Argument Categories[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#three-argument-categories "Direct link to Three Argument Categories")
slime uses three types of arguments:
**1. Megatron Arguments** (passed directly):

```
--tensor-model-parallel-size 2  
--pipeline-model-parallel-size 1  
--num-layers 32  
--hidden-size 4096  

```

**2. SGLang Arguments** (prefixed with `--sglang-`):

```
--sglang-mem-fraction-static 0.8  
--sglang-context-length 8192  
--sglang-log-level INFO  

```

**3. slime Arguments** :

```
# Resource allocation  
--actor-num-nodes 1  
--actor-num-gpus-per-node 8  
--rollout-num-gpus 8  
--colocate  # Share GPUs between training/inference  
  
# Data  
--prompt-data /path/to/data.jsonl  
--input-key prompt  
--label-key label  
  
# Training loop  
--num-rollout 3000  
--rollout-batch-size 32  
--n-samples-per-prompt 8  
--global-batch-size 256  
  
# Algorithm  
--advantage-estimator grpo  # or: gspo, ppo, reinforce_plus_plus  
--use-kl-loss  
--kl-loss-coef 0.001  

```

### Key Constraints[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#key-constraints "Direct link to Key Constraints")

```
rollout_batch_size × n_samples_per_prompt = global_batch_size × num_steps_per_rollout  

```

Example: 32 × 8 = 256 × 1
* * *
## Data Buffer System[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#data-buffer-system "Direct link to Data Buffer System")
slime's data buffer enables flexible data management:
### Basic Data Source[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#basic-data-source "Direct link to Basic Data Source")

```
class RolloutDataSource:  
    def get_samples(self, num_samples):  
        """Fetch prompts from dataset."""  
        return self.dataset.sample(num_samples)  
  
    def add_samples(self, samples):  
        """Called after generation (no-op by default)."""  
        pass  

```

### Buffered Data Source (Off-Policy)[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#buffered-data-source-off-policy "Direct link to Buffered Data Source \(Off-Policy\)")

```
class RolloutDataSourceWithBuffer(RolloutDataSource):  
    def __init__(self):  
        self.buffer = []  
  
    def add_samples(self, samples):  
        """Store generated samples for reuse."""  
        self.buffer.extend(samples)  
  
    def buffer_filter(self, args, buffer, num_samples):  
        """Custom selection logic (prioritized, stratified, etc.)."""  
        return select_best(buffer, num_samples)  

```

* * *
## Common Issues and Solutions[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#common-issues-and-solutions "Direct link to Common Issues and Solutions")
### Issue: SGLang Engine Crash[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#issue-sglang-engine-crash "Direct link to Issue: SGLang Engine Crash")
**Symptoms** : Inference engine dies mid-training
**Solutions** :

```
# Enable fault tolerance  
--use-fault-tolerance  
  
# Increase memory allocation  
--sglang-mem-fraction-static 0.85  
  
# Reduce batch size  
--rollout-batch-size 16  

```

### Issue: Weight Sync Timeout[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#issue-weight-sync-timeout "Direct link to Issue: Weight Sync Timeout")
**Symptoms** : Training hangs after rollout
**Solutions** :

```
# Increase sync interval  
--update-weights-interval 5  
  
# Use colocated mode (no network transfer)  
--colocate  

```

### Issue: OOM During Training[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#issue-oom-during-training "Direct link to Issue: OOM During Training")
**Symptoms** : CUDA OOM in backward pass
**Solutions** :

```
# Enable gradient checkpointing  
--recompute-activations  
  
# Reduce micro-batch size  
--micro-batch-size 1  
  
# Enable sequence parallelism  
--sequence-parallel  

```

### Issue: Slow Data Loading[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#issue-slow-data-loading "Direct link to Issue: Slow Data Loading")
**Symptoms** : GPU idle during data fetch
**Solutions** :

```
# Increase data workers  
--num-data-workers 4  
  
# Use streaming dataset  
--streaming-data  

```

* * *
## Supported Models[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#supported-models "Direct link to Supported Models")  
| Model Family  | Configurations  |  
| --- | --- |  
| GLM  | GLM-4.5, GLM-4.6, GLM-4.7, GLM-Z1-9B  |  
| Qwen  | Qwen3 (4B, 8B, 30B-A3B), Qwen3-MoE, Qwen2.5  |  
| DeepSeek  | V3, V3.1, R1  |  
| Llama  | Llama 3 (8B, 70B)  |  
| Others  | Kimi K2, Moonlight-16B  |  
Each model has pre-configured scripts in `scripts/models/`.
* * *
## Advanced Topics[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#advanced-topics "Direct link to Advanced Topics")
### Co-location Mode[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#co-location-mode "Direct link to Co-location Mode")
Share GPUs between training and inference to reduce memory:

```
python train.py \  
    --colocate \  
    --actor-num-gpus-per-node 8 \  
    --sglang-mem-fraction-static 0.4 \  
    ${MODEL_ARGS[@]}  

```

### Custom Reward Model[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#custom-reward-model "Direct link to Custom Reward Model")

```
# custom_rm.py  
class CustomRewardModel:  
    def __init__(self, model_path):  
        self.model = load_model(model_path)  
  
    def compute_reward(self, prompts, responses):  
        inputs = self.tokenize(prompts, responses)  
        scores = self.model(inputs)  
        return scores.tolist()  

```

```
--custom-rm-path custom_rm.py  

```

### Evaluation Multi-Task[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#evaluation-multi-task "Direct link to Evaluation Multi-Task")

```
--eval-prompt-data aime /path/to/aime.jsonl \  
--eval-prompt-data gsm8k /path/to/gsm8k.jsonl \  
--n-samples-per-eval-prompt 16  

```

* * *
## Resources[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-slime#resources "Direct link to Resources")
  * **Documentation** : <https://thudm.github.io/slime/>
  * **GitHub** : <https://github.com/THUDM/slime>
  * **Blog** : <https://lmsys.org/blog/2025-07-09-slime/>
  * **Examples** : See `examples/` directory for 14+ worked examples
