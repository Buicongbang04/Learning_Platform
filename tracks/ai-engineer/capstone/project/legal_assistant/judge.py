"""M03: chấm độ trung thực bằng LLM-as-judge và tổng hợp số liệu RAG.

Định nghĩa faithfulness giống bài Advanced 01 module 13: judge tách câu trả lời thành khẳng định, đánh dấu từng
khẳng định có được nguồn ủng hộ; điểm = tỉ lệ được ủng hộ. Đúng theo hiểu biết chung mà không có trong nguồn là
**không** được ủng hộ.
"""

from __future__ import annotations

FAITHFULNESS_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"claim": {"type": "string"}, "supported": {"type": "boolean"}},
                "required": ["claim", "supported"],
            },
        }
    },
    "required": ["claims"],
}


def judge_faithfulness(answer: str, passages: list[str], llm) -> float:
    """Gọi `llm.chat(messages, json_schema=FAITHFULNESS_SCHEMA)` đúng một lần; prompt chứa câu trả lời và mọi đoạn nguồn.

    Trả tỉ lệ khẳng định `supported` trong [0, 1]. JSON hỏng, sai cấu trúc, `supported` không phải bool, không có
    khẳng định nào, hoặc lời gọi lỗi (`llmkit.LLMError`): trả `nan`, không crash.
    """
    raise NotImplementedError("M03: judge_faithfulness")


def rag_summary(records: list[dict]) -> dict:
    """Tổng hợp một lượt chạy. Mỗi bản ghi có `refused` (bool), `citations` (uid được trích), `context` (uid các
    passage đã vào prompt), `relevant` (uid đúng theo qrels), `faithfulness` (float hoặc `nan`, có thể thiếu).

    Trả dict:
    - `n`; `context_hit`: tỉ lệ bản ghi có ít nhất một uid đúng trong `context`;
    - `refused`: tỉ lệ từ chối; `refused_with_hit`: **số** bản ghi từ chối dù `context` có uid đúng;
    - `cited_any`: tỉ lệ có ít nhất một trích dẫn; `cited_correct`: tỉ lệ trích ít nhất một uid đúng;
    - `citation_precision`: trên các bản ghi không từ chối, số trích dẫn đúng / tổng số trích dẫn (`nan` nếu không
      có trích dẫn nào);
    - `faithfulness`: trung bình điểm judge của bản ghi không từ chối, bỏ `nan`; `fully_faithful`: tỉ lệ điểm đúng
      1.0 trong các điểm đó (`nan` nếu không có điểm nào); `judge_nan`: số bản ghi không từ chối mà điểm là `nan`.

    Danh sách rỗng: `ValueError`.
    """
    raise NotImplementedError("M03: rag_summary")
