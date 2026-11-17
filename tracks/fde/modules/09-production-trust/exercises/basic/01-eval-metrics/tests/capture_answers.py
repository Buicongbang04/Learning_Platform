"""Ghi lại fixture của bài: câu trả lời thật của quillo 1.0.0 (`llm-small`, CPU) trên hợp đồng CUAD v1.

Chạy từ gốc repo (cần snapshot `07-customer-integration-quillo` và `data/raw/cuad/`):
`PYTHONPATH=. uv run python tracks/fde/modules/09-production-trust/exercises/basic/01-eval-metrics/tests/capture_answers.py`

Nạp nguyên văn `context` của từng hợp đồng trong `CUAD_v1.json` dưới dạng `.txt`, hỏi từng câu, rồi đổi mỗi trích dẫn
(`doc_id`, `chunk`) thành vị trí ký tự `[start, end)` trong `context` theo đúng cách quillo cắt đoạn. Fixture không chứa
văn bản hợp đồng, chỉ vị trí; nhãn lấy từ `answers` (answer_start + độ dài) của CUAD.
"""

import json
import re
import time
from pathlib import Path

import requests

import fdekit

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures" / "cuad-eval.json"
CUAD = fdekit.ROOT / "data" / "raw" / "cuad" / "CUAD_v1" / "CUAD_v1.json"
QUILLO = "/home/fde/quillo-1.0.0"
TOP_K = 3
CONTRACTS = {
    "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT": "Ability services agreement",
    "CENTRACKINTERNATIONALINC_10_29_1999-EX-10.3-WEB SITE HOSTING AGREEMENT": "Centrack web site hosting agreement",
    "GULFSOUTHMEDICALSUPPLYINC_12_24_1997-EX-4-AFFILIATE AGREEMENT": "Gulf South Medical Supply affiliate agreement",
    "AzulSa_20170303_F-1A_EX-10.3_9943903_EX-10.3_Maintenance Agreement2": "Azul maintenance agreement",
    "SimplicityEsportsGamingCompany_20181130_8-K_EX-10.1_11444071_EX-10.1_Franchise Agreement":
        "Simplicity Esports franchise agreement",
    "LegacyEducationAllianceInc_20141110_8-K_EX-10.9_8828866_EX-10.9_Endorsement Agreement":
        "Legacy Education endorsement agreement",
}
TEMPLATES = {
    "Governing Law": "Which law governs the {name}?",
    "Expiration Date": "When does the {name} expire?",
    "Agreement Date": "On what date was the {name} signed?",
    "Insurance": "What insurance must be maintained under the {name}?",
    "Cap On Liability": "Is liability capped in the {name}, and at what amount?",
    "Termination For Convenience": "Can a party terminate the {name} for convenience, and with how much notice?",
    "Non-Compete": "Does the {name} restrict a party from competing?",
    "Audit Rights": "Does the {name} give a party the right to audit records?",
    "Source Code Escrow": "Does the {name} require source code to be placed in escrow?",
    "Most Favored Nation": "Does the {name} contain a most favored nation pricing clause?",
    "Liquidated Damages": "What liquidated damages are set in the {name}?",
    "Exclusivity": "Is either party granted exclusivity under the {name}?",
}
PER_CONTRACT_ANSWERABLE = 4
PER_CONTRACT_IMPOSSIBLE = 2


def word_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]


def chunk_offsets(text: str, size: int = 1000, overlap: int = 150) -> list[tuple[int, int]]:
    """Cùng thuật toán với `quillo.ingest.chunk`, nhưng trả vị trí ký tự của mỗi đoạn trong văn bản gốc."""
    spans = word_spans(text)
    words = [text[a:b] for a, b in spans]
    out: list[tuple[int, int]] = []
    start = 0
    while start < len(words):
        end, length = start, 0
        while end < len(words) and length + len(words[end]) + (end > start) <= size:
            length += len(words[end]) + (end > start)
            end += 1
        end = max(end, start + 1)
        out.append((spans[start][0], spans[end - 1][1]))
        if end >= len(words):
            break
        back, kept = end, 0
        while back > start + 1 and kept + len(words[back - 1]) + 1 <= overlap:
            back -= 1
            kept += len(words[back]) + 1
        start = back
    return out


def select_items(entries: dict) -> list[dict]:
    items = []
    for title, name in CONTRACTS.items():
        qas = {qa["id"].split("__", 1)[1]: qa for qa in entries[title]["paragraphs"][0]["qas"]}
        answerable = [c for c in TEMPLATES if c in qas and qas[c]["answers"]][:PER_CONTRACT_ANSWERABLE]
        impossible = [c for c in TEMPLATES if c in qas and not qas[c]["answers"]][:PER_CONTRACT_IMPOSSIBLE]
        for clause in answerable + impossible:
            spans = sorted({(a["answer_start"], a["answer_start"] + len(a["text"])) for a in qas[clause]["answers"]})
            items.append({"id": f"{name.split()[0].lower()}-{clause.lower().replace(' ', '-')}", "contract": title,
                          "clause": clause, "question": TEMPLATES[clause].format(name=name),
                          "gold": [list(s) for s in spans]})
    return items


def main() -> None:
    entries = {e["title"]: e for e in json.loads(CUAD.read_text(encoding="utf-8"))["data"]}
    items = select_items(entries)
    with fdekit.customer_site("lab-open", base=fdekit.derived("07-customer-integration-quillo"), memory_mb=3072,
                              forwards=(18080,)) as site:
        api = f"http://127.0.0.1:{site.vm.port(18080)}"
        token = site.vm.ssh(f"sed -n 's/^QUILLO_ADMIN_TOKEN=//p' {QUILLO}/.env", timeout=60).stdout.strip()
        auth = {"Authorization": f"Bearer {token}"}
        deadline = time.monotonic() + 180
        while True:
            try:
                if requests.get(f"{api}/healthz", timeout=5).status_code == 200:
                    break
            except requests.RequestException:
                pass
            if time.monotonic() > deadline:
                raise SystemExit("quillo không lên")
            time.sleep(2)
        doc_ids = {}
        for title, name in CONTRACTS.items():
            body = entries[title]["paragraphs"][0]["context"].encode("utf-8")
            done = requests.post(f"{api}/api/documents", headers=auth, timeout=600,
                                 files={"file": (f"{name}.txt", body, "text/plain")})
            done.raise_for_status()
            doc_ids[done.json()["doc_id"]] = title
            print("nạp", name, done.json())
        for item in items:
            started = time.monotonic()
            response = requests.post(f"{api}/api/ask", headers=auth, timeout=600,
                                     json={"question": item["question"], "top_k": TOP_K})
            response.raise_for_status()
            body = response.json()
            item["seconds"] = round(time.monotonic() - started, 2)
            item["answer"] = body["answer"]
            item["citations"] = []
            for citation in body["citations"]:
                title = doc_ids[citation["doc_id"]]
                text = entries[title]["paragraphs"][0]["context"]
                start, end = chunk_offsets(text)[citation["chunk"]]
                assert " ".join(text[start:end].split())[:1000] == citation["text"], (title, citation["chunk"])
                item["citations"].append({"contract": title, "chunk": citation["chunk"], "start": start, "end": end})
            print(item["id"], item["seconds"], repr(item["answer"][:100]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "CUAD v1 (The Atticus Project, CC BY 4.0), data/raw/cuad/CUAD_v1/CUAD_v1.json",
        "system": "quillo 1.0.0, llm-small (Qwen2.5-0.5B-Instruct Q4_K_M), top_k 3, CPU",
        "items": items,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("ghi", OUT, len(items), "câu")


if __name__ == "__main__":
    main()
