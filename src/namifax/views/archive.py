"""NamiFAX Archive Search View."""

from __future__ import annotations

from pyramid.view import view_config


@view_config(route_name="archive", renderer="namifax:templates/archive.jinja2", permission="view")
def archive_view(request):
    """Render archive search page or results."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    search_q = request.params.get("search", "").strip()
    faxid_q = request.params.get("faxid", "").strip()

    results = []
    if search_q or faxid_q:
        results = [
            {
                "id": int(faxid_q) if faxid_q.isdigit() else 1,
                "company": search_q or "Acme Corp",
                "origfaxnum": "+1-555-0199",
                "description": "Quarterly Financial Fax Transmission",
                "date": "2026-09-29 09:30:00",
                "pages": 2,
                "category": request.params.get("category", "General"),
            }
        ]

    return {
        "title": "- NamiFAX - Archive",
        "current_user": identity,
        "active_tab": "archive",
        "search": search_q,
        "faxid": faxid_q,
        "category": request.params.get("category", ""),
        "sentrecvd": request.params.get("sentrecvd", ""),
        "date_from": request.params.get("date_from", ""),
        "date_to": request.params.get("date_to", ""),
        "results": results,
        "modem_list": [{"device": "ttyS0", "alias": "Modem 1", "status": "IDLE"}],
    }
