"""The scheduled maintenance is configured on an admin page (Admin > Scheduler): which jobs run, when, with which days; run now; the last
result of each job; and whether a scheduler is alive. The running scheduler follows the saved settings without a restart."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from bs4 import BeautifulSoup

from namifax.services import scheduler_config as cfg
from namifax.services.scheduler import NamiFaxScheduler
from namifax.services.system_config import SystemConfigService


@pytest.fixture
def client(testapp):
    testapp.post("/login", {"username": "admin", "password": "password", "_submit_check": "1"})
    return testapp


def _form(page):
    return next(f for f in page.forms.values() if "tmp_days" in f.fields)


# --- the settings -----------------------------------------------------------------------------------------------------------

def test_defaults_keep_the_old_behaviour(dbsession):
    s = cfg.load(dbsession)
    assert (s.tmp_enabled, s.tmp_time, s.tmp_days) == (True, "00:00", 1)
    assert s.inbox_enabled is False and s.lifecycle_enabled is True and (s.phonebook_enabled, s.phonebook_minutes) == (True, 60)


def test_saved_values_come_back(dbsession):
    s = cfg.load(dbsession)
    s.inbox_enabled, s.inbox_days, s.inbox_time = True, 14, "03:30"
    cfg.save(dbsession, s)
    again = cfg.load(dbsession)
    assert (again.inbox_enabled, again.inbox_days, again.inbox_time) == (True, 14, "03:30")


@pytest.mark.parametrize("raw,expected", [("07:05", "07:05"), ("7:5", "07:05"), ("24:00", "00:00"), ("junk", "00:00"), ("", "00:00")])
def test_times_are_checked(raw, expected):
    assert cfg.clean_time(raw, "00:00") == expected


def test_days_and_minutes_are_clamped(dbsession):
    s = cfg.load(dbsession)
    s.tmp_days, s.inbox_days, s.phonebook_minutes = -5, 99999, 0
    cfg.save(dbsession, s)
    again = cfg.load(dbsession)
    assert again.tmp_days >= 1 and again.inbox_days <= 3650 and again.phonebook_minutes >= 1


# --- the scheduler follows the settings ------------------------------------------------------------------------------------

def _jobs(sched):
    return {j.id: j for j in sched._scheduler.get_jobs()}


def test_jobs_are_scheduled_from_the_saved_settings(dbsession):
    s = cfg.load(dbsession)
    s.tmp_time, s.inbox_enabled, s.inbox_time, s.phonebook_minutes = "04:15", True, "05:20", 30
    cfg.save(dbsession, s)
    sched = NamiFaxScheduler()
    sched.start(blocking=False)
    try:
        sched.apply_config(dbsession)
        jobs = _jobs(sched)
        assert {"tmp", "inbox", "lifecycle", "phonebook"} <= set(jobs)
        tmp = jobs["tmp"].trigger
        assert isinstance(tmp, CronTrigger) and str(tmp.fields[5]) == "4" and str(tmp.fields[6]) == "15"
        assert isinstance(jobs["phonebook"].trigger, IntervalTrigger) and jobs["phonebook"].trigger.interval.total_seconds() == 1800
    finally:
        sched.stop()


def test_a_job_that_is_switched_off_is_removed(dbsession):
    sched = NamiFaxScheduler()
    sched.start(blocking=False)
    try:
        sched.apply_config(dbsession)
        assert "phonebook" in _jobs(sched)
        s = cfg.load(dbsession)
        s.phonebook_enabled = False
        cfg.save(dbsession, s)
        sched.apply_config(dbsession)
        assert "phonebook" not in _jobs(sched)
    finally:
        sched.stop()


def test_the_scheduler_notices_a_change_by_itself(dbsession):
    sched = NamiFaxScheduler()
    sched.start(blocking=False)
    try:
        sched.apply_config(dbsession)
        before = sched.config_signature
        s = cfg.load(dbsession)
        s.tmp_days = 9
        cfg.save(dbsession, s)
        assert sched.watch_config(dbsession) is True and sched.config_signature != before
        assert sched.watch_config(dbsession) is False                          # nothing new the second time
    finally:
        sched.stop()


def test_the_watcher_leaves_a_heartbeat(dbsession):
    sched = NamiFaxScheduler()
    sched.watch_config(dbsession)
    seen = cfg.heartbeat(dbsession)
    assert seen is not None and (datetime.now() - seen).total_seconds() < 5


# --- running a job ---------------------------------------------------------------------------------------------------------

def test_running_the_temp_cleanup_uses_the_saved_days(dbsession):
    s = cfg.load(dbsession)
    s.tmp_days = 3
    cfg.save(dbsession, s)
    with patch("namifax.services.scheduler.run_cron", return_value=0) as run:
        result = NamiFaxScheduler().run_job("tmp", dbsession)
    assert result["ok"] is True and run.call_args.args[0][:3] == ["cron", "-t", "3"]


def test_the_inbox_job_archives_by_the_saved_days(dbsession):
    s = cfg.load(dbsession)
    s.inbox_days = 21
    cfg.save(dbsession, s)
    with patch("namifax.services.scheduler.ArchiveIn") as inbox:
        inbox.return_value.prune_inbox.return_value = 4
        result = NamiFaxScheduler().run_job("inbox", dbsession)
    inbox.return_value.prune_inbox.assert_called_once_with(21)
    assert result["ok"] and "4" in result["summary"]


def test_the_lifecycle_job_says_when_no_policy_was_saved(dbsession):
    result = NamiFaxScheduler().run_job("lifecycle", dbsession)
    assert result["ok"] is True and "no policy" in result["summary"].lower()


def test_a_failing_job_is_recorded_not_raised(dbsession):
    with patch("namifax.services.scheduler.export_phonebook", side_effect=OSError("disk full")):
        result = NamiFaxScheduler().run_job("phonebook", dbsession)
    assert result["ok"] is False and "disk full" in result["summary"]
    assert cfg.last_run(dbsession, "phonebook")["ok"] is False


def test_the_last_run_is_remembered(dbsession):
    with patch("namifax.services.scheduler.export_phonebook", return_value=7):
        NamiFaxScheduler().run_job("phonebook", dbsession)
    last = cfg.last_run(dbsession, "phonebook")
    assert last["ok"] is True and "7" in last["summary"] and last["at"]


def test_an_unknown_job_is_refused(dbsession):
    with pytest.raises(ValueError):
        NamiFaxScheduler().run_job("nonsense", dbsession)


# --- the admin page --------------------------------------------------------------------------------------------------------

def test_the_page_lists_the_jobs_with_their_settings(client):
    soup = BeautifulSoup(client.get("/admin/scheduler").text, "html.parser")
    form = _form(client.get("/admin/scheduler"))
    for field in ("tmp_enabled", "tmp_time", "tmp_days", "inbox_enabled", "inbox_time", "inbox_days", "lifecycle_enabled",
                  "lifecycle_time", "phonebook_enabled", "phonebook_minutes"):
        assert field in form.fields, field
    assert soup.find("a", href="/admin/storage") is not None                       # the retention policy lives there


def test_saving_the_page_stores_the_settings(client, dbsession):
    form = _form(client.get("/admin/scheduler"))
    form["tmp_days"], form["tmp_time"] = "5", "03:10"
    form["inbox_enabled"], form["inbox_days"] = True, "45"
    res = form.submit()
    assert "saved" in res.text.lower()
    s = cfg.load(dbsession)
    assert (s.tmp_days, s.tmp_time, s.inbox_enabled, s.inbox_days) == (5, "03:10", True, 45)


def test_unticking_a_job_switches_it_off(client, dbsession):
    form = _form(client.get("/admin/scheduler"))
    form["phonebook_enabled"] = False
    form.submit()
    assert cfg.load(dbsession).phonebook_enabled is False


def test_a_bad_time_is_not_stored(client, dbsession):
    form = _form(client.get("/admin/scheduler"))
    form["tmp_time"] = "99:99"
    form.submit()
    assert cfg.load(dbsession).tmp_time == "00:00"


def test_run_now_runs_the_job_and_shows_the_result(client):
    page = client.get("/admin/scheduler")
    run = next(f for f in page.forms.values() if f.fields.get("job") and f["job"].value == "phonebook")
    with patch("namifax.services.scheduler.export_phonebook", return_value=12):
        res = run.submit()
    assert "12" in res.text


def test_the_page_shows_the_last_result_and_the_scheduler_state(client, dbsession):
    with patch("namifax.services.scheduler.export_phonebook", return_value=3):
        NamiFaxScheduler().run_job("phonebook", dbsession)
    html = client.get("/admin/scheduler").text
    assert "3" in html and "no scheduler is running" in html.lower()           # no scheduler heartbeat in a test
    cfg.beat(dbsession)
    after = client.get("/admin/scheduler").text.lower()
    assert "a scheduler is running" in after and "no scheduler is running" not in after


def test_only_an_administrator_may_open_it(testapp, dbsession):
    from namifax.services.user_account import AFUserAccount

    svc = AFUserAccount(db=dbsession)
    assert svc.create({"username": "plain", "password": "Secret123!", "email": "p@x.test", "name": "P", "acc_enabled": 1,
                       "last_login": "2026-01-01 10:00:00"})
    dbsession.flush()
    import webtest

    other = webtest.TestApp(testapp.app, extra_environ=testapp.extra_environ)
    other.post("/login", {"username": "plain", "password": "Secret123!", "_submit_check": "1"})
    assert other.get("/admin/scheduler", expect_errors=True).status_int in (302, 303, 403)


def test_the_menu_links_to_it(client):
    assert 'href="/admin/scheduler"' in client.get("/admin").text
