import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def mem():
    return ex.module("memory.py")


class EchoChat(GenericFakeChatModel):
    """Fake chat model: trả "#<số lời gọi>: <message cuối>", ghi lại messages của mọi lần gọi."""

    seen: list = []

    def __init__(self):
        super().__init__(messages=iter([]))
        self.seen = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        reply = AIMessage(content=f"#{len(self.seen)}: {messages[-1].content}")
        return ChatResult(generations=[ChatGeneration(message=reply)])


def contents(messages):
    return [(m.type, m.content) for m in messages]


def test_turn_and_system_prompt(mem):
    llm = EchoChat()
    app = mem.build_chat(llm, InMemorySaver())
    assert mem.turn(app, "a", "Tôi ở Đà Nẵng.") == "#1: Tôi ở Đà Nẵng."
    assert mem.turn(app, "a", "Tôi ở đâu?") == "#2: Tôi ở đâu?"
    assert contents(llm.seen[1]) == [("system", mem.SYSTEM), ("human", "Tôi ở Đà Nẵng."),
                                     ("ai", "#1: Tôi ở Đà Nẵng."), ("human", "Tôi ở đâu?")]


def test_threads_are_isolated(mem):
    llm = EchoChat()
    app = mem.build_chat(llm, InMemorySaver())
    mem.turn(app, "lan", "Tôi tên Lan.")
    mem.turn(app, "minh", "Tôi tên Minh.")
    mem.turn(app, "lan", "Tôi tên gì?")
    assert [c for _, c in contents(llm.seen[2]) if "Minh" in c] == [], "thread lan thấy hội thoại của minh"
    assert ("human", "Tôi tên Lan.") in contents(llm.seen[2])
    assert len(llm.seen[1]) == 2, "thread mới chỉ có system và câu đầu"


def test_window_trims_what_model_sees_not_state(mem):
    llm = EchoChat()
    app = mem.build_chat(llm, InMemorySaver(), max_messages=4)
    for i in range(1, 4):
        mem.turn(app, "t", f"câu {i}")
    sent = contents(llm.seen[2])
    assert sent == [("system", mem.SYSTEM), ("human", "câu 2"), ("ai", "#2: câu 2"), ("human", "câu 3")], \
        "cửa sổ 4 message cuối phải bắt đầu bằng message người dùng"
    state = app.get_state({"configurable": {"thread_id": "t"}}).values["messages"]
    assert len(state) == 6, "state vẫn giữ toàn bộ lịch sử"


def test_sqlite_survives_restart(mem, tmp_path):
    path = tmp_path / "chat.db"
    saver = mem.open_saver(path)
    app = mem.build_chat(EchoChat(), saver)
    mem.turn(app, "u1", "Tôi có hai con.")
    saver.conn.close()

    llm = EchoChat()
    saver2 = mem.open_saver(path)
    app2 = mem.build_chat(llm, saver2)
    mem.turn(app2, "u1", "Tôi có mấy con?")
    assert ("human", "Tôi có hai con.") in contents(llm.seen[0]), "lịch sử phải đọc lại từ tệp SQLite"
    saver2.conn.close()


def test_sqlite_saver_usable_from_other_thread(mem, tmp_path):
    import threading

    saver = mem.open_saver(tmp_path / "x.db")
    app = mem.build_chat(EchoChat(), saver)
    errors = []

    def work():
        try:
            mem.turn(app, "t", "xin chào")
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=work)
    worker.start()
    worker.join()
    assert errors == []
    saver.conn.close()


def test_timeline_two_turns(mem):
    app = mem.build_chat(EchoChat(), InMemorySaver())
    assert mem.timeline(app, "none") == []
    mem.turn(app, "t", "a")
    mem.turn(app, "t", "b")
    tl = mem.timeline(app, "t")
    assert [x["step"] for x in tl] == [-1, 0, 1, 2, 3, 4]
    assert [x["messages"] for x in tl] == [0, 1, 2, 2, 3, 4]
    assert tl[-1]["next"] == () and tl[1]["next"] == ("chat",)
    assert len({x["checkpoint_id"] for x in tl}) == 6


def test_fork_creates_branch_and_keeps_old(mem):
    llm = EchoChat()
    app = mem.build_chat(llm, InMemorySaver())
    mem.turn(app, "t", "Tôi ở Huế.")
    mem.turn(app, "t", "Tôi chuyển vào Sài Gòn.")
    old = mem.timeline(app, "t")
    after_first = next(x for x in old if x["messages"] == 2 and x["next"] == ())
    reply = mem.fork(app, "t", after_first["checkpoint_id"], "Tôi chuyển ra Hà Nội.")
    assert reply == "#3: Tôi chuyển ra Hà Nội."
    assert ("human", "Tôi chuyển vào Sài Gòn.") not in contents(llm.seen[2]), "nhánh mới không thấy lượt đã bỏ"

    new = mem.timeline(app, "t")
    assert [x["messages"] for x in new] == [0, 1, 2, 2, 3, 4]
    assert [x["checkpoint_id"] for x in new[:3]] == [x["checkpoint_id"] for x in old[:3]], "chung gốc tới điểm rẽ"
    assert new[-1]["checkpoint_id"] != old[-1]["checkpoint_id"]
    latest = app.get_state({"configurable": {"thread_id": "t"}}).values["messages"]
    assert latest[-2].content == "Tôi chuyển ra Hà Nội."
    old_head = app.get_state({"configurable": {"thread_id": "t", "checkpoint_id": old[-1]["checkpoint_id"]}})
    assert old_head.values["messages"][2].content == "Tôi chuyển vào Sài Gòn.", "nhánh cũ vẫn còn nguyên"

    mem.turn(app, "t", "Tôi ở đâu?")
    assert ("human", "Tôi chuyển ra Hà Nội.") in contents(llm.seen[3])
    assert ("human", "Tôi chuyển vào Sài Gòn.") not in contents(llm.seen[3])


def test_forget_deletes_one_thread(mem, tmp_path):
    saver = mem.open_saver(tmp_path / "f.db")
    app = mem.build_chat(EchoChat(), saver)
    mem.turn(app, "a", "bí mật của a")
    mem.turn(app, "b", "chuyện của b")
    mem.forget(saver, "a")
    assert mem.timeline(app, "a") == []
    assert len(mem.timeline(app, "b")) == 3
    saver.conn.close()
