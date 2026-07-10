---
title: "Modal Serverless Gpu"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal

# Modal Serverless Gpu
Serverless GPU cloud platform for running ML workloads. Use when you need on-demand GPU access without infrastructure management, deploying ML models as APIs, or running batch jobs with automatic scaling.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Optional — install with `hermes skills install official/mlops/modal`  |  
| Path  | `optional-skills/mlops/modal`  |  
| Version  | `1.0.0`  |  
| Author  | Orchestra Research  |  
| License  | MIT  |  
| Dependencies  | `modal>=0.64.0`  |  
| Platforms  | linux, macos, windows  |  
| Tags  |  `Infrastructure`, `Serverless`, `GPU`, `Cloud`, `Deployment`, `Modal`  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# Modal Serverless GPU
Comprehensive guide to running ML workloads on Modal's serverless GPU cloud platform.
## When to use Modal[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#when-to-use-modal "Direct link to When to use Modal")
**Use Modal when:**
  * Running GPU-intensive ML workloads without managing infrastructure
  * Deploying ML models as auto-scaling APIs
  * Running batch processing jobs (training, inference, data processing)
  * Need pay-per-second GPU pricing without idle costs
  * Prototyping ML applications quickly
  * Running scheduled jobs (cron-like workloads)


**Key features:**
  * **Serverless GPUs** : T4, L4, A10G, L40S, A100, H100, H200, B200 on-demand
  * **Python-native** : Define infrastructure in Python code, no YAML
  * **Auto-scaling** : Scale to zero, scale to 100+ GPUs instantly
  * **Sub-second cold starts** : Rust-based infrastructure for fast container launches
  * **Container caching** : Image layers cached for rapid iteration
  * **Web endpoints** : Deploy functions as REST APIs with zero-downtime updates


**Use alternatives instead:**
  * **RunPod** : For longer-running pods with persistent state
  * **Lambda Labs** : For reserved GPU instances
  * **SkyPilot** : For multi-cloud orchestration and cost optimization
  * **Kubernetes** : For complex multi-service architectures


## Quick start[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#quick-start "Direct link to Quick start")
### Installation[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#installation "Direct link to Installation")

```
pip install modal  
modal setup  # Opens browser for authentication  

```

### Hello World with GPU[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#hello-world-with-gpu "Direct link to Hello World with GPU")

```
import modal  
  
app = modal.App("hello-gpu")  
  
@app.function(gpu="T4")  
def gpu_info():  
    import subprocess  
    return subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout  
  
@app.local_entrypoint()  
def main():  
    print(gpu_info.remote())  

```

Run: `modal run hello_gpu.py`
### Basic inference endpoint[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#basic-inference-endpoint "Direct link to Basic inference endpoint")

```
import modal  
  
app = modal.App("text-generation")  
image = modal.Image.debian_slim().pip_install("transformers", "torch", "accelerate")  
  
@app.cls(gpu="A10G", image=image)  
class TextGenerator:  
    @modal.enter()  
    def load_model(self):  
        from transformers import pipeline  
        self.pipe = pipeline("text-generation", model="gpt2", device=0)  
  
    @modal.method()  
    def generate(self, prompt: str) -> str:  
        return self.pipe(prompt, max_length=100)[0]["generated_text"]  
  
@app.local_entrypoint()  
def main():  
    print(TextGenerator().generate.remote("Hello, world"))  

```

## Core concepts[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#core-concepts "Direct link to Core concepts")
### Key components[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#key-components "Direct link to Key components")  
| Component  | Purpose  |  
| --- | --- |  
| `App`  | Container for functions and resources  |  
| `Function`  | Serverless function with compute specs  |  
| `Cls`  | Class-based functions with lifecycle hooks  |  
| `Image`  | Container image definition  |  
| `Volume`  | Persistent storage for models/data  |  
| `Secret`  | Secure credential storage  |  
### Execution modes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#execution-modes "Direct link to Execution modes")  
| Command  | Description  |  
| --- | --- |  
| `modal run script.py`  | Execute and exit  |  
| `modal serve script.py`  | Development with live reload  |  
| `modal deploy script.py`  | Persistent cloud deployment  |  
## GPU configuration[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#gpu-configuration "Direct link to GPU configuration")
### Available GPUs[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#available-gpus "Direct link to Available GPUs")  
| GPU  | VRAM  | Best For  |  
| --- | --- | --- |  
| `T4`  | 16GB  | Budget inference, small models  |  
| `L4`  | 24GB  | Inference, Ada Lovelace arch  |  
| `A10G`  | 24GB  | Training/inference, 3.3x faster than T4  |  
| `L40S`  | 48GB  | Recommended for inference (best cost/perf)  |  
| `A100-40GB`  | 40GB  | Large model training  |  
| `A100-80GB`  | 80GB  | Very large models  |  
| `H100`  | 80GB  | Fastest, FP8 + Transformer Engine  |  
| `H200`  | 141GB  | Auto-upgrade from H100, 4.8TB/s bandwidth  |  
| `B200`  | Latest  | Blackwell architecture  |  
### GPU specification patterns[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#gpu-specification-patterns "Direct link to GPU specification patterns")

```
# Single GPU  
@app.function(gpu="A100")  
  
# Specific memory variant  
@app.function(gpu="A100-80GB")  
  
# Multiple GPUs (up to 8)  
@app.function(gpu="H100:4")  
  
# GPU with fallbacks  
@app.function(gpu=["H100", "A100", "L40S"])  
  
# Any available GPU  
@app.function(gpu="any")  

```

## Container images[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#container-images "Direct link to Container images")

