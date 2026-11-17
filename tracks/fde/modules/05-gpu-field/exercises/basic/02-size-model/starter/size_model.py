def size_model(model: dict, *, ctx: int, memory_mb: float, batch: int = 1, bits_per_weight: float | None = None,
               file_bytes: int | None = None, kv_bytes: float = 2.0, overhead_mb: float = 512.0) -> dict:
    """Trả weights_mb, kv_mb, total_mb, fits, max_ctx theo công thức trong README."""
    raise NotImplementedError("TODO: trọng số, KV cache, tổng, ctx tối đa")
