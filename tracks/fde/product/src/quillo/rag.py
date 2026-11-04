import re

from quillo import db
from quillo.llm import ModelServer

DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
NO_DOCUMENTS = "No documents have been ingested yet."
SYSTEM_PROMPT = (
    "You answer questions about the customer's documents. Use only the numbered passages provided. "
    "Cite the passages you used like [1] or [2]. If the passages do not contain the answer, say you don't know."
)
MARKER = re.compile(r"\[(\d+)\]")


def embed_documents(embedder: ModelServer, texts: list[str]) -> list[list[float]]:
    return embedder.embed([DOCUMENT_PREFIX + text for text in texts])


def build_prompt(question: str, passages: list[dict]) -> str:
    context = "\n\n".join(f"[{i}] ({p['filename']}) {p['text']}" for i, p in enumerate(passages, start=1))
    return f"Passages:\n\n{context}\n\nQuestion: {question}"


def cited(answer: str, passages: list[dict]) -> list[dict]:
    """Đoạn được câu trả lời trích ([n]) theo thứ tự xuất hiện; model không trích thì trả mọi đoạn đã đưa vào."""
    numbers = []
    for match in MARKER.finditer(answer):
        n = int(match.group(1))
        if 1 <= n <= len(passages) and n not in numbers:
            numbers.append(n)
    return [passages[n - 1] for n in numbers] or passages


def answer(conn, embedder: ModelServer, llm: ModelServer, question: str, top_k: int) -> dict:
    [query] = embedder.embed([QUERY_PREFIX + question])
    passages = db.search(conn, query, top_k)
    if not passages:
        return {"answer": NO_DOCUMENTS, "citations": [], "model": "", "passages": []}
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, passages)}]
    text, model = llm.chat(messages)
    return {"answer": text, "citations": cited(text, passages), "model": model, "passages": passages}
