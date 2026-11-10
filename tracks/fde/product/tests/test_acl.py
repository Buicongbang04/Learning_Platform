import psycopg
import pytest

from quillo import acl
from quillo_support import AUTH, bearer, upload
from test_worker import make_old, migrated, run_worker

GOVERNING = "This agreement is governed by the law of the State of New York. Governing law clause. "
PAYMENT = "Payment is due within thirty days of the invoice date. "


def test_acl_parse_and_prefixes():
    rules = acl.parse("legal:legal/, finance:finance,ops:/shared/ops/")
    assert rules == [("legal", "legal/"), ("finance", "finance/"), ("ops", "shared/ops/")]
    assert acl.prefixes(rules, {"finance", "it"}) == ["finance/"]
    assert acl.prefixes(rules, set()) == []
    assert acl.parse("") == []
    for bad in ("legal", "legal:", ":legal/", "legal:../x/", "a b:legal/"):
        with pytest.raises(ValueError):
            acl.parse(bad)
    assert acl.visible("legal/nda.pdf", ["legal/"])
    assert not acl.visible("legalese/nda.pdf", ["legal/"]) and not acl.visible("nda.pdf", ["legal/"])


def test_acl_filters_citations(sso_client, idp, fake_llm):
    legal = [upload(sso_client, f"nda-{i}.txt", f"Contract {i}. " + GOVERNING * 3, folder="legal").json()
             for i in range(6)]
    finance = upload(sso_client, "invoice.txt", PAYMENT * 3, folder="finance").json()
    legal_ids = {d["doc_id"] for d in legal}
    asked = sso_client.post("/api/ask", headers=bearer(idp.token("u-binh", ["/finance"])),
                            json={"question": "Which law governs this agreement?", "top_k": 2})
    assert asked.status_code == 200, asked.text
    citations = asked.json()["citations"]
    assert citations, "ACL phải lọc trong truy vấn: lọc sau top_k thì người nhóm finance không còn đoạn nào"
    assert {c["doc_id"] for c in citations} == {finance["doc_id"]}
    assert not legal_ids & {c["doc_id"] for c in citations}
    assert "New York" not in fake_llm.chats[-1]["messages"][-1]["content"]
    as_legal = sso_client.post("/api/ask", headers=bearer(idp.token("u-an", ["/legal"])),
                               json={"question": "Which law governs this agreement?", "top_k": 2}).json()
    assert {c["doc_id"] for c in as_legal["citations"]} <= legal_ids


def test_acl_unmatched_admin_only(sso_client, idp, fake_llm):
    fake_llm.answer = "Governed by New York law (no passage markers, so every passage is a citation)."
    memo = upload(sso_client, "memo.txt", GOVERNING * 3).json()
    other = upload(sso_client, "x.txt", GOVERNING * 2 + " Other.", folder="legalese").json()
    for token in (idp.token("u-chi", ["/legal", "/finance"]), idp.token("u-nobody", [])):
        assert sso_client.get("/api/documents", headers=bearer(token)).json() == []
        asked = sso_client.post("/api/ask", headers=bearer(token), json={"question": "Which law governs?"}).json()
        assert asked["citations"] == []
    assert not fake_llm.chats
    admin = sso_client.post("/api/ask", headers=AUTH, json={"question": "Which law governs?"}).json()
    assert {c["doc_id"] for c in admin["citations"]} == {memo["doc_id"], other["doc_id"]}


def test_upload_folder_is_sanitized_and_checked(sso_client, idp):
    stored = upload(sso_client, "nda.txt", GOVERNING, folder="../legal//sub dir;rm/").json()
    assert stored["filename"] == "legal/sub dir_rm/nda.txt"
    binh = bearer(idp.token("u-binh", ["/finance"]))
    assert upload(sso_client, "a.txt", PAYMENT, headers=binh, folder="legal").status_code == 403
    assert upload(sso_client, "a.txt", PAYMENT, headers=binh).status_code == 403
    assert upload(sso_client, "a.txt", PAYMENT, headers=binh, folder="finance/q3").status_code == 201
    assert upload(sso_client, "copy.txt", GOVERNING, headers=binh, folder="finance").status_code == 403
    listing = sso_client.get("/api/documents", headers=AUTH).json()
    assert sorted(d["filename"] for d in listing) == ["finance/q3/a.txt", "legal/sub dir_rm/nda.txt"]


def test_worker_keeps_subfolder(database_url, fake_llm, tmp_path):
    from quillo_support import make_settings

    migrated(database_url)
    inbox = tmp_path / "inbox"
    (inbox / "legal" / "2024").mkdir(parents=True)
    (inbox / "legal" / "nda-01.txt").write_text(GOVERNING)
    (inbox / "legal" / "2024" / "nda-02.txt").write_text(GOVERNING + " 2024.")
    (inbox / "top.txt").write_text(PAYMENT)
    make_old(*[p for p in inbox.rglob("*") if p.is_file()])
    settings = make_settings(database_url, fake_llm.url)
    run_worker(settings, inbox, lambda: len([p for p in (inbox / "done").rglob("*") if p.is_file()]) >= 3
               if (inbox / "done").exists() else False)
    assert (inbox / "done" / "legal" / "nda-01.txt").is_file()
    assert (inbox / "done" / "legal" / "2024" / "nda-02.txt").is_file()
    with psycopg.connect(database_url) as conn:
        names = sorted(r[0] for r in conn.execute("SELECT filename FROM documents"))
    assert names == ["legal/2024/nda-02.txt", "legal/nda-01.txt", "top.txt"]
