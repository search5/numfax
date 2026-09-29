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

    def job_cron_maintenance(self) -> None:
        """Execute daily temporary folder and inbox retention cleanup."""
        logger.info("[Scheduler] Executing scheduled cron maintenance...")
        try:
            run_cron(["cron", "-t", str(self.tmp_clean_days)])
            logger.info("[Scheduler] Cron maintenance completed successfully.")
        except Exception as exc:
            logger.error(f"[Scheduler] Cron maintenance failed: {exc}", exc_info=True)

    def job_phonebook_sync(self) -> None:
        """Execute periodic address book to HylaFAX PBOOK1.1 synchronization."""
        logger.info("[Scheduler] Executing scheduled phonebook synchronization...")
        try:
            count = export_phonebook()
            logger.info(f"[Scheduler] Phonebook synchronized {count} entries.")
        except Exception as exc:
            logger.error(f"[Scheduler] Phonebook synchronization failed: {exc}", exc_info=True)

    def start(self, blocking: bool = False) -> None:
        """Start scheduler. Uses APScheduler if available, else lightweight thread timer."""
        if self.is_running:
            return

        self._stop_event.clear()
        self.is_running = True

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger

            sched_cls = BlockingScheduler if blocking else BackgroundScheduler
            self._scheduler = sched_cls()

            # Schedule daily maintenance at 00:00 (midnight)
            self._scheduler.add_job(
                self.job_cron_maintenance,
                trigger=CronTrigger(hour=0, minute=0),
                id="cron_maintenance",
                name="Daily Temporary & Retention Cleanup",
                replace_existing=True,
            )

            # Schedule phonebook sync interval
            self._scheduler.add_job(
                self.job_phonebook_sync,
                trigger=IntervalTrigger(minutes=self.phonebook_sync_interval_mins),
                id="phonebook_sync",
                name="Periodic Phonebook Sync",
                replace_existing=True,
            )

            logger.info("[Scheduler] Starting APScheduler engine...")
            self._scheduler.start()

        except ImportError:
            # Fallback to internal daemon thread if apscheduler is not installed
            logger.warning("[Scheduler] APScheduler not installed; using built-in thread timer.")

            def _runner():
                while not self._stop_event.is_set():
                    # Sleep in small increments to be responsive to stop signal
                    for _ in range(self.phonebook_sync_interval_mins * 60):
                        if self._stop_event.is_set():
                            break
                        time.sleep(1)
                    if not self._stop_event.is_set():
                        self.job_phonebook_sync()

            t = threading.Thread(target=_runner, daemon=True, name="NamiFaxSchedulerFallback")
            t.start()
            self._fallback_threads.append(t)

            if blocking:
                try:
                    while not self._stop_event.is_set():
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.stop()

    def stop(self) -> None:
        """Stop scheduler and release workers."""
        if not self.is_running:
            return

        self._stop_event.set()
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass
            self._scheduler = None

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
