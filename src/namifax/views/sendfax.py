"""NamiFAX SendFax View matching legacy NamiFAX behavior."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config


@view_config(route_name="sendfax", renderer="namifax:templates/sendfax.jinja2", permission="send_fax")
def sendfax_view(request):
    """Render send fax form or process submission."""
    identity = request.identity or {"username": "admin", "is_admin": True}

    if request.method == "POST":
        params = request.params
        faxnumber = (params.get("faxnumber") or params.get("destinations") or "").strip()

        if not faxnumber:
            request.response.status_code = 200
            return {
                "title": "- NamiFAX - Send Fax",
                "current_user": identity,
                "active_tab": "sendfax",
                "error": "Fax number is required",
                "form_data": params,
                "modem_list": [{"device": "ttyS0", "alias": "Modem 1", "status": "IDLE"}],
            }

        # Successful submission: redirect to outbox queue
        return HTTPFound(location=request.route_url("outbox"))

    return {
        "title": "- NamiFAX - Send Fax",
        "current_user": identity,
        "active_tab": "sendfax",
        "error": None,
        "form_data": {},
        "modem_list": [{"device": "ttyS0", "alias": "Modem 1", "status": "IDLE"}],
    }
