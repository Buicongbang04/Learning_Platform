import torch

IGNORE_INDEX = -100


def _ids(tokenizer, text: str) -> list[int]:
    return list(tokenizer(text, add_special_tokens=False)["input_ids"])


def tokenize_chat(messages: list[dict], tokenizer, max_length: int | None = None) -> dict | None:
    """input_ids của cả hội thoại theo chat template; labels chỉ giữ token của các lượt assistant, còn lại -100."""
    ids = _ids(tokenizer, tokenizer.apply_chat_template(messages, tokenize=False))
    labels = [IGNORE_INDEX] * len(ids)
    for i, message in enumerate(messages):
        if message["role"] != "assistant":
            continue
        prompt = _ids(tokenizer, tokenizer.apply_chat_template(messages[:i], tokenize=False,
                                                               add_generation_prompt=True))
        upto = _ids(tokenizer, tokenizer.apply_chat_template(messages[: i + 1], tokenize=False))
        if ids[: len(prompt)] != prompt or ids[: len(upto)] != upto:
            raise ValueError("chat template không cho tiền tố ổn định, không tách được lượt assistant")
        labels[len(prompt): len(upto)] = ids[len(prompt): len(upto)]
    if max_length is not None:
        ids, labels = ids[:max_length], labels[:max_length]
    if all(label == IGNORE_INDEX for label in labels):
        return None
    return {"input_ids": ids, "labels": labels}


def pad_batch(examples: list[dict], pad_token_id: int, multiple_of: int = 1) -> dict[str, torch.Tensor]:
    longest = max(len(e["input_ids"]) for e in examples)
    width = -(-longest // multiple_of) * multiple_of
    input_ids = torch.full((len(examples), width), pad_token_id, dtype=torch.long)
    labels = torch.full((len(examples), width), IGNORE_INDEX, dtype=torch.long)
    attention_mask = torch.zeros((len(examples), width), dtype=torch.long)
    for row, e in enumerate(examples):
        n = len(e["input_ids"])
        input_ids[row, :n] = torch.tensor(e["input_ids"])
        labels[row, :n] = torch.tensor(e["labels"])
        attention_mask[row, :n] = 1
    return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}


def pack_examples(examples: list[dict], block_size: int) -> list[dict]:
    blocks: list[dict] = []
    current = {"input_ids": [], "labels": [], "position_ids": []}
    for e in examples:
        ids, labels = e["input_ids"][:block_size], e["labels"][:block_size]
        if current["input_ids"] and len(current["input_ids"]) + len(ids) > block_size:
            blocks.append(current)
            current = {"input_ids": [], "labels": [], "position_ids": []}
        current["input_ids"] += ids
        current["labels"] += labels
        current["position_ids"] += list(range(len(ids)))
    if current["input_ids"]:
        blocks.append(current)
    return blocks


def real_token_fraction(lengths: list[int], batch_size: int) -> float:
    real = padded = 0
    for start in range(0, len(lengths), batch_size):
        chunk = lengths[start: start + batch_size]
        real += sum(chunk)
        padded += max(chunk) * len(chunk)
    return real / padded
