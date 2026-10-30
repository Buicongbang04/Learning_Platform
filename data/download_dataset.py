"""Tải các bộ dữ liệu thật dùng trong track AI & Data Scientist và track Data Engineer.

Mỗi bộ ghi vào data/raw/<tên>/ (không commit). Test của bài tập tự skip khi bộ chưa được tải.

Bộ trên Kaggle cần token: KAGGLE_API_TOKEN=KGAT_... trong setup/.env (cách lấy token xem đầu tệp
data/download_olist.py). Bộ tải từ URL công khai không cần token.

Chạy:
    uv run python data/download_dataset.py --list            # liệt kê các bộ
    uv run python data/download_dataset.py cookie-cats       # ghi vào data/raw/cookie-cats/
    uv run python data/download_dataset.py hillstrom --out /tmp/hillstrom

Bộ Olist thật dùng script riêng (ghi thẳng vào data/raw/): uv run python data/download_olist.py
"""

from __future__ import annotations

import argparse
import io
import os
import random
import shutil
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

import requests
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_olist import ENV_FILE, _from_env_file, ensure_kaggle_credentials, kaggle_download  # noqa: E402

RAW = Path(__file__).resolve().parent / "raw"


@dataclass(frozen=True)
class Dataset:
    source: Literal["kaggle", "url", "hf"]
    ref: str | tuple[str, ...]  # "owner/slug" trên Kaggle hay Hugging Face (repo dataset), URL (xem download()), hoặc tuple nhiều URL
    files: list[str]    # tệp cần giữ (URL một tệp: tên lưu xuống; URL thư mục "/" hay .zip: tên tệp bên trong;
                        # tuple URL: tên lưu xuống, cùng độ dài với ref)
    license: str
    homepage: str
    about: str = ""
    needs_token: bool = False  # chỉ dùng cho source="hf": bắt buộc có HF_TOKEN
    revision: str | None = None  # chỉ dùng cho source="hf": nhánh/tag, vd "refs/convert/parquet"
    extract: bool = False  # chỉ dùng cho source="url" kiểu tuple: giải nén .zip/.tar.gz/.tgz giữ cấu trúc thư mục rồi xoá tệp nén


