# Local GPU setup and public testing

Verified on 30 October 2026 on this laptop: Intel i5-12450H, 16 GB RAM,
NVIDIA RTX 2050 (4 GB VRAM). The original virtual environment has CPU-only
PyTorch. The tested CUDA build, torch 2.10.0+cu128, is installed separately
under `scratch/cuda-runtime`; the original environment was not replaced.

## Start for the demonstration

From the repository root in PowerShell:

```powershell
.\scripts\start-local.ps1
```

Wait for `Server startup pre-warming complete` and `Application startup complete`.
The logs should identify ClaimBuster, RoBERTa NLI and the political bias model
as ready on `cuda:0`. Then open http://127.0.0.1:8001.
This loads and warms all classifiers before accepting requests. The embedding
model stays on CPU. GPU inference shares a lock to limit overlapping memory
allocations. The existing models, claim limits and verdict rules are retained;
GPU classifiers use FP16 instead of the CPU runtime's BF16.

If GPU execution is unavailable, a deliberate CPU launch is available:

```powershell
.\scripts\start-local.ps1 -Cpu
```

CPU execution is slower. Keep the laptop plugged in and awake during testing.
The model weights are already cached; startup uses offline model loading.
Article fetching, evidence search and the news feed still require Internet.

## Public access

The running Cloudflare tunnel forwards to port 8001, so public visitors use
the same warmed GPU models. Keep both the app and tunnel running. The temporary
URL is not permanent and depends on the laptop staying online.

If the tunnel needs restarting, the existing executable can create a new URL:

```powershell
.\scratch\tools\cloudflared.exe tunnel --url http://127.0.0.1:8001 --no-autoupdate --protocol http2
```

Share the URL printed by that process. Google Forms remains separate.
No Render deployment was changed by this local setup.

## Observed public-link timings

These are real uncached analysis requests, not guaranteed latency targets:

| Check | Seconds |
| --- | ---: |
| Full AP tariff article audit, 3 claims with sources and explanations | 5.93 |
| AP/CBS tariff comparison, 3 claims per article | 9.74 |
| Fresh technology news feed | 11.33 |
| Two simultaneous audits of different short factual texts, total elapsed | 2.33 |

The same AP/CBS comparison previously took 69.2 seconds on the warmed CPU
runtime. Observed GPU memory consumption was 1605 MiB of 4096 MiB. Network
delays, inaccessible publishers, search limits and additional simultaneous
users can increase latency. Two simultaneous text audits are a small
concurrency check, not a large-load capacity test.

Raw results are saved locally in `scratch/gpu-public-benchmark.json`.
Seven lightweight regression checks passed with:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests
```

The CUDA package source is PyTorch's official wheel index:
https://download.pytorch.org/whl/cu128
