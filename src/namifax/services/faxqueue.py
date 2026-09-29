from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional, Sequence

from namifax.services.user_account import AFUserAccount

SENDQ_KEYS = ["jid", "pri", "s", "owner", "mailaddr", "number", "pages", "dials", "tts", "status"]
DONEQ_KEYS = ["jid", "pri", "s", "owner", "mailaddr", "number", "pages", "dials", "status"]


def parse_queue_output(lines: Sequence[str], keys: Sequence[str]) -> List[Dict[str, Any]]:
    """Parse HylaFAX faxstat queue output lines into structured dictionary items."""
    cleaned = list(lines)

    # 1. Drop scheduler status line if present
    if cleaned and "HylaFAX scheduler on" in cleaned[0]:
        cleaned.pop(0)

    # 2. Drop modem lines
    while cleaned and cleaned[0].startswith("Modem "):
        cleaned.pop(0)

    # 3. Drop empty lines and header line (starting with JID)
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)

    if cleaned and cleaned[0].strip().startswith("JID"):
        cleaned.pop(0)

    queue = []
    num_keys = len(keys)
    last_idx = num_keys - 1

    for line in cleaned:
        tokens = line.split()
        if not tokens:
            continue

        item: Dict[str, Any] = {}
        for j, token in enumerate(tokens):
            if j < last_idx:
                item[keys[j]] = token
            else:
                if keys[last_idx] in item:
                    item[keys[last_idx]] += f" {token}"
                else:
                    item[keys[last_idx]] = token
        queue.append(item)

    return queue


class FaxQueue:
    """Service managing HylaFAX outbound send queue and failed queue operations."""

    def __init__(
        self,
        user_account: Optional[AFUserAccount] = None,
        faxsendq_cmd: str = "faxstat -s",
        faxdoneq_cmd: str = "faxstat -d",
        faxrm_cmd: str = "faxrm",
        faxalter_cmd: str = "faxalter",
        faxmail_user: str = "faxmail",
        www_user: str = "www-data",
        auto_process: bool = True,
    ) -> None:
        self.user_account = user_account
        self.faxsendq_cmd = faxsendq_cmd
        self.faxdoneq_cmd = faxdoneq_cmd
        self.faxrm_cmd = faxrm_cmd
        self.faxalter_cmd = faxalter_cmd
        self.faxmail_user = faxmail_user
        self.www_user = www_user

        self.queue: List[Dict[str, Any]] = []

        if auto_process:
            self.process_queue()

    def shell_exec(self, cmd: str) -> str:
        """Execute system command and return stdout."""
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
            return res.stdout
        except Exception as e:
            return str(e)

    def process_queue(self, raw_output: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse active sending queue."""
        if raw_output is None:
            raw_output = self.shell_exec(self.faxsendq_cmd)

        lines = raw_output.splitlines()
        self.queue = parse_queue_output(lines, SENDQ_KEYS)
        return self.queue

    def process_failed_queue(self, raw_output: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse done queue and filter for failed faxes (s == 'F')."""
        if raw_output is None:
            raw_output = self.shell_exec(self.faxdoneq_cmd)

        lines = raw_output.splitlines()
        items = parse_queue_output(lines, DONEQ_KEYS)
        self.queue = [item for item in items if item.get("s") == "F"]
        return self.queue

    def get_queue(self) -> List[Dict[str, Any]]:
        """Return queue decorated with resolved user display names."""
        user_svc = self.user_account or AFUserAccount()
        ret = []

        for q in self.queue:
            entry = dict(q)
            owner = entry.get("owner", "")
            mailaddr = entry.get("mailaddr", "")

            if owner in (self.faxmail_user, self.www_user):
                if user_svc.loadbyemail(mailaddr):
                    entry["user"] = getattr(user_svc, "name", mailaddr)
                else:
                    entry["user"] = mailaddr
            elif user_svc.load_username(owner):
                entry["user"] = getattr(user_svc, "name", owner)
            else:
                entry["user"] = owner

            ret.append(entry)

        return ret

    def list_owner(self, owner: str) -> List[Dict[str, Any]]:
        """Filter queue for specific owner or corresponding faxmail address."""
        user_svc = self.user_account or AFUserAccount()
        ret = []

        for q in self.queue:
            entry = dict(q)
            q_owner = entry.get("owner", "")
            mailaddr = entry.get("mailaddr", "")

            if q_owner == owner:
                if user_svc.load_username(q_owner):
                    entry["user"] = getattr(user_svc, "name", owner)
                else:
                    entry["user"] = owner
                ret.append(entry)
            elif q_owner in (self.faxmail_user, self.www_user):
                if user_svc.loadbyemail(mailaddr):
                    user_username = getattr(user_svc, "username", "")
                    if owner == user_username:
                        entry["user"] = getattr(user_svc, "name", owner)
                        ret.append(entry)

        return ret

    def killjob(self, user: str, jid: int) -> bool:
        """Cancel and remove job from queue using faxrm."""
        cmd = f"export FAXUSER='{user}'; {self.faxrm_cmd} {jid}; unset FAXUSER"
        self.shell_exec(cmd)
        return True

    def faxalter(self, user: str, jid: int, operations: Dict[str, Any]) -> bool:
        """Modify parameters of queued job using faxalter."""
        ops = []
        killjob = False

        for op, val in operations.items():
            if op == "resubmit":
                ops.append("-r")
                killjob = True
            elif op == "sendtime":
                ops.append(f'-a "{val}"')
            elif op == "destination":
                ops.append(f'-d "{val}"')
            elif op == "killtime":
                ops.append(f'-k "{val}"')
            elif op == "device":
                ops.append(f'-m "{val}"')
            elif op == "priority":
                ops.append(f'-P "{val}"')
            elif op == "tries":
                ops.append(f'-t "{val}"')

        ops_str = " ".join(ops)
        cmd = f"export FAXUSER='{user}'; {self.faxalter_cmd} {ops_str} {jid}; unset FAXUSER"
        self.shell_exec(cmd)

        if killjob:
            self.killjob(user, jid)

        return True
