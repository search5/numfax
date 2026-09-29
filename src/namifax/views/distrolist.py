"""NamiFAX Distribution Lists View Controllers."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

# Mock in-memory distribution list groups with sample members
_SAMPLE_DISTRO_LISTS = [
    {
        "dl_id": 1,
        "listname": "Executive Team",
        "members_count": 2,
        "members": [
            {"company": "Acme Global", "faxnumber": "+1-555-0100"},
            {"company": "Initech Corp", "faxnumber": "+1-555-0199"},
        ],
    },
    {
        "dl_id": 2,
        "listname": "Sales Branch",
        "members_count": 1,
        "members": [
            {"company": "Regional Partner", "faxnumber": "+1-555-0188"},
        ],
    },
    {
        "dl_id": 3,
        "listname": "Regional Vendors",
        "members_count": 0,
        "members": [],
    },
]


@view_config(route_name="distrolist", renderer="namifax:templates/distrolist.jinja2", permission="view")
def distrolist_view(request):
    """Display distribution lists selection and management interface."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    selected_id = request.params.get("dl_id")
    
    # Handle deletion
    if request.params.get("delete") and selected_id:
        global _SAMPLE_DISTRO_LISTS
        _SAMPLE_DISTRO_LISTS = [d for d in _SAMPLE_DISTRO_LISTS if str(d["dl_id"]) != str(selected_id)]
        return HTTPFound(location=request.route_url("distrolist"))

    selected_list = None
    if selected_id:
        selected_list = next((d for d in _SAMPLE_DISTRO_LISTS if str(d["dl_id"]) == str(selected_id)), None)
    elif _SAMPLE_DISTRO_LISTS:
        selected_list = _SAMPLE_DISTRO_LISTS[0]

    return {
        "title": "- NamiFAX - Distribution Lists",
        "current_user": identity,
        "active_tab": "addressbook",
        "distrolists": _SAMPLE_DISTRO_LISTS,
        "selected_list": selected_list,
    }


@view_config(route_name="distrolist_edit", renderer="namifax:templates/distrolist_edit.jinja2", permission="view")
def distrolist_edit_view(request):
    """Display distribution list create / edit form."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    global _SAMPLE_DISTRO_LISTS

    dl_id = request.params.get("dl_id")

    if request.method == "POST":
        if request.params.get("delete") and dl_id:
            if str(dl_id) != "1":
                _SAMPLE_DISTRO_LISTS = [d for d in _SAMPLE_DISTRO_LISTS if str(d.get("dl_id")) != str(dl_id)]
            return HTTPFound(location=request.route_url("distrolist"))

        listname = request.params.get("listname", "").strip()

        if dl_id:
            # Update existing list
            existing = next((d for d in _SAMPLE_DISTRO_LISTS if str(d["dl_id"]) == str(dl_id)), None)
            if existing and listname:
                existing["listname"] = listname
            return HTTPFound(location=f"{request.route_url('distrolist')}?dl_id={dl_id}")
        elif listname:
            # Create new list
            new_id = max([d["dl_id"] for d in _SAMPLE_DISTRO_LISTS], default=0) + 1
            _SAMPLE_DISTRO_LISTS.append({
                "dl_id": new_id,
                "listname": listname,
                "members_count": 0,
                "members": [],
            })
            return HTTPFound(location=f"{request.route_url('distrolist')}?dl_id={new_id}")

    selected_list = None
    if dl_id:
        selected_list = next((d for d in _SAMPLE_DISTRO_LISTS if str(d.get("dl_id")) == str(dl_id)), None)
        if not selected_list and str(dl_id) == "1":
            selected_list = _SAMPLE_DISTRO_LISTS[0]

    return {
        "title": "NamiFAX - Distribution Lists",
        "current_user": identity,
        "active_tab": "addressbook",
        "selected_list": selected_list,
        "dl_id": dl_id,
    }
