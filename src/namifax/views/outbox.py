"""NamiFAX Outbox View."""

from __future__ import annotations

from pyramid.view import view_config

from namifax.services.faxqueue import FaxQueue
from namifax.views.admin import get_all_admin_modems


@view_config(route_name="outbox", renderer="namifax:templates/outbox.jinja2", permission="view")
def outbox_view(request):
    """Render outbox transmission queue and handle job deletion."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    flash_message = None

    fq = FaxQueue(auto_process=False)

    kill_jid = request.params.get("kill")
    if kill_jid:
        try:
            success = fq.killjob(kill_jid)
            if success:
                flash_message = f"Job #{kill_jid} successfully killed"
            else:
                flash_message = f"Failed to kill job #{kill_jid}"
        except Exception:
            flash_message = f"Failed to kill job #{kill_jid}"

    try:
        jobs = fq.process_queue()
    except Exception:
        jobs = []

    try:
        failed_jobs = fq.process_failed_queue()
    except Exception:
        failed_jobs = []

    modem_list = get_all_admin_modems(request.db)

    return {
        "title": "- NamiFAX - Outbox",
        "current_user": identity,
        "active_tab": "outbox",
        "jobs": jobs,
        "failed_jobs": failed_jobs,
        "num_outbox": len(jobs),
        "flash_message": flash_message,
        "modem_list": modem_list,
    }
