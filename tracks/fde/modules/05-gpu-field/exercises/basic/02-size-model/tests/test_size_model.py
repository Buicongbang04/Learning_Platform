import random

import pytest
import yaml

from testkit import Exercise

ex = Exercise(__file__)
MODELS = yaml.safe_load((ex.dir / "models.yaml").read_text(encoding="utf-8"))
MIB = 1048576
QWEN7_Q4KM_BYTES = 3993201344 + 689872288
QWEN15_Q4KM_BYTES = 1117320736


def reference(model, *, ctx, memory_mb, batch=1, bits_per_weight=None, file_bytes=None, kv_bytes=2.0,
              overhead_mb=512.0):
    weights = file_bytes / MIB if file_bytes is not None else model["params_b"] * 1e9 * bits_per_weight / 8 / MIB
    head_dim = model["hidden_size"] // model["n_heads"]

    def kv(tokens):
        return 2 * model["n_layers"] * model["n_kv_heads"] * head_dim * tokens * batch * kv_bytes / MIB

    total = weights + kv(ctx) + overhead_mb
    best = 0
    for tokens in range(256, model["ctx_train"] + 1, 256):
        if weights + kv(tokens) + overhead_mb <= memory_mb:
            best = tokens
    return {"weights_mb": weights, "kv_mb": kv(ctx), "total_mb": total, "fits": total <= memory_mb, "max_ctx": best}


CASES = [
    ("qwen7b-q4km-file-on-3060", "qwen2.5-7b", dict(ctx=8192, memory_mb=12288, file_bytes=QWEN7_Q4KM_BYTES), True, 32768),
    ("qwen7b-q4km-on-3060-4-users", "qwen2.5-7b", dict(ctx=32768, batch=4, memory_mb=12288, file_bytes=QWEN7_Q4KM_BYTES), True, 32768),
    ("qwen7b-fp16-on-3060", "qwen2.5-7b", dict(ctx=4096, memory_mb=12288, bits_per_weight=16), False, 0),
    ("qwen32b-q4-on-24gb", "qwen2.5-32b", dict(ctx=8192, memory_mb=24576, bits_per_weight=4.85), True, 20992),
    ("qwen32b-q4-on-24gb-ctx32k", "qwen2.5-32b", dict(ctx=32768, memory_mb=24576, bits_per_weight=4.85), False, 20992),
    ("qwen32b-q4-kv-q8", "qwen2.5-32b", dict(ctx=32768, memory_mb=24576, bits_per_weight=4.85, kv_bytes=1.0625), True, 32768),
    ("qwen72b-q4-on-48gb", "qwen2.5-72b", dict(ctx=8192, memory_mb=49152, bits_per_weight=4.85), True, 20992),
    ("qwen72b-q4-on-24gb", "qwen2.5-72b", dict(ctx=2048, memory_mb=24576, bits_per_weight=4.85), False, 0),
    ("qwen72b-fp8-on-2x80gb", "qwen2.5-72b", dict(ctx=32768, batch=8, memory_mb=163840, bits_per_weight=8, overhead_mb=4096), True, 32768),
    ("qwen1.5b-file-on-factory", "qwen2.5-1.5b", dict(ctx=4096, memory_mb=2919, file_bytes=QWEN15_Q4KM_BYTES), True, 32768),
    ("qwen1.5b-file-on-factory-busy", "qwen2.5-1.5b", dict(ctx=4096, memory_mb=1400, file_bytes=QWEN15_Q4KM_BYTES), False, 0),
    ("qwen0.5b-q8-on-1gb", "qwen2.5-0.5b", dict(ctx=32768, batch=2, memory_mb=1024, bits_per_weight=8.5), False, 512),
    ("mistral7b-q4-on-8gb", "mistral-7b-v0.3", dict(ctx=16384, memory_mb=8192, bits_per_weight=4.85, overhead_mb=700), True, 26368),
    ("mistral7b-q4-on-6gb-laptop", "mistral-7b-v0.3", dict(ctx=8192, memory_mb=6144, bits_per_weight=4.85, overhead_mb=700), True, 9984),
    ("qwen14b-q4-on-12gb", "qwen2.5-14b", dict(ctx=8192, memory_mb=12288, bits_per_weight=4.85), True, 17408),
]


@pytest.fixture(scope="module")
def mod():
    return ex.module("size_model.py")


def check(got, want, label):
    assert isinstance(got, dict), f"{label}: size_model() phải trả dict"
    for key in ("weights_mb", "kv_mb", "total_mb"):
        assert key in got and abs(got[key] - want[key]) <= 0.5, f"{label}: {key} cần {want[key]:.1f}, nhận {got.get(key)}"
    assert got.get("fits") is want["fits"], f"{label}: fits cần {want['fits']}, nhận {got.get('fits')}"
    assert got.get("max_ctx") == want["max_ctx"], f"{label}: max_ctx cần {want['max_ctx']}, nhận {got.get('max_ctx')}"


@pytest.mark.parametrize("name,kwargs,fits,max_ctx", [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_cases(mod, name, kwargs, fits, max_ctx):
    want = reference(MODELS[name], **kwargs)
    assert want["fits"] is fits and want["max_ctx"] == max_ctx
    check(mod.size_model(dict(MODELS[name]), **kwargs), want, name)


def test_random(mod):
    rng = random.Random(random.SystemRandom().randrange(1 << 30))
    for _ in range(300):
        name = rng.choice(sorted(MODELS))
        model = MODELS[name]
        kwargs = {"ctx": rng.randrange(1, model["ctx_train"] + 1), "batch": rng.randint(1, 8),
                  "memory_mb": rng.choice([1024, 2919, 4096, 6144, 8192, 12288, 16384, 24576, 49152, 81920]),
                  "kv_bytes": rng.choice([2.0, 1.0625, 0.5625]), "overhead_mb": rng.choice([256.0, 512.0, 1024.0])}
        if rng.random() < 0.5:
            kwargs["bits_per_weight"] = rng.choice([4.5, 4.85, 5.7, 6.6, 8.5, 16.0])
        else:
            kwargs["file_bytes"] = int(model["params_b"] * 1e9 * rng.uniform(0.5, 1.2))
        check(mod.size_model(dict(model), **kwargs), reference(model, **kwargs), f"{name} {kwargs}")


@pytest.mark.parametrize("kwargs", [
    dict(ctx=4096, memory_mb=8192),
    dict(ctx=4096, memory_mb=8192, bits_per_weight=4.85, file_bytes=QWEN7_Q4KM_BYTES),
    dict(ctx=65536, memory_mb=8192, bits_per_weight=4.85),
    dict(ctx=0, memory_mb=8192, bits_per_weight=4.85),
    dict(ctx=4096, batch=0, memory_mb=8192, bits_per_weight=4.85),
], ids=["no-weights", "both-weights", "ctx-over-train", "ctx-zero", "batch-zero"])
def test_bad_input(mod, kwargs):
    with pytest.raises(ValueError):
        mod.size_model(dict(MODELS["qwen2.5-7b"]), **kwargs)
