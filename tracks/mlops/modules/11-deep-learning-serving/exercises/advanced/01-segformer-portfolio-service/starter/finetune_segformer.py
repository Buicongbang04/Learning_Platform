"""Bước chuẩn bị của module 11: fine-tune segformer-b0 trên một tập con Oxford-IIIT Pets + trimap, chạy một lần.

Lớp: 0 nền, 1 thú cưng, 2 viền (trimap gốc: 2 nền, 1 thú cưng, 3 viền). Kết quả: thư mục model Hugging Face,
tệp ONNX (batch động, opset 17) và một run MLflow local chứa cả hai.

GPU (RTX 3050 4 GB, vài phút):
    uv run --project setup/gpu python <tệp này> --device cuda
CPU (lâu hơn, nên giảm --train và --size):
    uv run python <tệp này> --device cpu --train 300 --size 192
Export ONNX (nếu chưa có) và ghi vào MLflow, chạy trong môi trường chính (setup/gpu không có onnx, mlflow):
    uv run python <tệp này> --log-only
"""

import argparse
import io
import json
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch
from PIL import Image

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "pyproject.toml").exists() and (p / "data").is_dir())
PETS = ROOT / "data" / "raw" / "oxford-pets" / "data"
TRIMAPS = ROOT / "data" / "raw" / "oxford-pets-trimaps" / "annotations" / "trimaps"
OUT = ROOT / "data" / "raw_models" / "segformer-b0-pets"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
TRIMAP_TO_CLASS = np.array([0, 1, 0, 2], dtype=np.int64)
LABELS = {0: "background", 1: "pet", 2: "border"}
ONNX_NAME = "segformer-b0-pets.onnx"


def load_split(split: str, count: int, size: int, seed: int) -> tuple[torch.Tensor, torch.Tensor]:
    table = pq.read_table(PETS / f"{split}-00000-of-00001.parquet", columns=["image", "image_id"])
    ids = table.column("image_id").to_pylist()
    have = [i for i, image_id in enumerate(ids) if (TRIMAPS / f"{image_id}.png").is_file()]
    chosen = np.random.default_rng(seed).choice(have, size=min(count, len(have)), replace=False)
    images, masks = [], []
    for i in sorted(chosen):
        image = Image.open(io.BytesIO(table.column("image")[int(i)].as_py()["bytes"])).convert("RGB")
        trimap = np.asarray(Image.open(TRIMAPS / f"{ids[i]}.png").resize((size, size), Image.NEAREST))
        pixels = (np.asarray(image.resize((size, size), Image.BILINEAR), dtype=np.float32) / 255.0 - MEAN) / STD
        images.append(pixels.transpose(2, 0, 1))
        masks.append(TRIMAP_TO_CLASS[np.clip(trimap, 0, 3)])
    return torch.from_numpy(np.stack(images)), torch.from_numpy(np.stack(masks))


def per_class_iou(pred: np.ndarray, target: np.ndarray) -> dict[str, float]:
    scores = {}
    for c, name in LABELS.items():
        union = np.logical_or(pred == c, target == c).sum()
        scores[name] = float(np.logical_and(pred == c, target == c).sum() / union) if union else float("nan")
    return scores


@torch.no_grad()
def evaluate(model, images, masks, device, batch: int) -> dict[str, float]:
    model.eval()
    preds = []
    for start in range(0, len(images), batch):
        logits = model(pixel_values=images[start:start + batch].to(device)).logits
        logits = torch.nn.functional.interpolate(logits, size=masks.shape[-2:], mode="bilinear", align_corners=False)
        preds.append(logits.argmax(1).cpu().numpy())
    scores = per_class_iou(np.concatenate(preds), masks.numpy())
    scores["miou"] = float(np.nanmean(list(scores.values())))
    return scores


class LogitsOnly(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, pixel_values):
        return self.model(pixel_values=pixel_values).logits


def export_onnx(model, path: Path, size: int) -> None:
    wrapper = LogitsOnly(model.cpu().eval())
    torch.onnx.export(wrapper, (torch.zeros(2, 3, size, size),), str(path), opset_version=17,
                      input_names=["pixel_values"], output_names=["logits"],
                      dynamic_axes={"pixel_values": {0: "batch"}, "logits": {0: "batch"}}, dynamo=False)


