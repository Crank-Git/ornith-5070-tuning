# Ornith-1.5-35B on an RTX 5070 (12 GB): quant quality and offload speed

Measurements of [Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B) GGUF quants running in llama.cpp on a 12 GB consumer card with the MoE experts partly in system RAM. They answer two questions:

1. **Does running a 35B MoE "offloaded" make it worse?** Moving experts to the CPU doesn't change the math. The quant does, so we measured how far each quant's output drifts from a Q8_0 reference (KL divergence).
2. **Do llama.cpp's newer offload levers help?** We tested `--moe-cache-mib` (a GPU cache for CPU-resident experts) and MTP speculative decoding against interleaved controls.

## Hardware and software

| | |
|---|---|
| GPU | RTX 5070 12 GB (Windows, WDDM; desktop apps hold about 1.1 GB) |
| CPU / RAM | Ryzen 7 9700X, 2×16 GB DDR5-6000 CL36 |
| Engine | llama.cpp b11856 (`3642238cc`), official Windows CUDA build |
| Serving config ("control") | `-c 131072 -ngl 99 --n-cpu-moe 30 --flash-attn on -ctk q8_0 -ctv q8_0 -np 1 -b 2048 -ub 2048 --spec-type draft-mtp --spec-draft-n-max 1` |

## Results: quant quality (KLD against Q8_0)

| Quant | Size | Code: mean KLD | Code: same top token | Prose: mean KLD | Prose: same top token |
|---|---:|---:|---:|---:|---:|
| official Q4_K_M (ornith-ai) | 21.7 GB | 0.0865 | 92.86% | 0.0729 | 89.63% |
| same, q8_0 KV cache | 21.7 GB | 0.0882 | 92.73% | 0.0714 | 89.52% |
| **bartowski Q4_K_L** | 22.2 GB | **0.0665** (−23%) | 93.60% | **0.0511** (−30%) | 91.46% |
| official Q5_K_M (ornith-ai) | 25.3 GB | 0.0443 (−49%) | 95.03% | 0.0467 (−36%) | 91.55% |

Full table (median, 99% and 99.9% KLD, RMS Δp, perplexity): [`results/kld/TABLE.md`](results/kld/TABLE.md). Raw logs are in `results/kld/`.

What it shows:

- **The standard Q4_K_M is the weak point.** Its tail is heavy: the 99th-percentile KLD on code is 1.19, so roughly 1 token in 100 has a substantially different distribution from Q8_0.
- **Q4_K_L gets a quarter to a third of the way to Q5 quality for 0.5 GB.** It keeps the always-active tensors at Q8_0/Q6_K (embedding, output, attention/SSM projections, shared experts) where the official Q4_K_M uses Q4_K. Those tensors sit on the GPU and every token reads them. Its routed experts are the same Q4_K, so its decode cost is nearly unchanged (see below).
- **q8_0 KV cache is free at this length.** It sits within ±2% of f16 KV, which is inside the error bars at a 4K context. This model has KV in only 10 of 40 layers. Longer contexts weren't tested.
- **The Ollama `ornith-1.5:35b` blob is byte-equivalent in quality** to ornith-ai's official Q4_K_M: identical KLD to every printed digit.

### Method

- `llama-perplexity --kl-divergence-base` with bartowski's Q8_0 as the reference, f16 KV, `-c 4096`, 12 chunks per corpus. That is about 24.5K scored tokens per corpus, from the second half of each chunk.
- **Corpora** (see [`corpus/SOURCES.md`](corpus/SOURCES.md)):
  - prose: WikiText-2 test;
  - code: interleaved Go 1.23 and CPython 3.13 stdlib source.
- **Script:** [`scripts/kld-sweep.ps1`](scripts/kld-sweep.ps1), with candidates in [`scripts/candidates.txt`](scripts/candidates.txt).
- **Caveats:**
  - **The reference is Q8_0, not BF16.** BF16 is 71 GB and doesn't fit this machine. Q8_0 typically sits within about 0.002–0.005 KLD of BF16.
  - **The reference and the Q4_K_L are both bartowski conversions.** If his conversion differs at all from ornith-ai's, that gives the Q4_K_L a small advantage.
  - **The ± values in the full table are per-token standard errors.** Tokens are correlated, so treat them as a lower bound on the real uncertainty.

## Results: speed (server-side timings, greedy)

Each candidate ran between two controls. Each run took the median of 6 greedy 512-token generations per prompt (code, prose), plus 3 cold prefills of about 16K tokens of code. The 6 control runs held within ±2% on decode and ±3% on prefill.

