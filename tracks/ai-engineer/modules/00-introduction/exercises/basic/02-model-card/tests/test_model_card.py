import json

import pytest

from testkit import Exercise

ex = Exercise(__file__)

# Số tham số đếm bằng transformers 5.22.0 (dựng model trên device "meta" từ đúng config.json này, không tải trọng số),
# ngày 2026-10-30. Khớp con số trên model card: 0.49B, 3.09B, 7.61B, 0.6B, 30.5B (3.3B activated), 360M, 7.25B.
EXPECTED = {
    "Qwen__Qwen2.5-0.5B-Instruct": 494_032_768,
    "Qwen__Qwen2.5-3B-Instruct": 3_085_938_688,
    "Qwen__Qwen2.5-7B-Instruct": 7_615_616_512,
    "Qwen__Qwen3-0.6B": 596_049_920,
    "Qwen__Qwen3-30B-A3B-Instruct-2507": 30_532_122_624,
    "HuggingFaceTB__SmolLM2-360M-Instruct": 361_821_120,
    "mistralai__Mistral-7B-Instruct-v0.3": 7_248_023_552,
}
MOE_ACTIVE = 3_353_032_704


@pytest.fixture(scope="module")
def mc():
    return ex.module("model_card.py")


def config(name: str) -> dict:
    return json.loads((ex.fixtures / name / "config.json").read_text(encoding="utf-8"))


def card(name: str) -> str:
    return (ex.fixtures / name / "README.md").read_text(encoding="utf-8")


# ---------- read_frontmatter ----------


def test_frontmatter_real_cards(mc):
    meta = mc.read_frontmatter(card("Qwen__Qwen2.5-0.5B-Instruct"))
    assert meta["license"] == "apache-2.0"
    assert meta["base_model"] == "Qwen/Qwen2.5-0.5B"
    assert meta["tags"] == ["chat"]
    meta3 = mc.read_frontmatter(card("Qwen__Qwen2.5-3B-Instruct"))
    assert meta3["license"] == "other" and meta3["license_name"] == "qwen-research"


def test_frontmatter_stops_at_second_marker(mc):
    text = "---\nlicense: mit\n---\n# Model\n\n---\nlicense: apache-2.0\n---\n"
    assert mc.read_frontmatter(text) == {"license": "mit"}


def test_frontmatter_missing_or_empty(mc):
    assert mc.read_frontmatter("# Model không có metadata\n\nlicense: mit\n") == {}
    assert mc.read_frontmatter("---\n---\n# Model\n") == {}
    assert mc.read_frontmatter("") == {}


# ---------- count_params ----------


@pytest.mark.parametrize("name", list(EXPECTED))
def test_count_params_matches_transformers(mc, name):
    assert mc.count_params(config(name)) == EXPECTED[name]


def test_active_params_moe(mc):
    cfg = config("Qwen__Qwen3-30B-A3B-Instruct-2507")
    assert mc.count_params(cfg, active=True) == MOE_ACTIVE  # 8/128 expert, router vẫn tính đủ
    # model dense: active bằng tổng
    dense = config("Qwen__Qwen2.5-3B-Instruct")
    assert mc.count_params(dense, active=True) == EXPECTED["Qwen__Qwen2.5-3B-Instruct"]


def test_count_params_attention_bias_flag(mc):
    # Llama có attention_bias=True: thêm bias ở q, k, v, o mỗi layer
    cfg = config("HuggingFaceTB__SmolLM2-360M-Instruct")
    biased = dict(cfg, attention_bias=True)
    h, layers = 960, 32
    q_dim, kv_dim = 15 * 64, 5 * 64
    assert mc.count_params(biased) - mc.count_params(cfg) == layers * (q_dim + 2 * kv_dim + h)


def test_count_params_untied_doubles_embedding(mc):
    cfg = config("Qwen__Qwen2.5-0.5B-Instruct")
    assert mc.count_params(dict(cfg, tie_word_embeddings=False)) - mc.count_params(cfg) == 151_936 * 896


# ---------- VRAM ----------


