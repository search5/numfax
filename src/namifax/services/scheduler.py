"""NamiFAX Scheduler Service managing periodic maintenance jobs using APScheduler.

Replaces OS-level crontab with in-process or standalone scheduling.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from typing import Callable, Optional

# Ensure src directory is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from namifax.cli.cron import run_cron
from namifax.cli.phb import export_phonebook
from namifax.db.provider import cli_session
from namifax.services import scheduler_config as cfg
from namifax.services.archive_in import ArchiveIn

logger = logging.getLogger("namifax.scheduler")


class NamiFaxScheduler:
    """Integrated task scheduler using APScheduler with threading fallback."""

    def __init__(self, tmp_clean_days: int = 1, phonebook_sync_interval_mins: int = 60) -> None:
        self.tmp_clean_days = tmp_clean_days
        self.phonebook_sync_interval_mins = phonebook_sync_interval_mins
        self.is_running = False
        self._scheduler = None
        self._fallback_threads: list[threading.Thread] = []
        self._stop_event = threading.Event()

    # --- the jobs -----------------------------------------------------------------------------------------------------

    def run_job(self, name: str, session=None) -> dict:
        """Run one job now (on a schedule or from the admin page) and remember how it went; never raises.

        Returns ``{"ok", "summary", "at"}``. ``session`` is used when given, else the job opens its own on the configured database.
        """
        if name not in cfg.JOBS:
            raise ValueError(f"unknown job: {name}")
        if session is None:
            with cli_session(ensure_schema=True) as opened:
                return self.run_job(name, opened)

        settings = cfg.load(session)
        try:
            if name == "tmp":
                run_cron(["cron", "-t", str(settings.tmp_days)], db=session)
                summary = f"temporary files older than {settings.tmp_days} day(s) removed"
            elif name == "inbox":
                moved = ArchiveIn(db=session).prune_inbox(settings.inbox_days)
                summary = f"{moved} fax(es) older than {settings.inbox_days} day(s) moved to the archive"
            elif name == "lifecycle":
                from namifax.services.storage_lifecycle import StorageLifecycleService

                result = StorageLifecycleService(db=session).run_saved_policy()
                summary = ("no policy saved on the Storage page: nothing was removed" if result is None else
                           f"{result.get('tiffs_purged', 0)} TIFF file(s) and {result.get('faxes_purged', 0)} fax(es) removed")
            else:
                summary = f"phonebook exported ({export_phonebook(db=session)} entries)"
            ok = True
        except Exception as exc:                                      # a failed job is a result, not a crash of the scheduler
            logger.error("[Scheduler] job %s failed: %s", name, exc, exc_info=True)
            ok, summary = False, f"failed: {exc}"
        result = cfg.record_run(session, name, ok, summary)
        try:
            from namifax.common.helpers import avantfaxlog

            avantfaxlog(f"scheduler> {name}: {summary}", echo=False, session=session)
        except Exception:
            pass
        return result

    def _scheduled(self, name: str) -> None:
        self.run_job(name)

    # --- following the saved settings ---------------------------------------------------------------------------------

    config_signature: str = ""

    @property
    def engine_running(self) -> bool:
        """Is the APScheduler engine itself running (jobs can fire)?"""
        return self._scheduler is not None and bool(getattr(self._scheduler, "running", False))

    def apply_config(self, session=None) -> None:
        """(Re)schedule every job from the saved settings; a job that is switched off is removed."""
        if self._scheduler is None:
            return
        if session is None:
            with cli_session(ensure_schema=True) as opened:
                return self.apply_config(opened)

        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        s = cfg.load(session)
        wanted = {}
        for name, enabled, at in (("tmp", s.tmp_enabled, s.tmp_time), ("inbox", s.inbox_enabled, s.inbox_time),
                                  ("lifecycle", s.lifecycle_enabled, s.lifecycle_time)):
            if enabled:
                hour, minute = at.split(":")
                wanted[name] = CronTrigger(hour=int(hour), minute=int(minute))
        if s.phonebook_enabled:
            wanted["phonebook"] = IntervalTrigger(minutes=s.phonebook_minutes)
        for name in cfg.JOBS:
            if name in wanted:
                self._scheduler.add_job(self._scheduled, trigger=wanted[name], args=[name], id=name, name=name,
                                        replace_existing=True, misfire_grace_time=3600, coalesce=True)
            elif self._scheduler.get_job(name):
                self._scheduler.remove_job(name)
        self.config_signature = cfg.signature(session)

    # --- the APScheduler engine: started and shut down as the administrator asks ----------------------------------------

    def start_engine(self, session=None) -> None:
        """Create and start the APScheduler engine with the saved jobs."""
        if self.engine_running:
            return
        from apscheduler.schedulers.background import BackgroundScheduler

        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        try:
            self.apply_config(session)
        except Exception as exc:
            logger.error("[Scheduler] could not read the saved settings: %s", exc)
        logger.info("[Scheduler] APScheduler engine started.")

    def stop_engine(self) -> None:
        """Shut the APScheduler engine down: no job fires until it is started again."""
        engine, self._scheduler = self._scheduler, None
        if engine is not None:
            try:
                engine.shutdown(wait=False)
            except Exception:
                pass
            logger.info("[Scheduler] APScheduler engine stopped.")

    def watch_config(self, session=None) -> bool:
        """The controller's turn: say we are alive, start or stop the engine as asked, follow changed settings.

        True when the engine was started or stopped or the jobs were rescheduled.
        """
        if session is None:
            with cli_session(ensure_schema=True) as opened:
                return self.watch_config(opened)
        changed = False
        want_running = not cfg.stopped(session)
        if want_running and not self.engine_running:
            self.start_engine(session)
            changed = True
        elif not want_running and self.engine_running:
            self.stop_engine()
            changed = True
        elif self.engine_running and cfg.signature(session) != self.config_signature:
            self.apply_config(session)
            changed = True
        cfg.beat(session, "running" if self.engine_running else "stopped")
        return changed

    def _control_loop(self) -> None:
        while not self._stop_event.wait(self.control_interval):
            try:
                self.watch_config()
            except Exception as exc:
                logger.error("[Scheduler] controller check failed: %s", exc)

    def job_phonebook_sync(self) -> None:
        """Execute periodic address book to HylaFAX PBOOK1.1 synchronization."""
        self.run_job("phonebook")

    control_interval = 15            # seconds between the controller's checks (it hears a Stop/Start within this time)
    _control_thread: Optional[threading.Thread] = None

    def start(self, blocking: bool = False) -> None:
        """Start the scheduler: the controller thread, and the APScheduler engine unless an administrator stopped it.

        With ``blocking`` the call waits until ``stop()`` (the standalone service); a Stop on the admin page shuts only the engine
        down, the process stays so that a Start can bring it back.
        """
        if self.is_running:
            return
        self._stop_event.clear()
        self.is_running = True

        try:
            import apscheduler  # noqa: F401
        except ImportError:                                                  # a plain thread timer when APScheduler is missing
            logger.warning("[Scheduler] APScheduler not installed; using built-in thread timer.")

            def _runner():
                while not self._stop_event.wait(self.phonebook_sync_interval_mins * 60):
                    self.job_phonebook_sync()

            t = threading.Thread(target=_runner, daemon=True, name="NamiFaxSchedulerFallback")
            t.start()
            self._fallback_threads.append(t)
        else:
            try:
                with cli_session(ensure_schema=True) as session:
                    if not cfg.stopped(session):
                        self.start_engine(session)
                    cfg.beat(session, "running" if self.engine_running else "stopped")
            except Exception as exc:                                         # no database yet: run with the defaults
                logger.error("[Scheduler] could not read the saved settings: %s", exc)
                if not self.engine_running:
                    self.start_engine_without_settings()
            self._control_thread = threading.Thread(target=self._control_loop, daemon=True, name="NamiFaxSchedulerControl")
            self._control_thread.start()

        if blocking:
            try:
                while not self._stop_event.wait(1):
                    pass
            except KeyboardInterrupt:
                self.stop()

    def start_engine_without_settings(self) -> None:
        from apscheduler.schedulers.background import BackgroundScheduler

        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

    def stop(self) -> None:
        """Stop everything: the engine and the controller (the process is meant to end)."""
        if not self.is_running:
            return
        self._stop_event.set()
        self.stop_engine()
        thread = self._control_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._control_thread = None
        self.is_running = False
        logger.info("[Scheduler] Scheduler stopped.")


_global_scheduler: Optional[NamiFaxScheduler] = None


def get_scheduler() -> NamiFaxScheduler:
    """Retrieve global singleton scheduler instance."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = NamiFaxScheduler()
    return _global_scheduler


def run_scheduler_standalone() -> int:
    """CLI entry point to run scheduler as dedicated foreground/systemd process."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("[*] Starting NamiFAX Standalone Scheduler Daemon (APScheduler)...")
    sched = get_scheduler()
    try:
        sched.start(blocking=True)
    except (KeyboardInterrupt, SystemExit):
        sched.stop()
        print("[*] NamiFAX Scheduler Daemon stopped.")
    return 0