| Config | Code tok/s | Prose tok/s | Prefill tok/s | VRAM used | Greedy output = control? |
|---|---:|---:|---:|---:|---|
| **control** (median of 6) | **70.3** | **62.8** | **1834** | 11.4 GB | n/a |
| `--n-cpu-moe 34 --moe-cache-mib 1900` | 56.2 (−20%) | 55.6 (−11%) | 1655 (−10%) | 11.5 GB | no |
| `--n-cpu-moe 38 --moe-cache-mib 3800` | 65.1 (−7%) | 71.3 (+13%) | 1563 (−15%) | 11.5 GB | no |
| `--n-cpu-moe 41 --moe-cache-mib 5000` | 64.4 (−8%) | 74.7 (+19%) | 1489 (−19%) | 11.1 GB | no |
| MTP off | 63.4 (−10%) | 63.0 (0%) | 1935 (+6%) | 9.9 GB | **yes** |
| bartowski Q4_K_L (`--n-cpu-moe 31`) | 68.2 (−3%) | 59.2 (−6%) | 1812 (−1%) | 11.2 GB | no (different weights) |

What it shows:

- **`--moe-cache-mib` doesn't pay off for coding on this box.**
  - Every size cut prefill (−10% to −19%) and code decode (−7% to −20%).
  - Large caches did speed up prose decode (+13% to +19%), presumably because prose routes to a narrower set of experts.
  - Hand-tuned `--n-cpu-moe` with no cache remains the best for agent workloads, which are prefill-heavy and code-heavy.
  - It also changes greedy output slightly. The cached experts compute on the GPU instead of the CPU, so the floating-point results differ.
- **MTP (1 draft) is +10% on code and neutral on prose, and it is lossless.** Greedy output was byte-identical with it on and off. It costs about 1.5 GB of VRAM and about 5% of prefill.
- **Q4_K_L costs about 3–6% decode and nothing on prefill**, for 23–30% lower KLD. That is the best quality-per-speed trade measured here.

Raw per-request data is in [`results/speed-ab.jsonl`](results/speed-ab.jsonl) and the driver output in [`results/speed-ab.out`](results/speed-ab.out). The scripts are [`scripts/ab.sh`](scripts/ab.sh) and [`scripts/bench.py`](scripts/bench.py).

## Qwen3.6-35B-A3B on the same box

Ornith-1.5 is a fine-tune of Qwen3.6-35B-A3B. We measured the base model with the same method.

### Quant quality (each against bartowski's Qwen3.6 Q8_0)

| Quant | Code: mean KLD | Code: same top | Prose: mean KLD | Prose: same top |
|---|---:|---:|---:|---:|
| **Unsloth UD-Q4_K_M** (MTP build) | **0.0504** | 95.42% | **0.0116** | 95.68% |
| Unsloth UD-Q4_K_XL (MTP build) | 0.0501 | 95.41% | 0.0110 | 96.00% |
| bartowski Q4_K_L | 0.0720 (+43%) | 94.60% | 0.0176 (+52%) | 94.99% |

Full table: [`results/kld-qwen36/TABLE.md`](results/kld-qwen36/TABLE.md).

- **Unsloth's dynamic quants win for Qwen3.6**, and UD-Q4_K_XL buys nothing over UD-Q4_K_M. The recipe that helped Ornith (bartowski Q4_K_L) is the worst of the three here.
- These numbers measure how faithful each quant is to its own model's Q8_0. They don't say which model is better, and KLD values don't compare across the two models.

### Speed (interleaved with Ornith Q4_K_L as the control)

| Config | Code tok/s | Prose tok/s | Prefill tok/s | VRAM used | MTP acceptance (code) |
|---|---:|---:|---:|---:|---:|
| **Ornith Q4_K_L** (`--n-cpu-moe 31`, median of 4) | 67.7 | 58.9 | 1724 | 11.1 GB | 79% |
| Qwen3.6 UD-Q4_K_M, `--n-cpu-moe 30` | 72.7 | 67.4 | **1033** | 11.7 GB | 92% |
| Qwen3.6 UD-Q4_K_M, `--n-cpu-moe 31` | 71.5 (+6%) | 65.7 (+11%) | 1740 (+1%) | 11.3 GB | 92% |
| Qwen3.6 UD-Q4_K_XL, `--n-cpu-moe 31` | 71.2 (+5%) | 64.5 (+10%) | 1758 (+2%) | 11.5 GB | 92% |
| Qwen3.6 bartowski Q4_K_L, `--n-cpu-moe 31` | 73.2 (+8%) | 68.3 (+16%) | 1730 (0%) | 11.5 GB | 92% |

- **Qwen3.6 decodes 5–16% faster** on the same hardware, mostly because its MTP head's drafts are accepted more often (92% against 79%). Ornith's MTP head works, but it was evidently not retrained as well as the rest of the fine-tune.
- **Watch VRAM headroom on Windows.** At `--n-cpu-moe 30` the UD-Q4_K_M sat at 11.7 of 12.2 GB, and prefill dropped 40%. Moving one more expert layer to RAM restored it at almost no cost to decode. Under WDDM, a nearly full card loses prefill speed without any error.

