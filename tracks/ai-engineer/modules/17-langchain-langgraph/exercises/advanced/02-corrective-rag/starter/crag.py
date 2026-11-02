"""Hàm thuần của Corrective RAG: quyết định bước tiếp theo sau khi chấm, và đo độ khớp của bộ chấm với qrels."""


def decide_next(relevant: list[str], rewrites: int, max_rewrites: int) -> str:
    """Sau bước chấm: còn nguồn được chấm là liên quan thì "answer"; không còn mà số lần viết lại < max_rewrites thì
    "rewrite"; ngược lại "refuse"."""
    # TODO
    raise NotImplementedError


def grader_agreement(rounds: list[dict]) -> dict:
    """Độ khớp của bộ chấm LLM với qrels trên mọi lượt chấm.

    Mỗi phần tử của `rounds`: {"uids": các nguồn đã đưa cho bộ chấm, "relevant": các uid bộ chấm giữ lại,
    "gold": tập điều đúng của câu hỏi}. Chỉ xét các uid trong "uids":
    - precision = (giữ lại và đúng) / (giữ lại); recall = (giữ lại và đúng) / (đúng); mẫu số 0 thì None;
    - judged = tổng số uid đã chấm; marked = tổng số uid được giữ lại;
    - gold_kept_rate = trong các lượt có ít nhất một điều đúng nằm trong "uids", tỉ lệ lượt giữ lại được ít nhất một
      điều đúng (không có lượt nào như vậy thì None).
    """
    # TODO
    raise NotImplementedError
