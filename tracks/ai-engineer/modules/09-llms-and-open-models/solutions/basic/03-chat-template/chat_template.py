"""Chat template viết tay: đổi danh sách message thành đúng chuỗi mà model instruct đã thấy lúc fine-tune.

Message là dict {"role": "system" | "user" | "assistant" | "tool", "content": str}.
Chỉ dùng thư viện chuẩn.
"""

from __future__ import annotations

import re
from collections.abc import Callable

QWEN_DEFAULT_SYSTEM = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."

Message = dict[str, str]


def render_qwen(messages: list[Message], add_generation_prompt: bool = True) -> str:
    """Chuỗi prompt theo chat template của Qwen2.5 (ChatML), trường hợp không truyền `tools`.

    - Message đầu là system: in nó thành khối system đầu tiên. Không có: in khối system mặc định QWEN_DEFAULT_SYSTEM.
    - Mỗi message user, assistant, hoặc system không đứng đầu: `<|im_start|>{role}\\n{content}<|im_end|>\\n`.
      Nội dung giữ nguyên, không strip.
    - Message tool: các tool liên tiếp gom vào **một** khối user: mở `<|im_start|>user` một lần, mỗi tool thêm
      `\\n<tool_response>\\n{content}\\n</tool_response>`, đóng `<|im_end|>\\n` sau tool cuối của chuỗi liên tiếp.
    - add_generation_prompt: thêm `<|im_start|>assistant\\n` ở cuối.
    """
    out = []
    if messages and messages[0]["role"] == "system":
        out.append(f"<|im_start|>system\n{messages[0]['content']}<|im_end|>\n")
        rest = messages[1:]
    else:
        out.append(f"<|im_start|>system\n{QWEN_DEFAULT_SYSTEM}<|im_end|>\n")
        rest = messages
    for i, m in enumerate(rest):
        if m["role"] == "tool":
            if i == 0 or rest[i - 1]["role"] != "tool":
                out.append("<|im_start|>user")
            out.append(f"\n<tool_response>\n{m['content']}\n</tool_response>")
            if i == len(rest) - 1 or rest[i + 1]["role"] != "tool":
                out.append("<|im_end|>\n")
        else:
            out.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n")
    if add_generation_prompt:
        out.append("<|im_start|>assistant\n")
    return "".join(out)


def render_llama3(messages: list[Message], add_generation_prompt: bool = True) -> str:
    """Chuỗi prompt theo chat template của Llama 3 Instruct.

    - `<|begin_of_text|>` một lần ở đầu (chỉ khi có ít nhất một message).
    - Mỗi message: `<|start_header_id|>{role}<|end_header_id|>\\n\\n{content đã strip}<|eot_id|>`.
    - Không có system mặc định. add_generation_prompt: thêm `<|start_header_id|>assistant<|end_header_id|>\\n\\n`.
    """
    out = ["<|begin_of_text|>"] if messages else []
    for m in messages:
        out.append(f"<|start_header_id|>{m['role']}<|end_header_id|>\n\n{m['content'].strip()}<|eot_id|>")
    if add_generation_prompt:
        out.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(out)


def parse_chatml(text: str) -> list[Message]:
    """Ngược lại của ChatML: mọi khối `<|im_start|>{role}\\n{content}<|im_end|>` thành message, theo thứ tự.

    Khối mở cuối cùng chưa có `<|im_end|>` (generation prompt) bị bỏ qua. Nội dung giữ nguyên (kể cả xuống dòng).
    """
    blocks = re.findall(r"<\|im_start\|>(\w+)\n(.*?)<\|im_end\|>", text, flags=re.S)
    return [{"role": role, "content": content} for role, content in blocks]


def fit_history(messages: list[Message], max_tokens: int, count_tokens: Callable[[str], int],
                per_message: int = 4) -> list[Message]:
    """Cắt lịch sử hội thoại cho vừa ngân sách token của context.

    Chi phí một message = count_tokens(content) + per_message (token của các thẻ role).
    - Message đầu là system thì luôn giữ (tính vào ngân sách).
    - Rồi lấy các message **mới nhất** đi ngược về trước, dừng ở message đầu tiên không còn vừa (giữ một đoạn
      liên tục ở cuối, không nhảy cóc).
    - Bỏ các message ở đầu đoạn đó cho tới khi đoạn bắt đầu bằng message user (model không nên thấy một câu trả
      lời assistant hay kết quả tool mà không có câu hỏi trước nó).
    - System (nếu có) cộng message cuối cùng đã vượt max_tokens: ValueError.
    Trả list mới, giữ nguyên các dict message.
    """
    def cost(m: Message) -> int:
        return count_tokens(m["content"]) + per_message

    head = [messages[0]] if messages and messages[0]["role"] == "system" else []
    body = messages[len(head):]
    budget = max_tokens - sum(cost(m) for m in head)
    kept: list[Message] = []
    for m in reversed(body):
        c = cost(m)
        if c > budget:
            break
        kept.append(m)
        budget -= c
    if body and not kept:
        raise ValueError("message mới nhất (cộng system) không vừa max_tokens")
    kept.reverse()
    while kept and kept[0]["role"] != "user":
        kept.pop(0)
    return head + kept
