import torch


def peak_memory_mib(model: torch.nn.Module, batch_sizes: list[int], size: int = 128, dtype: torch.dtype = torch.float32,
                    channels_last: bool = False) -> dict[int, float]:
    device = torch.device("cuda")
    layout = torch.channels_last if channels_last else torch.contiguous_format
    model = model.to(device=device, dtype=dtype, memory_format=layout).eval()
    peaks = {}
    for batch in batch_sizes:
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        baseline = torch.cuda.memory_allocated()
        x = torch.randn(batch, 3, size, size, device=device, dtype=dtype).contiguous(memory_format=layout)
        with torch.inference_mode():
            model(x)
        torch.cuda.synchronize()
        peaks[batch] = (torch.cuda.max_memory_allocated() - baseline) / 2**20
    return peaks
