import io
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from PIL import Image

INPUT_NAME = "pixel_values"
INPUT_SIZE = 64
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
MIN_SIDE = 32
MAX_SIDE = 1024
MAX_BYTES = 10 * 1024 * 1024


def preprocess(image: Image.Image) -> np.ndarray:
    # TODO: RGB, resize INPUT_SIZE x INPUT_SIZE bilinear, /255, chuẩn hoá MEAN/STD, NCHW float32 (1, 3, S, S)
    raise NotImplementedError


def postprocess(logits: np.ndarray, size: tuple[int, int]) -> bytes:
    # TODO: argmax theo lớp, uint8, phóng về size (width, height) bằng nearest, trả PNG mode L
    raise NotImplementedError


def create_app(model_path: Path, model_version: str) -> FastAPI:
    # TODO: nạp session một lần lúc khởi động; GET /healthz; POST /segment nhận file ảnh, kiểm tra, trả mask PNG
    raise NotImplementedError
