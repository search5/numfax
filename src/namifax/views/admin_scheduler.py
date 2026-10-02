"""Admin > Scheduled Tasks: which maintenance jobs run, when, with which days; run one now; how the last run went."""

from __future__ import annotations

from datetime import datetime

from pyramid.view import view_config

from namifax.i18n import _
from namifax.services import scheduler_config as cfg
from namifax.services.scheduler import NamiFaxScheduler, get_scheduler
from namifax.services.system_config import SystemConfigService


def _read(post, current: cfg.JobSettings) -> tuple[cfg.JobSettings, list[str]]:
    """The settings from the form; a time that is not ``HH:MM`` keeps the old value and is reported."""
    problems: list[str] = []

    def time(name: str, old: str) -> str:
        raw = post.get(name, "")
        clean = cfg.clean_time(raw, "")
        if not clean:
            problems.append(f"{raw!r}")
            return old
        return clean

    def number(name: str, old: int) -> int:
        raw = (post.get(name) or "").strip()
        return int(raw) if raw.isdigit() else old

    updated = cfg.JobSettings(
        tmp_enabled="tmp_enabled" in post, tmp_time=time("tmp_time", current.tmp_time), tmp_days=number("tmp_days", current.tmp_days),
        inbox_enabled="inbox_enabled" in post, inbox_time=time("inbox_time", current.inbox_time),
        inbox_days=number("inbox_days", current.inbox_days),
        lifecycle_enabled="lifecycle_enabled" in post, lifecycle_time=time("lifecycle_time", current.lifecycle_time),
        phonebook_enabled="phonebook_enabled" in post, phonebook_minutes=number("phonebook_minutes", current.phonebook_minutes),
    )
    return updated, problems


@view_config(route_name="admin_scheduler", renderer="namifax:templates/admin_scheduler.jinja2", permission="admin")
def admin_scheduler_view(request):
    """The scheduled tasks page."""
    session = request.dbsession
    message = error = None
    current = cfg.load(session)

    if request.method == "POST":
        action = request.POST.get("action")
        if action in ("stop", "start"):
            cfg.set_stopped(session, action == "stop")
            hosted = get_scheduler()
            if hosted.is_running:                          # this process hosts the scheduler: act at once, do not wait for the next check
                hosted.watch_config(session)
            message = (_("The scheduler was stopped. Nothing runs by itself until it is started again; Run now still works.")
                       if action == "stop" else _("The scheduler was started."))
        elif action == "run":
            job = request.POST.get("job", "")
            if job in cfg.JOBS:
                result = NamiFaxScheduler().run_job(job, session)
                message = f"{job}: {result['summary']}" if result["ok"] else None
                error = None if result["ok"] else f"{job}: {result['summary']}"
            else:
                error = _("Unknown task.")
        else:
            updated, bad = _read(request.POST, current)
            cfg.save(session, updated)
            current = cfg.load(session)
            if bad:
                error = _("A time must be written HH:MM (24 hours); the old time was kept.") + " " + ", ".join(bad)
            else:
                message = _("Scheduled tasks saved. A running scheduler picks the change up within a minute.")

    store = SystemConfigService(session)
    seen = cfg.heartbeat(session)
    return {
        "title": "NamiFAX - Admin - Scheduled Tasks",
        "current_user": request.identity,
        "active_tab": "admin",
        "active_admin": "scheduler",
        "s": current,
        "last": {job: cfg.last_run(session, job) for job in cfg.JOBS},
        "alive": cfg.alive(session),
        "stopped": cfg.stopped(session) or cfg.engine_state(session) == "stopped",
        "seen_ago": int((datetime.now() - seen).total_seconds()) if seen else None,
        "policy": {"tiff_days": store.get("storage_purge_tiff_days", ""), "keep_days": store.get("storage_retention_days", "")},
        "message": message,
        "error": error,
    }