Raw data: [`results/speed-qwen36.jsonl`](results/speed-qwen36.jsonl) and [`results/speed-qwen36.out`](results/speed-qwen36.out).

## Agent tasks: harness and model

These runs used six multi-file Go feature tasks (a small private benchmark, not published here), each graded by its test suite. Each agent ran against llama-server through a logging proxy, with the server's default sampling of temperature 0.6, top-p 0.95, top-k 20.

### Which harness (Ornith official Q4_K_M, 2 reps per task)

| Harness | Pass | Median time per task | Median generated tokens | Runs that edited the tests |
|---|---:|---:|---:|---:|
| **Claude Code `--bare`** | **11/12** | **211 s** | 13.5K | 0 |
| Claude Code (full prompt) | 10/12 | 285 s | 17.1K | 1 |
| little-coder | 11/12 | 529 s | 32.4K | 4 |
| [pi](https://github.com/badlogic/pi-mono) | 6/12 | 78 s | 4.6K | 0 |

Claude Code reaches llama-server's Anthropic-compatible `/v1/messages` with `ANTHROPIC_BASE_URL` and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072`. `--bare` cuts the system prompt to about 1K tokens and the tool set to Bash, Read and Edit, which suits a 35B model at this speed. Full table: [`results/harness/harness4-hard.md`](results/harness/harness4-hard.md).

### Ornith-1.5 against Qwen3.6 (Claude Code `--bare`, 3 reps per task)

| Model | Pass | Median time per task | Median generated tokens | Total time (18 runs) |
|---|---:|---:|---:|---:|
| Ornith-1.5 bartowski Q4_K_L | 16/18 | 218 s | 12.5K | 73 min |
| Qwen3.6 Unsloth UD-Q4_K_M, `preserve_thinking` on | 15/18 | **73 s** | **4.0K** | **30 min** |

- **The pass rates are a statistical tie.** One run in 18 is noise at this sample size.
- **Qwen3.6 finishes in about a third of the time**, mostly because it writes about a third as many tokens; its faster decode adds a little.
- **They fail differently.** Ornith failed one task (split) twice after long attempts of 256–343 s. Qwen3.6 failed two other tasks in short runs of 70–110 s: it stopped and reported done with the work incomplete.
- Per-task table: [`results/harness/h2h.md`](results/harness/h2h.md).

## Recommendations for a 12 GB card + 32 GB RAM

1. For Ornith, use **Q4_K_L** (or any quant with Q8_0 attention/SSM/shared-expert tensors) rather than a stock Q4_K_M. For Qwen3.6, use **Unsloth UD-Q4_K_M**. Use Q5_K_M only if you can give up decode and prefill speed. An earlier, less controlled measurement on this box gave 64 against 78 tok/s decode and 634 against 1,123 tok/s prefill, at `--n-cpu-moe 32`.
2. Keep **`--n-cpu-moe`** hand-tuned to just under full VRAM: on Windows, leave about 0.8 GB free or prefill drops sharply. Use **MTP with 1 draft**. Skip `--moe-cache-mib` for coding.
3. **q8_0 KV** is fine.
4. For agent work, **Claude Code `--bare`** was the best harness tested. Between the two models, Qwen3.6 matched Ornith's pass rate in about a third of the time. Set `preserve_thinking` for Qwen3.6 (`--chat-template-kwargs '{"preserve_thinking":true}'`), since its template otherwise drops earlier reasoning.

## Reproducing

- **KLD (on the Windows box):** copy `corpus/*.txt` and `scripts/candidates.txt` to `C:\AI\kld\`, then run
  `powershell -File scripts\kld-sweep.ps1 -RefPath <Q8_0.gguf> -CandidatesFile C:\AI\kld\candidates.txt`.
  It needs about 12 GB of disk per corpus for the reference logits.
- **Speed (from any machine):** set `GAMER_SSH`, `GAMER_KEY` and `GAMER_URL`, then
  `scripts/ab.sh results/x.jsonl "ctl|-NCpuMoe 30" 'cand|-NCpuMoe 34 -Extra "--moe-cache-mib 1900"' "ctl|-NCpuMoe 30"`.
  It expects a `llama-up.ps1` launcher that accepts `-NCpuMoe`, `-MtpDraft`, `-Model` and `-Extra`.
- **Tables:** `python3 scripts/kld-summary.py results/kld`.

## A pitfall we hit

On macOS, `<host>.local` mDNS names also resolve to an IPv6 link-local address. llama-server bound to `0.0.0.0` never answers on it. Python's `socket.create_connection` tries IPv6 first and waits about 7.8 s for it to time out on **every new connection**. curl and Node fall back within about 250 ms ("happy eyeballs"), so the problem is invisible from those clients. A Python proxy or benchmark client should resolve IPv4 explicitly.

## License

Scripts: MIT. Corpus files keep their upstream licenses (see `corpus/SOURCES.md`).
