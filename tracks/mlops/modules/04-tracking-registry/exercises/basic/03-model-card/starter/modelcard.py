REQUIRED_HEADINGS = [
    "## Mục đích sử dụng",
    "## Dữ liệu huấn luyện",
    "## Hiệu năng",
    "## Hạn chế và rủi ro",
    "## Lineage",
]


def worst_slices(slices: dict, overall_mae: float, k: int = 3, min_n: int = 100) -> list[tuple[str, float]]:
    """k slice tệ nhất so với MAE tổng, dạng [(tên, slice_mae / overall_mae)], tỉ lệ giảm dần.

    Bỏ slice có n < min_n. `slices` là {tên: {"mae": float, "n": int}}.
    """
    # TODO
    raise NotImplementedError


def build_model_card(info: dict) -> str:
    """Sinh model card Markdown từ `info`.

    info có: name, version, owner, intended_use (str), out_of_scope (list[str]),
    training_data {"data_version", "rows", "period"}, metrics {"mae", "latency_p95_ms"},
    slices {tên: {"mae", "n"}}, limitations (list[str]), lineage {"run_id", "git_commit"}.

    Dòng đầu: "# Model card: <name> v<version>". Sau đó đúng năm phần theo REQUIRED_HEADINGS, theo thứ tự.
    Phần Hiệu năng có bảng slice, tệ nhất đứng đầu, kèm cột tỉ lệ so với MAE tổng (vd. 1.50x).
    limitations rỗng thì raise ValueError: model card không có hạn chế là model card chưa viết xong.
    """
    # TODO
    raise NotImplementedError


def card_problems(text: str) -> list[str]:
    """Linter cho model card (chạy trong CI): trả danh sách lỗi, rỗng nghĩa là đạt.

    Lỗi khi: thiếu một heading trong REQUIRED_HEADINGS, còn chữ "TODO", phần Hạn chế và rủi ro không có
    gạch đầu dòng nào, phần Hiệu năng không có bảng Markdown, thiếu git_commit 40 ký tự hex ở phần Lineage.
    """
    # TODO
    raise NotImplementedError
