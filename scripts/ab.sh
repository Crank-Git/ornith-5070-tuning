#!/bin/bash
# Interleaved A/B of llama-server launch configs on the Windows inference box.
#
# usage: ab.sh <out.jsonl> "<name>|<llama-up args>" ...
#   e.g. ab.sh results/moe-cache.jsonl "ctl|-NCpuMoe 30" 'c1800|-NCpuMoe 34 -Extra "--moe-cache-mib 1800"' "ctl|-NCpuMoe 30"
#
# Env: GAMER_SSH (ssh target, e.g. user@host), GAMER_KEY (ssh key path), GAMER_URL (http://host:8888).
# For each config: restart the server through llama-up.ps1, record VRAM and the log tail, run bench.py.
set -u
out=$1; shift
here=$(cd "$(dirname "$0")" && pwd)
ssh_=(ssh -o ConnectTimeout=10 -i "$GAMER_KEY" "$GAMER_SSH")
for cfg in "$@"; do
  name=${cfg%%|*}; args=${cfg#*|}; args_j=${args//\"/\\\"}
  echo "=== $(date +%T) $name: $args"
  if ! "${ssh_[@]}" "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\AI\\scripts\\llama-up.ps1 $args" ; then
    echo "{\"config\": \"$name\", \"args\": \"$args_j\", \"error\": \"start failed\"}" >> "$out"; continue
  fi
  vram=$("${ssh_[@]}" "nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits" | tr -d '\r')
  moe=$("${ssh_[@]}" "powershell -NoProfile -Command \"Get-Content C:\\AI\\logs\\llama.err.log -Tail 400 | Select-String -Pattern 'moe.cache|moe_cache|expert cache' | Select-Object -Last 3 | ForEach-Object { \$_.Line }\"" | tr -d '\r' | tr '\n' ' ' | tr '"' "'")
  echo "{\"config\": \"$name\", \"args\": \"$args_j\", \"vram_used_total_util\": \"$vram\", \"moe_log\": \"$moe\"}" >> "$out"
  python3 -I "$here/bench.py" "$GAMER_URL" "$name" "$out" --samples "${SAMPLES:-6}" | tail -1
done
