"""NamiFAX Archive Search View."""

from __future__ import annotations

from typing import Any

from pyramid.view import view_config

from namifax.services.addressbook import AFAddressBook
from namifax.services.archive_base import FaxPDFArchive
from namifax.services.categories import FaxPDFCategory
from namifax.views.admin import get_all_admin_modems
from namifax.views.fax_rights import fax_access


@view_config(route_name="archive", renderer="namifax:templates/archive.jinja2", permission="view")
def archive_view(request):
    """Render archive search page or results."""
    identity = request.identity or {"username": "admin", "is_admin": True}
    search_q = request.params.get("search", "").strip()
    faxid_q = request.params.get("faxid", "").strip()
    category_q = request.params.get("category", "")
    sentrecvd_q = request.params.get("sentrecvd", "")
    date_from_q = request.params.get("date_from", "")
    date_to_q = request.params.get("date_to", "")

    results: list[dict[str, Any]] = []
    searched = bool(search_q or faxid_q or category_q or sentrecvd_q or date_from_q or date_to_q)

    if searched:
        try:
            fa = FaxPDFArchive(db=request.dbsession)
            criteria = {
                "keywords": search_q or None,
                "faxid": int(faxid_q) if faxid_q.isdigit() else None,
                "category": category_q or None,
                "sentrecvd": sentrecvd_q or None,
                "start_date": date_from_q or None,
                "end_date": date_to_q or None,
                "userid": None if fax_access(request).superuser else fax_access(request).uid,
                **fax_access(request).search_rights(),
            }
            num_found = fa.search_archive(criteria)
            if num_found > 0:
                ab = AFAddressBook(db=request.dbsession)
                while True:
                    fid = fa.next_archive_entry()
                    if not fid:
                        break
                    # the search only yields ids: load each fax, then name its company from the address book
                    fax = FaxPDFArchive(db=request.dbsession)
                    if not fax.load_fax(fid):
                        continue
                    company = None
                    if fax.get_companyid() and ab.loadbycid(fax.get_companyid()):
                        company = ab.get_company()
                    if not company and fax.get_faxnumid() and ab.loadbyfaxnumid(fax.get_faxnumid()):
                        company = ab.get_company()
                    results.append({
                        "id": fid,
                        "company": company or "Unknown",
                        "origfaxnum": fax.get_origfaxnum() or "-",
                        "description": fax.get_description() or "Archived Fax",
                        "date": fax.get_archstamp() or "-",
                        "pages": fax.get_pages() or 1,
                        "category": str(fax.get_faxcatid() or "General"),
                    })
        except Exception:
            pass

    # Retrieve categories
    cat_svc = FaxPDFCategory(db=request.dbsession)
    categories = cat_svc.get_categories() or []

    return {
        "title": "- NamiFAX - Archive",
        "current_user": identity,
        "active_tab": "archive",
        "search": search_q,
        "faxid": faxid_q,
        "category": category_q,
        "sentrecvd": sentrecvd_q,
        "date_from": date_from_q,
        "date_to": date_to_q,
        "results": results,
        "searched": searched,
        "categories": categories,
        "modem_list": get_all_admin_modems(request.dbsession),
    }
