#!/bin/sh
set -eu
image=$1
model=$2
threads=$3
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
name="grader-$port"
work=$(mktemp -d "$HOME/.grader-measure.XXXXXX")
trap 'docker rm -f "$name" >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
trap 'exit 130' INT TERM HUP
docker run -d --name "$name" -p "127.0.0.1:$port:8080" -v "$(dirname "$model"):/models:ro" "$image" \
    -m "/models/$(basename "$model")" -c 4096 -np 1 -t "$threads" --host 0.0.0.0 --port 8080 >/dev/null
i=0
until [ "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health")" = 200 ]; do
    i=$((i + 1))
    [ "$i" -lt 360 ] || { echo "server không lên" >&2; exit 1; }
    sleep 0.5
done
prompt='Viết một đoạn ngắn hướng dẫn bảo trì máy CNC cho ca đêm.'
body() { printf '{"prompt":"%s","n_predict":%s,"ignore_eos":true,"cache_prompt":false,"temperature":0}' "$prompt" "$1"; }
curl -sf --noproxy '*' -m 120 "http://127.0.0.1:$port/completion" -d "$(body 8)" >/dev/null
for r in 1 2 3; do
    curl -sf --noproxy '*' -m 120 "http://127.0.0.1:$port/completion" -d "$(body 64)" > "$work/run-$r.json"
done
pid=$(docker inspect -f '{{.State.Pid}}' "$name")
hwm=$(awk '/^VmHWM:/ {print $2}' "/proc/$pid/status")
python3 - "$work" "$hwm" <<'PY'
import json, sys
runs = [json.load(open(f"{sys.argv[1]}/run-{r}.json"))["timings"] for r in (1, 2, 3)]
tps = sum(t["predicted_n"] for t in runs) / (sum(t["predicted_ms"] for t in runs) / 1000)
print(json.dumps({"tokens_per_s": tps, "peak_rss_mb": int(sys.argv[2]) / 1024}))
PY