DATASETS: dict[str, Dataset] = {
    "cookie-cats": Dataset(
        "kaggle", "yufengsui/mobile-games-ab-testing", ["cookie_cats.csv"],
        license="Không ghi rõ trên Kaggle (dữ liệu công khai của Tactile Games qua DataCamp)",
        homepage="https://www.kaggle.com/datasets/yufengsui/mobile-games-ab-testing",
        about="A/B test vị trí gate (level 30 vs 40) của game Cookie Cats, ~90k người chơi",
    ),
    "ab-data": Dataset(
        "kaggle", "zhangluyuan/ab-testing", ["ab_data.csv"],
        license="Không ghi rõ trên Kaggle (dữ liệu khoá Udacity A/B Testing)",
        homepage="https://www.kaggle.com/datasets/zhangluyuan/ab-testing",
        about="A/B test landing page, ~290k phiên, có cả dòng gán nhóm sai",
    ),
    "hillstrom": Dataset(
        "url",
        "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv",
        ["hillstrom.csv"],
        license="Kevin Hillstrom công bố cho MineThatData E-Mail Analytics Challenge (2008), dùng tự do cho học tập",
        homepage="https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html",
        about="Thí nghiệm email ngẫu nhiên 3 nhánh, 64k khách: visit, conversion, spend",
    ),
    "nyc-tlc": Dataset(
        "url",
        tuple(f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2019-{m:02d}.parquet" for m in range(1, 13))
        + ("https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv",),
        [f"yellow_tripdata_2019-{m:02d}.parquet" for m in range(1, 13)] + ["taxi_zone_lookup.csv"],
        license="Dữ liệu mở của NYC Taxi & Limousine Commission (NYC Open Data), dùng tự do",
        homepage="https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
        about="Chuyến Yellow Taxi NYC, ghim 12 tháng 2019-01..2019-12 (Parquet, ~1,2 GB, ~84 triệu chuyến) + taxi_zone_lookup.csv",
    ),
    "nasa-http-logs": Dataset(
        "url", "https://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz", ["NASA_access_log_Jul95.gz"],
        license="Công bố tự do bởi NASA Kennedy Space Center (Internet Traffic Archive), dùng cho mọi mục đích",
        homepage="https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html",
        about="Access log HTTP của NASA KSC tháng 7/1995 (gz ~20 MB, ~1,9 triệu request, định dạng Common Log)",
    ),
    "air-quality-uci": Dataset(
        "url", ("https://archive.ics.uci.edu/static/public/360/air+quality.zip",), ["air-quality.zip"],
        license="CC BY 4.0 (UCI Machine Learning Repository)",
        homepage="https://archive.ics.uci.edu/dataset/360/air+quality",
        about="Đọc cảm biến khí thật (id 360), 9 357 dòng theo giờ, Ý 03/2004-04/2005, chứa -200 là giá trị thiếu",
    ),
    "lalonde": Dataset(
        "url", "https://users.nber.org/~rdehejia/data/", ["nsw_dw.dta", "psid_controls.dta"],
        license="Dữ liệu NSW của LaLonde (1986), bản Dehejia-Wahba (1999) do Rajeev Dehejia công bố công khai để nghiên cứu và giảng dạy",
        homepage="https://users.nber.org/~rdehejia/nswdata2.html",
        about="NSW: mẫu thí nghiệm Dehejia-Wahba (445 dòng, treat 185/260) + mẫu đối chứng quan sát PSID (2 490 dòng); re78 là thu nhập kết quả",
    ),
    "prop99": Dataset(
        "url",
        "https://raw.githubusercontent.com/OscarEngelbrektson/SyntheticControlMethods/master/examples/datasets/smoking_data.csv",
        ["smoking_data.csv"],
        license="Dữ liệu của Abadie, Diamond, Hainmueller (2010) (Proposition 99, California); bản CSV trong repo SyntheticControlMethods (MIT)",
        homepage="https://github.com/OscarEngelbrektson/SyntheticControlMethods",
        about="Panel 39 bang Mỹ x 1970-2000: cigsale (bao/người), retprice, lnincome, beer, age15to24; California là bang can thiệp (1988)",
    ),
    "card": Dataset(
        "url", "https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/wooldridge/card.csv",
        ["card.csv"],
        license="Dữ liệu NLS Young Men của Card (1995), công bố công khai trên trang David Card; bản CSV qua Rdatasets (gói wooldridge)",
        homepage="https://vincentarelbundock.github.io/Rdatasets/doc/wooldridge/card.html",
        about="3 010 nam giới (NLSYM 1976): lwage, educ, nearc4 (gần đại học 4 năm: IV), exper, black, smsa, ...",
    ),
    "store-sales": Dataset(
        "kaggle", "pratyushakar/rossmann-store-sales", ["train.csv", "store.csv"],
        license="Không ghi rõ trên Kaggle (dữ liệu Rossmann từ cuộc thi Kaggle 2015, bản dataset không cần chấp nhận luật)",
        homepage="https://www.kaggle.com/datasets/pratyushakar/rossmann-store-sales",
        about="Doanh số ngày của 1 115 cửa hàng Rossmann (2013-2015), 1 017 209 dòng: mùa vụ tuần/năm, khuyến mãi, ngày lễ",
    ),
    "telco-churn": Dataset(
        "kaggle", "blastchar/telco-customer-churn", ["WA_Fn-UseC_-Telco-Customer-Churn.csv"],
        license="Không ghi rõ trên Kaggle (dữ liệu mẫu của IBM)",
        homepage="https://www.kaggle.com/datasets/blastchar/telco-customer-churn",
        about="7 043 khách hàng viễn thông, 21 cột, nhãn Churn (~26,5% rời bỏ)",
    ),
    "movielens": Dataset(
        "url", "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
        ["ratings.csv", "movies.csv", "tags.csv", "links.csv"],
        license="GroupLens: dùng cho nghiên cứu/học tập, không phân phối lại, ghi nguồn Harper & Konstan (2015)",
        homepage="https://grouplens.org/datasets/movielens/latest/",
        about="MovieLens ml-latest-small: 100 836 rating của 610 người dùng cho 9 742 phim",
    ),
    "creditcard-fraud": Dataset(
        "kaggle", "mlg-ulb/creditcardfraud", ["creditcard.csv"],
        license="Open Database License (DbCL v1.0), ULB Machine Learning Group",
        homepage="https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
        about="284 807 giao dịch thẻ (2 ngày, châu Âu 2013), 492 gian lận (0,17%); V1-V28 là PCA, Time, Amount, Class",
    ),
    "mnist": Dataset(
        "url", "https://ossci-datasets.s3.amazonaws.com/mnist/",
        ["train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz", "t10k-images-idx3-ubyte.gz", "t10k-labels-idx1-ubyte.gz"],
        license="CC BY-SA 3.0 (Yann LeCun & Corinna Cortes); bản mirror S3 mà torchvision dùng",
        homepage="https://yann.lecun.com/exdb/mnist/",
        about="Chữ số viết tay 28x28: 60 000 ảnh train + 10 000 ảnh test (định dạng idx, gz)",
    ),
    "zalo-legal": Dataset(
        "hf", "GreenNode/zalo-ai-legal-text-retrieval-vn",
        ["corpus.jsonl", "queries.jsonl", "qrels/train.jsonl", "qrels/test.jsonl"],
        license="MIT (theo thẻ Hugging Face); bản mirror bên thứ ba của dữ liệu Zalo AI Challenge 2021 (Legal Text Retrieval), dùng học tập/nghiên cứu",
        homepage="https://huggingface.co/datasets/GreenNode/zalo-ai-legal-text-retrieval-vn",
        about="Truy hồi văn bản pháp luật Việt Nam: corpus các điều luật, câu hỏi và qrels (điều luật liên quan)",
        needs_token=False,
    ),
    # --- AI Engineer giai đoạn 3: ảnh, văn bản tiếng Việt, tiếng nói, toán, an toàn ---
    "cifar10": Dataset(
        "hf", "uoft-cs/cifar10", ["plain_text/train-00000-of-00001.parquet", "plain_text/test-00000-of-00001.parquet"],
        license="Thẻ Hugging Face ghi unknown; Krizhevsky (2009) công bố cho nghiên cứu/học tập, ghi nguồn bài báo. Bản mirror HF vì www.cs.toronto.edu tải rất chậm/treo",
        homepage="https://huggingface.co/datasets/uoft-cs/cifar10",
        about="CIFAR-10: 50 000 ảnh train + 10 000 ảnh test, 32x32x3, 10 lớp; parquet với cột img ({bytes: PNG}) và label",
    ),
    "oxford-pets": Dataset(
        "hf", "timm/oxford-iiit-pet", ["data/train-00000-of-00001.parquet", "data/test-00000-of-00001.parquet"],
        license="CC BY-SA 4.0 (Parkhi, Vedaldi, Zisserman, Jawahar 2012, VGG Oxford); bản mirror HF của timm vì thor.robots.ox.ac.uk tải rất chậm (~1 MB/phút)",
        homepage="https://huggingface.co/datasets/timm/oxford-iiit-pet",
        about="Oxford-IIIT Pet: ảnh chó/mèo 37 giống (parquet: image {bytes}, label, image_id...), dùng cho transfer learning; không có trimap",
    ),
    "penn-fudan": Dataset(
        "url", ("https://www.cis.upenn.edu/~jshi/ped_html/PennFudanPed.zip",), ["PennFudanPed.zip"],
        license="Công bố công khai bởi Jianbo Shi (UPenn) cho nghiên cứu; không ghi giấy phép chính thức",
        homepage="https://www.cis.upenn.edu/~jshi/ped_html/",
        about="Penn-Fudan Pedestrian: 170 ảnh, 345 người đi bộ, kèm mask từng người (PennFudanPed/PNGImages, PedMasks, Annotation)",
        extract=True,
    ),
    "uit-vsfc": Dataset(
        "hf", "uitnlp/vietnamese_students_feedback",
        ["default/train/0000.parquet", "default/validation/0000.parquet", "default/test/0000.parquet"],
        license="Thẻ Hugging Face ghi unknown; UIT-NLP công bố cho nghiên cứu/học tập (Nguyen et al., KSE 2018). Không dùng thương mại",
        homepage="https://huggingface.co/datasets/uitnlp/vietnamese_students_feedback",
        about="UIT-VSFC: phản hồi sinh viên tiếng Việt, cột sentence/sentiment (0 negative, 1 neutral, 2 positive)/topic; bản parquet do Hugging Face tự chuyển từ script gốc",
        revision="refs/convert/parquet",
    ),
    "iwslt15-en-vi": Dataset(
        "url",
        tuple(f"https://raw.githubusercontent.com/stefan-it/nmt-en-vi/master/data/{n}-en-vi.tgz" for n in ("train", "dev-2012", "test-2013")),
        ["train-en-vi.tgz", "dev-2012-en-vi.tgz", "test-2013-en-vi.tgz"],
        license="Dữ liệu IWSLT 2015 en-vi (Stanford NLP công bố cho nghiên cứu/học tập); bản mirror GitHub stefan-it/nmt-en-vi vì nlp.stanford.edu không truy cập được từ máy này",
        homepage="https://nlp.stanford.edu/projects/nmt/",
        about="IWSLT'15 en-vi: 133 317 cặp câu train (TED), dev tst2012 1 553 cặp, test tst2013 1 268 cặp (train.en/.vi, tst2012.*, tst2013.*)",
        extract=True,
    ),
    "wikipedia-vi": Dataset(
        "hf", "wikimedia/wikipedia",
        ["20231101.vi/train-00001-of-00004.parquet", "20231101.vi/train-00002-of-00004.parquet"],
        license="CC BY-SA 3.0 và GFDL (Wikipedia, Wikimedia Foundation)",
        homepage="https://huggingface.co/datasets/wikimedia/wikipedia",
        about="Wikipedia tiếng Việt bản 20231101, chỉ 2 trong 4 shard (~120 MB) để vừa laptop; cột id/url/title/text",
    ),
    "openorca-viet": Dataset(
        "hf", "vilm/OpenOrca-Viet", ["OpenOrca-Viet.jsonl"],
        license="Apache-2.0 (thẻ Hugging Face); dữ liệu sinh bởi GPT-4/PaLM-2/Claude từ vi-FLAN, tuân điều khoản các nhà cung cấp model khi dùng thương mại",
        homepage="https://huggingface.co/datasets/vilm/OpenOrca-Viet",
        about="Instruction tiếng Việt kiểu Orca: JSONL với instruction (system prompt), input, output; ~290 MB",
    ),
    "gsm8k": Dataset(
        "hf", "openai/gsm8k", ["main/train-00000-of-00001.parquet", "main/test-00000-of-00001.parquet"],
        license="MIT (OpenAI, Cobbe et al. 2021)",
        homepage="https://huggingface.co/datasets/openai/gsm8k",
        about="GSM8K: 7 473 bài toán chữ cấp tiểu học train + 1 319 test, cột question/answer (đáp số sau '####')",
    ),
    "prompt-injections": Dataset(
        "hf", "deepset/prompt-injections",
        ["data/train-00000-of-00001-9564e8b05b4757ab.parquet", "data/test-00000-of-00001-701d16158af87368.parquet"],
        license="Apache-2.0 (deepset)",
        homepage="https://huggingface.co/datasets/deepset/prompt-injections",
        about="Prompt injection: 546 train + 116 test, cột text/label (1 = injection), pha trộn tiếng Anh và tiếng Đức",
    ),
    "fleurs-vi": Dataset(
        "hf", "google/fleurs", ["data/vi_vn/test.tsv", "data/vi_vn/audio/test.tar.gz"],
        license="CC BY 4.0 (Google, Conneau et al. 2022)",
        homepage="https://huggingface.co/datasets/google/fleurs",
        about="FLEURS tiếng Việt, tập test: tệp tsv (id, tên wav, transcription...) + audio/test.tar.gz các wav 16 kHz; ~545 MB",
    ),
}


def _no_token() -> SystemExit:
    return SystemExit(
        "Chưa có Kaggle token. Thêm KAGGLE_API_TOKEN=KGAT_... vào setup/.env "
        "(hướng dẫn ở đầu tệp data/download_olist.py)."
    )


def _no_hf_token() -> SystemExit:
    return SystemExit(
        "Bộ này cần Hugging Face token. Tạo token loại Read tại https://huggingface.co/settings/tokens "
        "rồi thêm HF_TOKEN=hf_... vào setup/.env."
    )


def _get(url: str) -> bytes:
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    return resp.content


def _extract(archive: Path, out: Path) -> None:
    """Giải nén .zip hoặc .tar.gz/.tgz vào out, giữ cấu trúc thư mục; chặn đường dẫn thoát khỏi out."""
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            for member in zf.namelist():
                if not (out / member).resolve().is_relative_to(out.resolve()):
                    raise SystemExit(f"{archive.name}: đường dẫn nguy hiểm {member!r}")
            zf.extractall(out)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(out, filter="data")


def download(name: str, out: Path) -> list[Path]:
    """Ba kiểu URL: một tệp (lưu thành files[0]); thư mục kết thúc bằng "/" (tải từng tên trong files);
    tệp .zip (giải nén, giữ các tệp có tên trong files, bất kể thư mục con)."""
    ds = DATASETS[name]
    if ds.source == "url" and isinstance(ds.ref, tuple):
        out.mkdir(parents=True, exist_ok=True)
        paths = []
        for url, fname in zip(ds.ref, ds.files, strict=True):
            target = out / fname
            with requests.get(url, stream=True, timeout=300) as resp:
                resp.raise_for_status()
                with target.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            print(fname, flush=True)
            paths.append(target)
        if ds.extract:
            for target in paths:
                _extract(target, out)
                target.unlink()
            return [p for p in out.rglob("*") if p.is_file()]
        return paths

    if ds.source == "url":
        out.mkdir(parents=True, exist_ok=True)
        if ds.ref.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(_get(ds.ref))) as zf:
                members: dict[str, str] = {}
                for n in zf.namelist():  # bỏ thư mục, __MACOSX và "._*"; trùng tên thì lấy đường dẫn nông nhất
                    parts = PurePosixPath(n).parts
                    if n.endswith("/") or "__MACOSX" in parts or parts[-1].startswith("._"):
                        continue
                    base = parts[-1]
                    if base not in members or len(parts) < len(PurePosixPath(members[base]).parts):
                        members[base] = n
                missing = [f for f in ds.files if f not in members]
                if missing:
                    raise SystemExit(f"{ds.ref} thiếu {missing}. Có: {sorted(members)}")
                written = []
                for f in ds.files:
                    target = out / f
                    target.write_bytes(zf.read(members[f]))
                    written.append(target)
                return written
        if ds.ref.endswith("/"):
            written = []
            for f in ds.files:
                target = out / f
                target.write_bytes(_get(ds.ref + f))
                written.append(target)
            return written
        target = out / ds.files[0]
        target.write_bytes(_get(ds.ref))
        return [target]

    if ds.source == "hf":
        token = os.environ.get("HF_TOKEN") or _from_env_file(ENV_FILE, "HF_TOKEN")
        if ds.needs_token and not token:
            raise _no_hf_token()
        out.mkdir(parents=True, exist_ok=True)
        written = []
        for f in ds.files:
            cached = hf_hub_download(repo_id=ds.ref, filename=f, repo_type="dataset", token=token, revision=ds.revision)
            target = out / f  # giữ đường dẫn con (qrels/train.jsonl và qrels/test.jsonl khác tên nhưng cùng cấp)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached, target)
            written.append(target)
        return written

    if not ensure_kaggle_credentials(env_file=ENV_FILE):
        raise _no_token()
    return kaggle_download(ds.ref, out, ds.files)


