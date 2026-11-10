"""Hội thoại 6 phiên tự tạo giữa người dùng Minh và trợ lý: 24 lượt có thông tin, phần còn lại là chuyện phiếm.

QUESTIONS: (câu hỏi, từ khoá đáp án (khớp một trong các từ là đúng), fact_id chứa bằng chứng (vị trí trong FACT_TURNS), nhóm).
"""

import random

FACT_TURNS = [
    (0, "Chào bạn, mình tên là Minh, năm nay 29 tuổi.", "Chào Minh! Rất vui được nói chuyện với bạn."),
    (0, "Mình đang làm kỹ sư dữ liệu ở một công ty logistics tại Hà Nội.", "Nghe thú vị đấy, chắc bạn làm nhiều với pipeline."),
    (0, "Mình bị dị ứng hải sản, nhất là tôm.", "Mình sẽ nhớ để không gợi ý món có tôm."),
    (0, "Con chó nhà mình tên là Mực, giống Phú Quốc.", "Mực nghe dễ thương quá!"),
    (1, "Sinh nhật mình là ngày 14 tháng 3.", "Mình ghi nhận rồi, 14/3."),
    (1, "Mình thích đọc sách lịch sử, gần đây đang đọc về nhà Trần.", "Nhà Trần có nhiều chuyện hay lắm."),
    (1, "Em gái mình tên Thảo, đang học năm ba ở Huế.", "Chúc Thảo học tốt nhé."),
    (1, "Mình uống cà phê đen không đường, mỗi sáng một ly.", "Cà phê đen không đường, chuẩn dân kỹ thuật."),
    (2, "Mình đang chuẩn bị chạy bán marathon vào tháng 12.", "Cố lên! 21 km là thử thách lớn."),
    (2, "Dự án hiện tại của mình là chuyển hệ thống báo cáo sang Airflow, hạn chót cuối tháng 11.", "Hạn khá gấp, chúc bạn kịp tiến độ."),
    (2, "Mình đi làm bằng xe máy, khoảng 25 phút mỗi chiều.", "Hà Nội giờ cao điểm chắc mệt lắm."),
    (2, "Mình đang học tiếng Nhật, trình độ N4.", "Tiếng Nhật khó nhưng đáng học."),
    (3, "Mình vừa chuyển nhà vào Đà Nẵng tuần trước, công ty cho làm từ xa.", "Đà Nẵng đẹp lắm, chúc bạn ổn định nhanh."),
    (3, "Bạn gái mình tên Linh, làm giáo viên tiếng Anh.", "Chào Linh qua bạn nhé."),
    (3, "Mình không ăn cay được, ăn cay là đau dạ dày.", "Mình sẽ tránh gợi ý món cay."),
    (3, "Mình thích nghe nhạc Trịnh Công Sơn khi làm việc.", "Nhạc Trịnh rất hợp để tập trung."),
    (4, "Mình vừa đổi việc, giờ làm kỹ sư machine learning cho một startup y tế.", "Chúc mừng công việc mới!"),
    (4, "Mực vừa được 3 tuổi hôm qua.", "Chúc mừng sinh nhật Mực!"),
    (4, "Mình đã bỏ cà phê, chuyển sang uống trà xanh vì mất ngủ.", "Trà xanh nhẹ nhàng hơn, tốt cho giấc ngủ."),
    (4, "Mình đang tiết kiệm để mua một chiếc ô tô điện vào năm sau.", "Mục tiêu hay đấy."),
    (5, "Mình đã đăng ký giải bán marathon Đà Nẵng ngày 8 tháng 12.", "Tuyệt, có ngày cụ thể rồi."),
    (5, "Laptop của mình là ThinkPad X1, RAM 32GB.", "Máy tốt cho công việc ML."),
    (5, "Mình dự định đi Nhật du lịch vào tháng 4 năm sau với Linh.", "Mùa hoa anh đào, hợp lý quá."),
    (5, "Món mình thích nhất là bún chả.", "Bún chả Hà Nội thì tuyệt."),
]

