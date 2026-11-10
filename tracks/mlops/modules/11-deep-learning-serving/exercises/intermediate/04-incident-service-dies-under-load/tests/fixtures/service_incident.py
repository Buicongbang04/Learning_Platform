import asyncio
import io
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

INPUT_SIZE = 64
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
COLLECT_WINDOW_MS = 10
REQUEST_TIMEOUT_S = 2.0


def preprocess(image: Image.Image) -> np.ndarray:
    resized = image.convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    pixels = (np.asarray(resized, dtype=np.float32) / 255.0 - MEAN) / STD
    return np.ascontiguousarray(pixels.transpose(2, 0, 1)[None], dtype=np.float32)


def postprocess(logits: np.ndarray, size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(logits.argmax(axis=0).astype(np.uint8), mode="L").resize(size, Image.NEAREST).save(buffer, format="PNG")
    return buffer.getvalue()


def create_app(model_path: Path, device, model_version: str = "seg-tiny-1") -> FastAPI:
    state = {}

    async def worker() -> None:
        queue = state["queue"]
        while True:
            jobs = [await queue.get()]
            await asyncio.sleep(COLLECT_WINDOW_MS / 1000)
            while not queue.empty():
                jobs.append(queue.get_nowait())
            pixel_values = np.concatenate([x for x, _ in jobs])
            logits = await asyncio.to_thread(device.run, state["session"], pixel_values)
            for (_, future), output in zip(jobs, logits):
                if not future.done():
                    future.set_result(output)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state["session"] = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        state["queue"] = asyncio.Queue()
        task = asyncio.create_task(worker())
        yield
        task.cancel()

    app = FastAPI(lifespan=lifespan)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "model_version": model_version}

    @app.post("/segment")
    async def segment(file: UploadFile = File(...)):
        try:
            image = Image.open(io.BytesIO(await file.read()))
            image.load()
        except Exception:
            raise HTTPException(400, "không đọc được ảnh")
        future = asyncio.get_running_loop().create_future()
        await state["queue"].put((preprocess(image), future))
        try:
            logits = await asyncio.wait_for(future, REQUEST_TIMEOUT_S)
        except asyncio.TimeoutError:
            raise HTTPException(504, "hết thời gian chờ suy luận")
        return Response(postprocess(logits, image.size), media_type="image/png", headers={"X-Model-Version": model_version})

    return app
