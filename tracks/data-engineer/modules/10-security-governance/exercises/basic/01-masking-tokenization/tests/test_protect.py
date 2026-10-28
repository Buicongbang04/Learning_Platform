import pandas as pd
import pytest
from cryptography.fernet import Fernet

from testkit import Exercise

ex = Exercise(__file__)
KEY = b"test-secret-key"


@pytest.fixture(scope="module")
def p():
    return ex.module("protect.py")


def test_mask_email(p):
    assert p.mask_email("maria.silva@gmail.com") == "m***@gmail.com"
    assert p.mask_email("a@olist.com.br") == "a***@olist.com.br"
    assert p.mask_email("khong-phai-email") == "***"
    assert p.mask_email("@x.com") == "***"
    assert p.mask_email(None) is None


def test_mask_phone(p):
    assert p.mask_phone("+55 (11) 98765-4321") == "*********4321"
    assert p.mask_phone("0912 345 678") == "******5678"
    assert p.mask_phone("123") == "***"
    assert p.mask_phone(None) is None


def test_pseudonymize(p):
    a = p.pseudonymize("861eff4711a542e4b93843c6dd7febb0", KEY)
    assert a == p.pseudonymize("861eff4711a542e4b93843c6dd7febb0", KEY)
    assert len(a) == 16 and all(c in "0123456789abcdef" for c in a)
    assert a != p.pseudonymize("861eff4711a542e4b93843c6dd7febb0", b"other-key")
    assert a != p.pseudonymize("861eff4711a542e4b93843c6dd7febb1", KEY)
    assert len(p.pseudonymize("x", KEY, length=32)) == 32
    # đúng là HMAC-SHA256, không phải SHA-256 trần
    import hashlib, hmac
    assert a == hmac.new(KEY, b"861eff4711a542e4b93843c6dd7febb0", hashlib.sha256).hexdigest()[:16]


def test_tokenizer(p):
    t = p.Tokenizer(Fernet.generate_key(), KEY)
    tok = t.tokenize("4111111111111111")
    assert tok.startswith("tok_") and len(tok) == 28
    assert t.tokenize("4111111111111111") == tok
    assert t.tokenize("5500000000000004") != tok
    assert len(t.vault) == 2
    for v in t.vault.values():
        assert isinstance(v, bytes)
        assert b"4111111111111111" not in v and b"5500000000000004" not in v
    assert t.detokenize(tok) == "4111111111111111"
    with pytest.raises(KeyError):
        t.detokenize("tok_000000000000000000000000")


def test_mask_dataframe(p):
    df = pd.DataFrame({
        "customer_id": ["c1", "c2", None],
        "email": ["ana@gmail.com", "bob@uol.com.br", None],
        "phone": ["11987654321", "21912345678", "123"],
        "cpf": ["123.456.789-09", "987.654.321-00", "111.222.333-44"],
        "notes": ["x", "y", "z"],
        "customer_state": ["SP", "RJ", "MG"],
    })
    original = df.copy()
    out = p.mask_dataframe(df, {"customer_id": "pseudonym", "email": "email", "phone": "phone",
                                "cpf": "drop", "notes": "redact"}, KEY)
    pd.testing.assert_frame_equal(df, original)
    assert "cpf" not in out.columns
    assert list(out["email"])[:2] == ["a***@gmail.com", "b***@uol.com.br"]
    assert out["phone"].tolist() == ["*******4321", "*******5678", "***"]
    assert out["customer_id"].iloc[0] == p.pseudonymize("c1", KEY)
    assert out["customer_id"].iloc[2] is None or pd.isna(out["customer_id"].iloc[2])
    assert set(out["notes"]) == {"REDACTED"}
    assert out["customer_state"].tolist() == ["SP", "RJ", "MG"]
    with pytest.raises(ValueError):
        p.mask_dataframe(df, {"email": "rot13"}, KEY)