FILLER_USER = [
    "Hôm nay trời {w} quá nhỉ.", "Bạn gợi ý giúp mình một bộ phim {g} xem cuối tuần?", "Giải thích giúp mình {c} là gì?",
    "Viết giúp mình một câu chúc {o} ngắn.", "Mình đang hơi buồn ngủ.", "Cho mình một mẹo để tập trung hơn.",
    "Tính giúp 15% của 240 nghìn.", "Từ '{wd}' tiếng Anh là gì?", "Kể một câu chuyện cười ngắn đi.",
    "Có cách nào để ngủ ngon hơn không?", "Bạn biết gì về {c}?", "Gợi ý một món ăn sáng nhanh.",
]
FILL = {"w": ["nóng", "mưa", "đẹp", "âm u", "lạnh"], "g": ["hành động", "hài", "tài liệu", "hoạt hình"],
        "c": ["Kafka", "vector database", "gradient descent", "Docker", "REST API", "transformer"],
        "o": ["năm mới", "sinh nhật đồng nghiệp", "khai trương", "tốt nghiệp"], "wd": ["kiên nhẫn", "tò mò", "bền bỉ", "biết ơn"]}
FILLER_ASSISTANT = "Đây là câu trả lời ngắn cho yêu cầu của bạn."

QUESTIONS = [
    ("Mình tên là gì?", ["minh"], [0], "cu"),
    ("Mình bị dị ứng với gì?", ["hải sản", "tôm"], [2], "cu"),
    ("Con chó của mình tên gì?", ["mực"], [3], "cu"),
    ("Sinh nhật mình ngày nào?", ["14"], [4], "cu"),
    ("Em gái mình đang học ở thành phố nào?", ["huế"], [6], "cu"),
    ("Mình đang học ngoại ngữ gì?", ["nhật"], [11], "cu"),
    ("Bạn gái mình tên gì?", ["linh"], [13], "moi"),
    ("Mình có ăn cay được không?", ["không"], [14], "moi"),
    ("Khi làm việc mình thích nghe nhạc của ai?", ["trịnh"], [15], "moi"),
    ("Mình đang tiết kiệm tiền để mua gì?", ["ô tô"], [19], "moi"),
    ("Laptop của mình là máy gì?", ["thinkpad"], [21], "moi"),
    ("Món ăn mình thích nhất là gì?", ["bún chả"], [23], "moi"),
    ("Mình dự định đi du lịch nước nào?", ["nhật"], [22], "moi"),
    ("Hiện giờ mình sống ở thành phố nào?", ["đà nẵng"], [12], "cap-nhat"),
    ("Công việc hiện tại của mình là gì?", ["machine learning"], [16], "cap-nhat"),
    ("Buổi sáng mình thường uống gì?", ["trà"], [18], "cap-nhat"),
    ("Giải bán marathon mình đăng ký diễn ra ngày nào?", ["8"], [20], "cap-nhat"),
    ("Con chó của mình bao nhiêu tuổi?", ["3"], [17], "cap-nhat"),
    ("Mình có nuôi mèo không?", ["không"], [], "khong-co"),
    ("Mình chơi nhạc cụ gì?", ["không"], [], "khong-co"),
]


def build_sessions(fillers_per_session: int = 14, seed: int = 0):
    """Danh sách turn: dict(session, idx, user, assistant, fact_id hoặc None). Fact ở vị trí ngẫu nhiên trong phiên."""
    rnd = random.Random(seed)
    turns = []
    for s in range(6):
        facts = [(i, u, a) for i, (sess, u, a) in enumerate(FACT_TURNS) if sess == s]
        items = [("fact", f) for f in facts]
        for _ in range(fillers_per_session):
            tpl = rnd.choice(FILLER_USER)
            text = tpl.format(**{k: rnd.choice(v) for k, v in FILL.items()})
            items.append(("filler", text))
        rnd.shuffle(items)
        for kind, item in items:
            if kind == "fact":
                fid, u, a = item
                turns.append({"session": s, "user": u, "assistant": a, "fact_id": fid})
            else:
                turns.append({"session": s, "user": item, "assistant": FILLER_ASSISTANT, "fact_id": None})
    for i, t in enumerate(turns):
        t["idx"] = i
    return turns
