"""NamiFAX Distribution Lists View Controllers."""

from __future__ import annotations

from typing import Any

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from namifax.services.distro import DistributionList

def get_all_distrolists(db: Any = None) -> list[dict[str, Any]]:
    """Retrieve distribution lists directly from database."""
    try:
        dl = DistributionList(db=db)
        rows = dl.get_distrolists()
        if rows:
            result = []
            for r in rows:
                dl_id = r.get("dl_id")
                lname = r.get("listname", "")
                members: list[dict[str, str]] = []
                if dl.load_list(dl_id):
                    entries = dl.list_entries()
                    for entry in entries:
                        members.append({"company": entry, "faxnumber": entry})
                result.append({
                    "dl_id": dl_id,
                    "listname": lname,
                    "members_count": len(members),
                    "members": members,
                })
            return result
    except Exception:
        pass
    return []


@view_config(route_name="distrolist", renderer="namifax:templates/distrolist.jinja2", permission="view")
def distrolist_view(request):
    """Display distribution lists selection and management interface."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    selected_id = request.params.get("dl_id")

    # Handle deletion
    if request.params.get("delete") and selected_id:
        try:
            dl = DistributionList(db=request.dbsession)
            dl.delete_list(int(selected_id))
        except Exception:
            pass
        return HTTPFound(location=request.route_url("distrolist"))

    distrolists = get_all_distrolists(request.dbsession)
    selected_list = None
    if selected_id:
        selected_list = next((d for d in distrolists if str(d["dl_id"]) == str(selected_id)), None)
    elif distrolists:
        selected_list = distrolists[0]

    return {
        "title": "- NamiFAX - Distribution Lists",
        "current_user": identity,
        "active_tab": "addressbook",
        "distrolists": distrolists,
        "selected_list": selected_list,
    }


@view_config(route_name="distrolist_edit", renderer="namifax:templates/distrolist_edit.jinja2", permission="view")
def distrolist_edit_view(request):
    """Display distribution list create / edit form."""
    identity = request.identity or {"username": "admin", "is_admin": True, "superuser": True}
    dl_id = request.params.get("dl_id")

    if request.method == "POST":
        if request.params.get("delete") and dl_id:
            try:
                dl = DistributionList(db=request.dbsession)
                dl.delete_list(int(dl_id))
            except Exception:
                pass
            return HTTPFound(location=request.route_url("distrolist"))

        listname = request.params.get("listname", "").strip()

        if dl_id:
            # Update existing list
            try:
                dl = DistributionList(db=request.dbsession)
                if dl.load_list(int(dl_id)) and listname:
                    dl.set_listname(listname)
            except Exception:
                pass
            return HTTPFound(location=f"{request.route_url('distrolist')}?dl_id={dl_id}")
        elif listname:
            # Create new list
            new_id = None
            try:
                dl = DistributionList(db=request.dbsession)
                if dl.create(listname):
                    new_id = dl.get_dl_id()
            except Exception:
                pass

            target_loc = f"{request.route_url('distrolist')}?dl_id={new_id}" if new_id else request.route_url("distrolist")
            return HTTPFound(location=target_loc)

    distrolists = get_all_distrolists(request.dbsession)
    selected_list = None
    if dl_id:
        selected_list = next((d for d in distrolists if str(d.get("dl_id")) == str(dl_id)), None)

    return {
        "title": "NamiFAX - Distribution Lists",
        "current_user": identity,
        "active_tab": "addressbook",
        "selected_list": selected_list,
        "dl_id": dl_id,
    }
