#!/bin/sh
set -eu
work=${1:?Cách dùng: sh bench_pc.sh <thư mục làm việc>}
model=${FDE_PC_MODEL:-$HOME/fde-models/qwen2.5-1.5b-instruct-q4_k_m.gguf}
cpu_image=ghcr.io/ggml-org/llama.cpp:server-b11718
gpu_image=ghcr.io/ggml-org/llama.cpp:server-cuda-b11718
tag=$(basename "$work")
started=""

cleanup() {
    trap - EXIT INT TERM HUP
    for name in $started; do docker rm -f "$name" >/dev/null 2>&1 || true; done
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP

[ -f "$model" ] || { echo "bench_pc: thiếu $model" >&2; exit 1; }
for image in "$cpu_image" "$gpu_image"; do
    docker image inspect "$image" >/dev/null 2>&1 || { echo "bench_pc: thiếu image $image" >&2; exit 1; }
done
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits > "$work/gpu.csv"
cores=$(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)

run() {
    name="$tag-$1"
    port=$2
    shift 2
    started="$started $name"
    docker run -d --name "$name" -p "127.0.0.1:$port:8080" -v "$(dirname "$model"):/models:ro" "$@" \
        -m "/models/$(basename "$model")" -c 4096 -np 1 -t "$cores" --host 0.0.0.0 --port 8080 >/dev/null
    i=0
    until [ "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health")" = 200 ]; do
        i=$((i + 1))
        [ "$i" -lt 240 ] || { docker logs --tail 20 "$name" >&2; echo "bench_pc: $name không lên" >&2; exit 1; }
        sleep 0.5
    done
    body='{"prompt":"Viết một đoạn ngắn hướng dẫn bảo trì máy CNC cho ca đêm.","n_predict":128,"ignore_eos":true,"cache_prompt":false,"temperature":0}'
    curl -s --noproxy '*' "http://127.0.0.1:$port/completion" -d "$body" > /dev/null
    for r in 1 2 3; do
        curl -s --noproxy '*' "http://127.0.0.1:$port/completion" -d "$body" > "$work/$1-$r.json"
    done
    docker rm -f "$name" >/dev/null
}

run cpu 18091 "$cpu_image"
run gpu 18092 --gpus all "$gpu_image" -ngl 99

python3 - "$work" <<'PY'
import json, sys
work = sys.argv[1]
def tps(kind):
    runs = [json.load(open(f"{work}/{kind}-{r}.json"))["timings"] for r in (1, 2, 3)]
    return round(sum(t["predicted_n"] for t in runs) / (sum(t["predicted_ms"] for t in runs) / 1000), 2)
name, memory, driver = (p.strip() for p in open(f"{work}/gpu.csv").readline().split(","))
print(json.dumps({"gpu": {"name": name, "memory_mb": int(float(memory)), "driver": driver},
                  "cpu_tokens_per_s": tps("cpu"), "gpu_tokens_per_s": tps("gpu")}))
PY
