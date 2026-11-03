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
    resized = image.convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    pixels = np.asarray(resized, dtype=np.float32) / 255.0
    pixels = (pixels - MEAN) / STD
    return np.ascontiguousarray(pixels.transpose(2, 0, 1)[None], dtype=np.float32)


def postprocess(logits: np.ndarray, size: tuple[int, int]) -> bytes:
    mask = logits[0].argmax(axis=0).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(mask, mode="L").resize(size, Image.NEAREST).save(buffer, format="PNG")
    return buffer.getvalue()


def create_app(model_path: Path, model_version: str) -> FastAPI:
    state = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state["session"] = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        yield
        state.clear()

    app = FastAPI(lifespan=lifespan)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "model_version": model_version}

    @app.post("/segment")
    async def segment(file: UploadFile = File(...)):
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, f"ảnh lớn hơn {MAX_BYTES} byte")
        try:
            image = Image.open(io.BytesIO(data))
        except Exception:
            raise HTTPException(400, "không đọc được ảnh")
        width, height = image.size
        if min(width, height) < MIN_SIDE or max(width, height) > MAX_SIDE:
            raise HTTPException(422, f"kích thước {width}x{height} ngoài khoảng [{MIN_SIDE}, {MAX_SIDE}] px")
        try:
            image.load()
        except Exception:
            raise HTTPException(400, "ảnh hỏng")
        batch = preprocess(image)
        logits = await run_in_threadpool(state["session"].run, None, {INPUT_NAME: batch})
        png = postprocess(logits[0], (width, height))
        return Response(png, media_type="image/png", headers={"X-Model-Version": model_version})

    return app