def train(args) -> None:
    from transformers import SegformerForSemanticSegmentation

    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else
                          ("cpu" if args.device == "auto" else args.device))
    torch.manual_seed(args.seed)
    train_x, train_y = load_split("train", args.train, args.size, args.seed)
    val_x, val_y = load_split("test", args.val, args.size, args.seed)
    print(f"train {tuple(train_x.shape)}, val {tuple(val_x.shape)}, device {device}")
    model = SegformerForSemanticSegmentation.from_pretrained(
        args.checkpoint, num_labels=len(LABELS), id2label=LABELS, label2id={v: k for k, v in LABELS.items()},
        ignore_mismatched_sizes=True,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    history = []
    started = time.time()
    for epoch in range(args.epochs):
        model.train()
        order = torch.randperm(len(train_x))
        losses = []
        for start in range(0, len(order), args.batch):
            idx = order[start:start + args.batch]
            with torch.autocast(device.type, dtype=torch.float16, enabled=use_amp):
                loss = model(pixel_values=train_x[idx].to(device), labels=train_y[idx].to(device)).loss
            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            losses.append(loss.item())
        scores = evaluate(model, val_x, val_y, device, args.batch)
        history.append({"epoch": epoch, "loss": float(np.mean(losses)), **scores})
        print(json.dumps(history[-1]))
    if device.type == "cuda":
        print(f"bộ nhớ GPU đỉnh khi train: {torch.cuda.max_memory_allocated() / 2**20:.0f} MiB")
    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out / "hf")
    meta = {"checkpoint": args.checkpoint, "size": args.size, "train": len(train_x), "val": len(val_x),
            "epochs": args.epochs, "lr": args.lr, "seed": args.seed, "seconds": round(time.time() - started),
            "device": str(device), "labels": LABELS, "mean": MEAN.tolist(), "std": STD.tolist(), "history": history}
    (args.out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"đã lưu {args.out}")


def ensure_onnx(args) -> None:
    path = args.out / ONNX_NAME
    if path.is_file():
        return
    try:
        import onnx
    except ImportError:
        print("Môi trường này không có gói onnx; export ONNX bằng: uv run python <tệp này> --log-only")
        return
    from transformers import SegformerForSemanticSegmentation

    size = json.loads((args.out / "meta.json").read_text(encoding="utf-8"))["size"]
    export_onnx(SegformerForSemanticSegmentation.from_pretrained(args.out / "hf"), path, size)
    print(f"đã export {path}")


def log_to_mlflow(args) -> None:
    try:
        import mlflow
    except ImportError:
        print("Môi trường này không có mlflow. Ghi vào MLflow bằng: uv run python <tệp này> --log-only")
        return
    meta = json.loads((args.out / "meta.json").read_text(encoding="utf-8"))
    mlflow.set_tracking_uri(args.tracking_uri)
    if mlflow.get_experiment_by_name("segformer-pets") is None:
        mlflow.create_experiment("segformer-pets", artifact_location=(args.out.parent / "mlartifacts").resolve().as_uri())
    mlflow.set_experiment("segformer-pets")
    with mlflow.start_run(run_name=f"segformer-b0-{meta['size']}px") as run:
        mlflow.log_params({k: meta[k] for k in ("checkpoint", "size", "train", "val", "epochs", "lr", "seed", "device")})
        for row in meta["history"]:
            mlflow.log_metrics({k: v for k, v in row.items() if k != "epoch" and v == v}, step=row["epoch"])
        mlflow.log_artifacts(str(args.out), artifact_path="model")
        print(f"MLflow run {run.info.run_id} ở {args.tracking_uri}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", default="nvidia/mit-b0")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--train", type=int, default=800)
    parser.add_argument("--val", type=int, default=200)
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--lr", type=float, default=6e-5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--tracking-uri", default=f"sqlite:///{OUT.parent / 'mlflow.db'}")
    parser.add_argument("--log-only", action="store_true")
    args = parser.parse_args()
    if not args.log_only:
        train(args)
    ensure_onnx(args)
    log_to_mlflow(args)


if __name__ == "__main__":
    main()
