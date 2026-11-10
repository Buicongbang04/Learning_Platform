import io

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from PIL import Image

from testkit import Exercise

ex = Exercise(__file__)


def write_trimap(path, values):
    Image.fromarray(np.asarray(values, dtype=np.uint8)).save(path)


def trimap_dir(tmp_path):
    folder = tmp_path / "trimaps"
    folder.mkdir()
    write_trimap(folder / "cat_1.png", [[1, 1, 2, 2], [1, 3, 2, 2]])
    write_trimap(folder / "dog_2.png", [[2, 2, 2], [2, 2, 2]])
    (folder / "._cat_1.png").write_bytes(b"\x00\x05\x16\x07AppleDouble junk")
    (folder / "notes.txt").write_text("x")
    return folder


def image_bytes(width, height, mode="RGB", fmt="JPEG"):
    buffer = io.BytesIO()
    Image.new(mode, (width, height)).save(buffer, format=fmt)
    return buffer.getvalue()


def pets_dir(tmp_path):
    data = tmp_path / "pets" / "data"
    data.mkdir(parents=True)
    rows = {
        "train": [("cat_1", 4, 2, "RGB", "JPEG"), ("bird_9", 1200, 700, "RGB", "JPEG")],
        "test": [("dog_2", 2, 3, "RGBA", "PNG")],
    }
    for split, items in rows.items():
        table = pa.table({
            "image": [{"bytes": image_bytes(w, h, mode, fmt), "path": None} for _, w, h, mode, fmt in items],
            "label": [0] * len(items),
            "image_id": [i for i, *_ in items],
        })
        pq.write_table(table, data / f"{split}-00000-of-00001.parquet")
    return tmp_path / "pets"


def test_list_trimaps_skips_appledouble(tmp_path):
    nb = ex.notebook("pets_profile.ipynb")
    names = [p.name for p in nb.list_trimaps(trimap_dir(tmp_path))]
    assert names == ["cat_1.png", "dog_2.png"]


def test_trimap_profile_shares(tmp_path):
    nb = ex.notebook("pets_profile.ipynb")
    df = nb.trimap_profile(nb.list_trimaps(trimap_dir(tmp_path)))
    assert list(df.columns) == ["image_id", "height", "width", "pet", "background", "border"]
    cat = df.set_index("image_id").loc["cat_1"]
    assert (cat["height"], cat["width"]) == (2, 4)
    assert cat[["pet", "background", "border"]].tolist() == pytest.approx([3 / 8, 4 / 8, 1 / 8])
    assert df.set_index("image_id").loc["dog_2", "pet"] == 0


def test_image_table_reads_sizes_split_and_mode(tmp_path):
    nb = ex.notebook("pets_profile.ipynb")
    df = nb.image_table(pets_dir(tmp_path))
    assert list(df.columns) == ["image_id", "split", "height", "width", "mode"]
    rows = {r.image_id: (r.split, r.height, r.width, r.mode) for r in df.itertuples()}
    assert rows == {"cat_1": ("train", 2, 4, "RGB"), "bird_9": ("train", 700, 1200, "RGB"), "dog_2": ("test", 3, 2, "RGBA")}


def test_join_report_share_over_and_without_pet(tmp_path):
    nb = ex.notebook("pets_profile.ipynb")
    trimaps = nb.trimap_profile(nb.list_trimaps(trimap_dir(tmp_path)))
    trimaps = pd.concat([trimaps, pd.DataFrame([{"image_id": "ghost_3", "height": 5, "width": 5, "pet": 0.2,
                                                 "background": 0.8, "border": 0.0}])], ignore_index=True)
    images = nb.image_table(pets_dir(tmp_path))
    assert nb.join_report(trimaps, images) == {"matched": 2, "trimap_only": 1, "image_only": 1, "size_mismatch": 1}
    assert nb.share_over(images, 1000) == pytest.approx(1 / 3)
    assert nb.share_over(images, 1200) == 0
    assert nb.without_pet(trimaps) == ["dog_2"]


def test_real_pets_and_trimaps():
    nb = ex.notebook("pets_profile.ipynb")
    trimap_root = ex.dataset("oxford-pets-trimaps") / "annotations" / "trimaps"
    paths = nb.list_trimaps(trimap_root)
    assert len(paths) == 7390
    trimaps = nb.trimap_profile(paths)
    images = nb.image_table(ex.dataset("oxford-pets"))
    assert len(images) == 7349
    assert nb.join_report(trimaps, images) == {"matched": 7349, "trimap_only": 41, "image_only": 0, "size_mismatch": 0}
    assert trimaps["pet"].mean() == pytest.approx(0.2997, abs=5e-4)
    assert trimaps["border"].mean() == pytest.approx(0.1184, abs=5e-4)
    assert nb.share_over(images, 500) == pytest.approx(0.0186, abs=5e-4)
    assert nb.share_over(images, 1024) == pytest.approx(0.0029, abs=2e-4)
    assert len(nb.without_pet(trimaps)) == 23
    assert int((images["mode"] != "RGB").sum()) == 3