def ensure(name: str) -> Path:
    """Trả data/raw/<name>/; chưa có tệp thì tải vào thư mục tạm rồi đổi tên (atomic)."""
    final = RAW / name
    if final.is_dir() and any(final.iterdir()):
        return final
    RAW.mkdir(parents=True, exist_ok=True)
    for stale in RAW.glob(f".{name}.partial-*"):  # dọn thư mục tạm của lần tải bị kill
        shutil.rmtree(stale, ignore_errors=True)
    tmp = RAW / f".{name}.partial-{random.randrange(16**8):08x}"
    try:
        download(name, tmp)
        if final.is_dir():  # thư mục rỗng còn sót
            final.rmdir()
        tmp.rename(final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return final


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Tải bộ dữ liệu thật cho track AI & Data Scientist và track Data Engineer.")
    parser.add_argument("name", nargs="?", choices=sorted(DATASETS))
    parser.add_argument("--out", type=Path, help="mặc định data/raw/<tên>/")
    parser.add_argument("--list", action="store_true", help="liệt kê các bộ")
    args = parser.parse_args(argv)

    if args.list or not args.name:
        for key, ds in DATASETS.items():
            print(f"{key:12} {ds.about}\n{'':12} {ds.homepage}")
        return
    if args.out:
        for path in download(args.name, args.out):
            print(f"  {path}")
    else:
        print(f"  {ensure(args.name)}")


if __name__ == "__main__":
    main()
