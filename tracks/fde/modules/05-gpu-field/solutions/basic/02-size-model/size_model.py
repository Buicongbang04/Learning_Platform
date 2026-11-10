MIB = 1048576
CTX_STEP = 256


def weights_mb(model: dict, bits_per_weight: float | None, file_bytes: int | None) -> float:
    if (bits_per_weight is None) == (file_bytes is None):
        raise ValueError("cần đúng một trong bits_per_weight hoặc file_bytes")
    if file_bytes is not None:
        return file_bytes / MIB
    return model["params_b"] * 1e9 * bits_per_weight / 8 / MIB


def kv_mb(model: dict, ctx: int, batch: int, kv_bytes: float) -> float:
    head_dim = model["hidden_size"] // model["n_heads"]
    return 2 * model["n_layers"] * model["n_kv_heads"] * head_dim * ctx * batch * kv_bytes / MIB


def size_model(model: dict, *, ctx: int, memory_mb: float, batch: int = 1, bits_per_weight: float | None = None,
               file_bytes: int | None = None, kv_bytes: float = 2.0, overhead_mb: float = 512.0) -> dict:
    if not 1 <= ctx <= model["ctx_train"]:
        raise ValueError(f"ctx phải trong 1..{model['ctx_train']}, nhận {ctx}")
    if batch < 1:
        raise ValueError(f"batch phải ≥ 1, nhận {batch}")
    weights = weights_mb(model, bits_per_weight, file_bytes)
    kv = kv_mb(model, ctx, batch, kv_bytes)
    total = weights + kv + overhead_mb
    room = memory_mb - weights - overhead_mb
    per_token = kv_mb(model, 1, batch, kv_bytes)
    max_ctx = 0 if room < 0 else min(int(room / per_token) // CTX_STEP * CTX_STEP, model["ctx_train"])

    def fits(tokens: int) -> bool:
        return weights + kv_mb(model, tokens, batch, kv_bytes) + overhead_mb <= memory_mb

    while max_ctx > 0 and not fits(max_ctx):
        max_ctx -= CTX_STEP
    while max_ctx + CTX_STEP <= model["ctx_train"] and fits(max_ctx + CTX_STEP):
        max_ctx += CTX_STEP
    return {"weights_mb": weights, "kv_mb": kv, "total_mb": total, "fits": total <= memory_mb, "max_ctx": max_ctx}