def test_weights_gb(mc):
    assert mc.weights_gb(EXPECTED["Qwen__Qwen2.5-3B-Instruct"], 16) == pytest.approx(6.171877376, abs=1e-9)
    assert mc.weights_gb(EXPECTED["Qwen__Qwen2.5-3B-Instruct"], 4) == pytest.approx(1.542969344, abs=1e-9)
    assert mc.weights_gb(1_000_000_000, 8) == pytest.approx(1.0)


def test_kv_cache_gb(mc):
    # Qwen2.5-3B: 2 × 36 layer × 2 head KV × 128 × 4096 token × 2 byte
    assert mc.kv_cache_gb(config("Qwen__Qwen2.5-3B-Instruct"), 4096) == pytest.approx(0.150994944, abs=1e-12)
    # Qwen3-0.6B có head_dim = 128 riêng (không phải 1024 / 16 = 64)
    assert mc.kv_cache_gb(config("Qwen__Qwen3-0.6B"), 1000) == pytest.approx(0.114688, abs=1e-12)
    # tuyến tính theo batch và byte
    mistral = config("mistralai__Mistral-7B-Instruct-v0.3")
    assert mc.kv_cache_gb(mistral, 4096, batch=8, bytes_per_value=1) == pytest.approx(
        4 * mc.kv_cache_gb(mistral, 4096), abs=1e-12
    )


def test_fits_on_gpu(mc):
    q7 = config("Qwen__Qwen2.5-7B-Instruct")
    assert not mc.fits_on_gpu(q7, 12, bits=16, seq_len=4096)  # 15.2 GB trọng số
    assert mc.fits_on_gpu(q7, 12, bits=4, seq_len=4096)  # 3.81 + 0.23 + 0.5
    assert not mc.fits_on_gpu(q7, 4, bits=4, seq_len=4096)  # 4.54 GB > 4 GB
    q3 = config("Qwen__Qwen2.5-3B-Instruct")
    assert mc.fits_on_gpu(q3, 4, bits=4, seq_len=4096)
    # context dài làm tràn: 32 768 token × 16 chuỗi KV cache 19.3 GB
    assert not mc.fits_on_gpu(q3, 12, bits=4, seq_len=32768, batch=16)
    # MoE: 3.35B hoạt động nhưng VRAM phải chứa đủ 30.5B (15.3 GB ở 4 bit)
    assert not mc.fits_on_gpu(config("Qwen__Qwen3-30B-A3B-Instruct-2507"), 12, bits=4, seq_len=4096)
    # overhead được tính
    assert mc.fits_on_gpu(q3, 2.2, bits=4, seq_len=4096, overhead_gb=0.5)
    assert not mc.fits_on_gpu(q3, 2.2, bits=4, seq_len=4096, overhead_gb=0.6)


# ---------- card_summary ----------


def test_card_summary_license_trap(mc):
    s = mc.card_summary(card("Qwen__Qwen2.5-3B-Instruct"), config("Qwen__Qwen2.5-3B-Instruct"))
    assert s == {
        "license": "qwen-research",
        "base_model": "Qwen/Qwen2.5-3B",
        "params": 3_085_938_688,
        "active_params": 3_085_938_688,
        "context_length": 32768,
        "moe": False,
    }


def test_card_summary_list_base_model_and_moe(mc):
    s = mc.card_summary(card("HuggingFaceTB__SmolLM2-360M-Instruct"), config("HuggingFaceTB__SmolLM2-360M-Instruct"))
    assert s["base_model"] == "HuggingFaceTB/SmolLM2-360M" and s["license"] == "apache-2.0"
    assert s["context_length"] == 8192
    moe = mc.card_summary(card("Qwen__Qwen3-30B-A3B-Instruct-2507"), config("Qwen__Qwen3-30B-A3B-Instruct-2507"))
    assert moe["moe"] is True and moe["base_model"] is None
    assert (moe["params"], moe["active_params"], moe["context_length"]) == (30_532_122_624, MOE_ACTIVE, 262144)
