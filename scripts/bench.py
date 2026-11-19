#!/usr/bin/env python3
"""Decode/prefill benchmark against a running llama-server, using the server's own timings.

Usage: bench.py <base_url> <config_name> <out.jsonl> [--samples N] [--prefill-chars N]

Each run sends:
  - N greedy decode requests per prompt kind (code, prose), 512 new tokens, prompt cache off;
  - 3 prefill requests of a long code prompt with 1 new token.
Greedy (temperature 0) keeps the generated text, and so the MTP acceptance, the same across
configs. Every request's timings go to out.jsonl, plus a summary line with medians.
"""
import argparse
import hashlib
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

PROMPTS = {
    "code": "Write a complete, idiomatic Go package `lru` implementing a thread-safe LRU cache with "
            "generics, TTL expiry per entry, an eviction callback, and table-driven tests. Output only code.",
    "prose": "Explain, in about 600 words of plain prose with no lists or headings, how a mixture-of-experts "
             "language model decides which experts to use for each token, and why that makes it cheap to run.",
}


def post(base, body, timeout=1800):
    req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def one(base, messages, max_tokens):
    body = {"messages": messages, "max_tokens": max_tokens, "temperature": 0, "top_k": 1,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.time()
    r = post(base, body)
    t = r.get("timings", {})
    text = r["choices"][0]["message"].get("content") or ""
    return {"wall_s": round(time.time() - t0, 2), "prompt_n": t.get("prompt_n"),
            "prompt_tps": t.get("prompt_per_second"), "gen_n": t.get("predicted_n"),
            "gen_tps": t.get("predicted_per_second"), "draft_n": t.get("draft_n"),
            "draft_accepted": t.get("draft_n_accepted"),
            "text_sha": hashlib.sha256(text.encode()).hexdigest()[:12]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("config")
    ap.add_argument("out")
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--prefill-file", default=str(Path(__file__).parent.parent / "corpus" / "code.txt"))
    ap.add_argument("--prefill-chars", type=int, default=60000)  # ~16K tokens of code
    a = ap.parse_args()

    rows = []
    one(a.base, [{"role": "user", "content": "Say hi."}], 8)  # warm-up
    for kind, prompt in PROMPTS.items():
        for i in range(a.samples):
            r = one(a.base, [{"role": "user", "content": prompt}], 512)
            r.update(config=a.config, kind=kind, i=i)
            rows.append(r)
            print(json.dumps(r), flush=True)
    code = Path(a.prefill_file).read_text()
    for i in range(3):
        # A different offset each time, so no prefix can be reused.
        chunk = code[i * 7000: i * 7000 + a.prefill_chars]
        r = one(a.base, [{"role": "user", "content": "Summarize this code in one line.\n\n" + chunk}], 1)
        r.update(config=a.config, kind="prefill", i=i)
        rows.append(r)
        print(json.dumps(r), flush=True)

    def med(kind, key):
        v = [r[key] for r in rows if r["kind"] == kind and r.get(key)]
        return round(statistics.median(v), 2) if v else None

    summary = {"config": a.config, "summary": True, "t": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "code_tps": med("code", "gen_tps"), "prose_tps": med("prose", "gen_tps"),
               "prefill_tps": med("prefill", "prompt_tps"), "prefill_tokens": med("prefill", "prompt_n"),
               "code_sha": sorted({r["text_sha"] for r in rows if r["kind"] == "code"}),
               "prose_sha": sorted({r["text_sha"] for r in rows if r["kind"] == "prose"})}
    print(json.dumps(summary), flush=True)
    with open(a.out, "a") as f:
        for r in rows + [summary]:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    sys.exit(main())
