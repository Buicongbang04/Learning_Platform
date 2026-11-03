import torch


def peak_memory_mib(model: torch.nn.Module, batch_sizes: list[int], size: int = 128, dtype: torch.dtype = torch.float32,
                    channels_last: bool = False) -> dict[int, float]:
    # TODO: model lên CUDA theo dtype (và channels_last nếu bật); mỗi batch: đo bộ nhớ đỉnh tăng thêm khi suy luận (MiB)
    raise NotImplementedError
