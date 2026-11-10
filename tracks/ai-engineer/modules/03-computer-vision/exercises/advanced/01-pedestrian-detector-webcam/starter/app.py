"""App phát hiện người đi bộ thời gian thực: webcam, tệp video hoặc thư mục ảnh → khung hình có hộp + FPS.

OpenCV bản headless (của env này) không mở được cửa sổ, nên app phát hình qua trình duyệt (MJPEG trên HTTP,
chỉ dùng thư viện chuẩn) và/hoặc ghi ra tệp video:

    uv run python app.py --weights best.pt --source 0 --port 8000         # webcam, mở http://localhost:8000
    uv run python app.py --weights best.pt --source vtest.avi --out out.mp4  # tệp video, không cần camera

`--source` là số (chỉ số camera) hoặc đường dẫn tệp video/thư mục ảnh.
"""

from __future__ import annotations

import argparse
import http.server
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import cv2
import numpy as np

# detect_fn(frame_bgr) -> (boxes xyxy (K, 4) float pixel, scores (K,), labels (K,) int)
DetectFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray, np.ndarray]]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}


def parse_source(source: str) -> int | str:
    """"0", "1"... → chỉ số camera (int); còn lại giữ nguyên là đường dẫn (str)."""
    # TODO
    raise NotImplementedError


def iter_frames(source: int | str) -> Iterator[np.ndarray]:
    """Sinh từng khung hình BGR uint8. Thư mục: đọc mọi ảnh theo tên tăng dần (cv2.imread); còn lại:
    cv2.VideoCapture(source) tới khi hết khung. Không mở được nguồn thì raise RuntimeError có lời nhắn rõ."""
    # TODO: nhớ release VideoCapture khi xong
    raise NotImplementedError


def draw_detections(frame: np.ndarray, boxes: np.ndarray, scores: np.ndarray, labels: np.ndarray,
                    names: dict[int, str], fps: float | None = None) -> np.ndarray:
    """Vẽ hộp (viền 2 px) và nhãn "<tên> <score:.2f>" lên frame (BGR uint8), thêm "FPS x.x" ở góc trên trái
    nếu có. Vẽ tại chỗ và trả lại chính frame. Hộp được làm tròn và kẹp vào trong ảnh."""
    # TODO: cv2.rectangle, cv2.putText
    raise NotImplementedError


class FpsMeter:
    """FPS trượt: trung bình mũ (EMA) của 1 / khoảng thời gian giữa hai lần tick, hệ số `alpha` cho giá trị mới.

    Lần tick đầu chỉ ghi mốc thời gian và trả 0.0; lần thứ hai trả đúng 1 / dt; từ lần ba:
    fps = alpha * (1 / dt) + (1 - alpha) * fps. `clock` là hàm trả thời gian (giây), để test tiêm đồng hồ giả.
    """

    def __init__(self, alpha: float = 0.1, clock: Callable[[], float] = time.perf_counter):
        # TODO
        raise NotImplementedError

    def tick(self) -> float:
        # TODO
        raise NotImplementedError


def run(source: int | str, detect_fn: DetectFn, names: dict[int, str], out_path: str | None = None,
        max_frames: int | None = None, on_frame: Callable[[np.ndarray], None] | None = None,
        clock: Callable[[], float] = time.perf_counter) -> dict:
    """Vòng chính: đọc khung → detect_fn → draw_detections (kèm FPS) → ghi tệp (nếu out_path) / on_frame (nếu có).

    Ghi video bằng cv2.VideoWriter (codec "mp4v", 25 fps, cỡ của khung đầu). Dừng khi hết nguồn hoặc đủ
    max_frames. Trả {"frames": số khung, "detections": tổng số hộp, "fps": FPS trung bình = frames / tổng thời gian}.
    """
    # TODO
    raise NotImplementedError


def make_detector(weights: str, conf: float = 0.25, imgsz: int = 640, device: str = "cpu") -> DetectFn:
    """detect_fn từ weights ultralytics (best.pt sau fine-tune, hoặc yolo11n.pt để so)."""
    # TODO: from ultralytics import YOLO (import trong hàm để test không phải nạp ultralytics)
    raise NotImplementedError


# ---------- phát MJPEG qua HTTP: đã viết sẵn, không cần sửa ----------

class _Latest:
    """Giữ JPEG mới nhất cho mọi client đang xem."""

    def __init__(self):
        self.jpeg: bytes | None = None
        self.cond = threading.Condition()

    def push(self, frame: np.ndarray) -> None:
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok:
            with self.cond:
                self.jpeg = buf.tobytes()
                self.cond.notify_all()


def serve_mjpeg(latest: _Latest, port: int) -> http.server.ThreadingHTTPServer:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    with latest.cond:
                        latest.cond.wait(timeout=5)
                        jpeg = latest.jpeg
                    if jpeg is None:
                        continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", required=True, help="best.pt sau fine-tune (hoặc yolo11n.pt để so)")
    ap.add_argument("--source", default="0", help="chỉ số camera, tệp video hoặc thư mục ảnh")
    ap.add_argument("--out", help="ghi video kết quả (.mp4)")
    ap.add_argument("--port", type=int, help="phát MJPEG ở http://localhost:<port>")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--max-frames", type=int)
    args = ap.parse_args()

    latest = _Latest() if args.port else None
    if latest:
        serve_mjpeg(latest, args.port)
        print(f"mở http://localhost:{args.port} trên trình duyệt (Ctrl+C để dừng)")
    stats = run(parse_source(args.source), make_detector(args.weights, args.conf, args.imgsz, args.device),
                {0: "person"}, args.out, args.max_frames, latest.push if latest else None)
    print(stats)


if __name__ == "__main__":
    main()
