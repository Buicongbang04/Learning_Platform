import torch

IGNORE_INDEX = -100


def tokenize_chat(messages: list[dict], tokenizer, max_length: int | None = None) -> dict | None:
    """input_ids của cả hội thoại theo chat template; labels chỉ giữ token của các lượt assistant, còn lại -100."""
    # TODO
    raise NotImplementedError


def pad_batch(examples: list[dict], pad_token_id: int, multiple_of: int = 1) -> dict[str, torch.Tensor]:
    # TODO
    raise NotImplementedError


def pack_examples(examples: list[dict], block_size: int) -> list[dict]:
    # TODO
    raise NotImplementedError


def real_token_fraction(lengths: list[int], batch_size: int) -> float:
    # TODO
    raise NotImplementedError