```
# Basic image with pip  
image = modal.Image.debian_slim(python_version="3.11").pip_install(  
    "torch==2.1.0", "transformers==4.36.0", "accelerate"  
)  
  
# From CUDA base  
image = modal.Image.from_registry(  
    "nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04",  
    add_python="3.11"  
).pip_install("torch", "transformers")  
  
# With system packages  
image = modal.Image.debian_slim().apt_install("git", "ffmpeg").pip_install("whisper")  

```

## Persistent storage[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#persistent-storage "Direct link to Persistent storage")

```
volume = modal.Volume.from_name("model-cache", create_if_missing=True)  
  
@app.function(gpu="A10G", volumes={"/models": volume})  
def load_model():  
    import os  
    model_path = "/models/llama-7b"  
    if not os.path.exists(model_path):  
        model = download_model()  
        model.save_pretrained(model_path)  
        volume.commit()  # Persist changes  
    return load_from_path(model_path)  

```

## Web endpoints[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#web-endpoints "Direct link to Web endpoints")
### FastAPI endpoint decorator[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#fastapi-endpoint-decorator "Direct link to FastAPI endpoint decorator")

```
@app.function()  
@modal.fastapi_endpoint(method="POST")  
def predict(text: str) -> dict:  
    return {"result": model.predict(text)}  

```

### Full ASGI app[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#full-asgi-app "Direct link to Full ASGI app")

```
from fastapi import FastAPI  
web_app = FastAPI()  
  
@web_app.post("/predict")  
async def predict(text: str):  
    return {"result": await model.predict.remote.aio(text)}  
  
@app.function()  
@modal.asgi_app()  
def fastapi_app():  
    return web_app  

```

### Web endpoint types[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#web-endpoint-types "Direct link to Web endpoint types")  
| Decorator  | Use Case  |  
| --- | --- |  
| `@modal.fastapi_endpoint()`  | Simple function → API  |  
| `@modal.asgi_app()`  | Full FastAPI/Starlette apps  |  
| `@modal.wsgi_app()`  | Django/Flask apps  |  
| `@modal.web_server(port)`  | Arbitrary HTTP servers  |  
## Dynamic batching[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#dynamic-batching "Direct link to Dynamic batching")

```
@app.function()  
@modal.batched(max_batch_size=32, wait_ms=100)  
async def batch_predict(inputs: list[str]) -> list[dict]:  
    # Inputs automatically batched  
    return model.batch_predict(inputs)  

```

## Secrets management[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#secrets-management "Direct link to Secrets management")

```
# Create secret  
modal secret create huggingface HF_TOKEN=hf_xxx  

```


```
@app.function(secrets=[modal.Secret.from_name("huggingface")])  
def download_model():  
    import os  
    token = os.environ["HF_TOKEN"]  

```

## Scheduling[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#scheduling "Direct link to Scheduling")

```
@app.function(schedule=modal.Cron("0 0 * * *"))  # Daily midnight  
def daily_job():  
    pass  
  
@app.function(schedule=modal.Period(hours=1))  
def hourly_job():  
    pass  

```

## Performance optimization[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#performance-optimization "Direct link to Performance optimization")
### Cold start mitigation[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#cold-start-mitigation "Direct link to Cold start mitigation")

```
@app.function(  
    container_idle_timeout=300,  # Keep warm 5 min  
    allow_concurrent_inputs=10,  # Handle concurrent requests  
)  
def inference():  
    pass  

```

### Model loading best practices[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#model-loading-best-practices "Direct link to Model loading best practices")

```
@app.cls(gpu="A100")  
class Model:  
    @modal.enter()  # Run once at container start  
    def load(self):  
        self.model = load_model()  # Load during warm-up  
  
    @modal.method()  
    def predict(self, x):  
        return self.model(x)  

```

## Parallel processing[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#parallel-processing "Direct link to Parallel processing")

```
@app.function()  
def process_item(item):  
    return expensive_computation(item)  
  
@app.function()  
def run_parallel():  
    items = list(range(1000))  
    # Fan out to parallel containers  
    results = list(process_item.map(items))  
    return results  

```

## Common configuration[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#common-configuration "Direct link to Common configuration")

```
@app.function(  
    gpu="A100",  
    memory=32768,              # 32GB RAM  
    cpu=4,                     # 4 CPU cores  
    timeout=3600,              # 1 hour max  
    container_idle_timeout=120,# Keep warm 2 min  
    retries=3,                 # Retry on failure  
    concurrency_limit=10,      # Max concurrent containers  
)  
def my_function():  
    pass  

```

## Debugging[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#debugging "Direct link to Debugging")

```
# Test locally  
if __name__ == "__main__":  
    result = my_function.local()  
  
# View logs  
# modal app logs my-app  

```

## Common issues[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#common-issues "Direct link to Common issues")  
| Issue  | Solution  |  
| --- | --- |  
| Cold start latency  | Increase `container_idle_timeout`, use `@modal.enter()`  |  
| GPU OOM  | Use larger GPU (`A100-80GB`), enable gradient checkpointing  |  
| Image build fails  | Pin dependency versions, check CUDA compatibility  |  
| Timeout errors  | Increase `timeout`, add checkpointing  |  
## References[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#references "Direct link to References")
  * **[Advanced Usage](https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/mlops/modal/references/advanced-usage.md)** - Multi-GPU, distributed training, cost optimization
  * **[Troubleshooting](https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/mlops/modal/references/troubleshooting.md)** - Common issues and solutions


## Resources[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-modal#resources "Direct link to Resources")
  * **Documentation** : <https://modal.com/docs>
  * **Examples** : <https://github.com/modal-labs/modal-examples>
  * **Pricing** : <https://modal.com/pricing>
  * **Discord** : <https://discord.gg/modal>
