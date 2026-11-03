"""Online learning với River so với model batch huấn luyện một lần, trên cùng một luồng."""


def make_online_model():
    raise NotImplementedError("TODO 1: model River học từng mẫu (learn_one/predict_one)")


def prequential(stream, model, start: int = 0) -> float:
    raise NotImplementedError("TODO 2: đánh giá test-then-train, chỉ tính độ chính xác từ vị trí start")


def frozen_batch(stream, train_n: int) -> float:
    raise NotImplementedError("TODO 3: huấn luyện một lần trên train_n mẫu đầu, chấm trên phần còn lại")


def compare(stream, train_n: int) -> dict:
    raise NotImplementedError("TODO 4: {'online': ..., 'batch': ...} trên cùng đoạn sau train_n")


def choose(result: dict, margin: float = 0.05) -> str:
    raise NotImplementedError("TODO 5: 'online' hay 'batch'")
