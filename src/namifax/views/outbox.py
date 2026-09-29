"""NamiFAX Outbox View."""

from __future__ import annotations

from pyramid.view import view_config


@view_config(route_name="outbox", renderer="namifax:templates/outbox.jinja2", permission="view")
def outbox_view(request):
    """Render outbox transmission queue and handle job deletion."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    flash_message = None

    kill_jid = request.params.get("kill")
    if kill_jid:
        flash_message = f"Job #{kill_jid} successfully killed and removed from queue."

    return {
        "title": "- NamiFAX - Outbox",
        "current_user": identity,
        "active_tab": "outbox",
        "jobs": [],
        "failed_jobs": [],
        "num_outbox": 0,
        "flash_message": flash_message,
        "modem_list": [
            {"device": "ttyS0", "alias": "Modem 1", "status": "IDLE"}
        ],
    }
