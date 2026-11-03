import re

import pytest

import cikit
from testkit import Exercise

ex = Exercise(__file__)

CRON = re.compile(r"^(\d{1,2}) (\d{1,2}) \* \* 1$")


@pytest.fixture(scope="module")
def workflow():
    return cikit.load_workflow(ex.path("ct.yml"))


@pytest.fixture(scope="module")
def evs(workflow):
    return cikit.events(workflow)


def test_push_only_on_main_and_only_for_retraining_inputs(evs):
    push = evs.get("push")
    assert push is not None, "Thiếu trigger push"
    assert push.get("branches") == ["main"], "push chỉ trên nhánh main"
    assert sorted(push.get("paths") or []) == ["data.dvc", "params.yaml"], "push chỉ khi đổi params.yaml hoặc data.dvc"


def test_pull_request_uses_the_same_filter(evs):
    pr = evs.get("pull_request")
    assert pr is not None, "Thiếu trigger pull_request"
    assert sorted(pr.get("paths") or []) == ["data.dvc", "params.yaml"]


def test_weekly_schedule_on_monday(evs):
    schedule = evs.get("schedule")
    assert schedule, "Thiếu trigger schedule"
    crons = [item["cron"] for item in schedule]
    assert len(crons) == 1 and CRON.match(crons[0]), f"Cron phải dạng 'phút giờ * * 1', đang là {crons}"
    minute, hour = map(int, CRON.match(crons[0]).groups())
    assert minute < 60 and hour < 24
    assert (minute, hour) != (0, 0), "Đừng đặt đúng 00:00 UTC: giờ đó hàng triệu workflow cùng chạy"


def test_manual_dispatch_requires_a_reason(evs):
    assert "workflow_dispatch" in evs, "Thiếu workflow_dispatch"
    reason = ((evs["workflow_dispatch"] or {}).get("inputs") or {}).get("reason")
    assert reason, "workflow_dispatch cần input 'reason'"
    assert reason.get("required") is True and reason.get("type") == "string"


def test_token_is_read_only(workflow):
    assert workflow.get("permissions") == {"contents": "read"}, "Đặt permissions ở cấp workflow: chỉ contents: read"


def test_act_lists_the_train_job_for_each_event(tmp_path):
    repo = cikit.make_repo(tmp_path)
    cikit.write_workflow(repo, "ct.yml", ex.read("ct.yml"))
    cikit.commit_all(repo)
    for event in ("push", "pull_request", "schedule", "workflow_dispatch"):
        result = cikit.run_ci(repo, "-l", event=event)
        assert result.returncode == 0, cikit.log(result)[-1500:]
        assert "train" in result.stdout, f"act -l với sự kiện {event} không thấy job train:\n{result.stdout}"
