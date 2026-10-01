import math
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from namifax.db.repository import MDBOData
from namifax.services import archive_orm


PDFNAME = "fax.pdf"
THUMBNAIL = "thumb.png"
TIFFNAME = "fax.tif"
PREVIMG = "page"
PREVIMGSFX = ".png"
DEFAULT_ARCHIVE_DATE_FORMAT = "%Y-%m-%d %H:%M"


def clean_faxnum(num: Optional[str]) -> str:
    if not num:
        return ""
    return re.sub(r"[^\d+]", "", str(num))


class FaxPDFArchive:
    """Core Archive Domain Service managing fax metadata, inbox/archive search, permissions, and file pruning."""

    def __init__(
        self,
        db: Any = None,
        installdir: str = "",
        date_format: str = DEFAULT_ARCHIVE_DATE_FORMAT,
    ) -> None:
        self.db = db
        self._orm = isinstance(db, Session)     # a session: portable ORM queries; else the legacy SQL
        self._route_filters: List[Any] = []
        self.installdir = installdir
        self.date_format = date_format

        self.faxarchive = MDBOData("FaxArchive", db=self.db)
        self.dbdata: Dict[str, Any] = {}

        self.thumbnail: Optional[str] = None
        self.tiffpath: Optional[str] = None
        self.pdfpath: Optional[str] = None
        self.faximages: List[str] = []
        self.m_archstamp: Optional[str] = None
        self.m_lastmoddate: Optional[str] = None
        self.m_lastoperation: Optional[str] = None
        self.error: Optional[str] = None

        self.archive_results: Optional[List[Dict[str, Any]]] = None
        self.sqlroutes: str = ""

    def get_error(self) -> Optional[str]:
        return self.error

    def get_faxcatid(self) -> Optional[int]:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return None
        return self.dbdata.get("faxcatid")

    def user_has_rights(
        self,
        userid: int,
        modems: Optional[List[Any]] = None,
        routes: Optional[List[Any]] = None,
        faxcat: Optional[List[Any]] = None,
    ) -> bool:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        modems = self.check_empty_array(modems or [])
        routes = self.check_empty_array(routes or [])
        faxcat = self.check_empty_array(faxcat or [])

        # User matches
        if userid and self.dbdata.get("userid") == userid:
            return True

        # Modem matches
        if modems and self.dbdata.get("modemdev") in modems:
            return True

        # Fax category matches
        if faxcat and self.dbdata.get("faxcatid") in faxcat:
            return True

        # Route matches
        if routes:
            didr_id = self.dbdata.get("didr_id")
            # Handle int and str representations
            if didr_id in routes or str(didr_id) in [str(r) for r in routes]:
                return True

        return False

    @staticmethod
    def check_empty_array(a: List[Any]) -> List[Any]:
        if a and (a[0] is None or a[0] == ""):
            return a[1:]
        return a

    def viewable_devices(
        self,
        devices: Optional[List[Any]] = None,
        faxcats: Optional[List[Any]] = None,
        enable_did_routing: bool = False,
    ) -> None:
        if self._orm:
            self._route_filters = archive_orm.inbox_filters(devices, faxcats, enable_did_routing)
            return
        myroutes = []
        mycategories = []

        if isinstance(devices, list):
            for dev in devices:
                if dev == "" or dev is None:
                    continue
                qdev = self.faxarchive.quote(str(dev))
                if enable_did_routing:
                    myroutes.append(f"didr_id = {qdev}")
                else:
                    myroutes.append(f"modemdev = {qdev}")

        if devices is None:
            self.sqlroutes = ""
        elif myroutes:
            self.sqlroutes = " AND (" + " OR ".join(myroutes) + ")"
        else:
            self.sqlroutes = " AND modemdev = '' "

        if isinstance(faxcats, list):
            for cat in faxcats:
                if cat is None:
                    continue
                qcat = self.faxarchive.quote(cat)
                mycategories.append(f"faxcatid = {qcat}")

            mycategories.append("(faxcatid is null or faxcatid = '')")

            if mycategories:
                self.sqlroutes += " AND (" + " OR ".join(mycategories) + ")"
            else:
                self.sqlroutes += " AND faxcatid = '' "

    def get_num_faxes(
        self,
        devices: Optional[List[Any]] = None,
        faxcats: Optional[List[Any]] = None,
        enable_did_routing: bool = False,
    ) -> int:
        self.viewable_devices(devices, faxcats, enable_did_routing)
        if self._orm:
            return archive_orm.count_inbox(self.db, self._route_filters)
        query = f"SELECT fid FROM FaxArchive WHERE inbox = 1 {self.sqlroutes}"
        results = self.faxarchive.query(query, reduce_single=False)
        return len(results) if isinstance(results, list) else 0

    def get_fid_prev(self) -> Optional[int]:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return None

        results = self._inbox_fids()
        fid = None

        if isinstance(results, list):
            for info in results:
                if info["fid"] == self.dbdata["fid"]:
                    return fid
                else:
                    fid = info["fid"]
        return None

    def get_fid_next(self) -> Optional[int]:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return None

        results = self._inbox_fids()
        is_next = False

        if isinstance(results, list):
            for info in results:
                if is_next:
                    return info["fid"]
                if info["fid"] == self.dbdata["fid"]:
                    is_next = True
        return None

    def _inbox_fids(self) -> List[Dict[str, Any]]:
        """Visible inbox fids, newest first, as ``[{"fid": n}]``."""
        if self._orm:
            return [{"fid": f} for f in archive_orm.inbox_fids(self.db, self._route_filters)]
        results = self.faxarchive.query(
            f"SELECT fid FROM FaxArchive WHERE inbox = 1 {self.sqlroutes} ORDER BY fid DESC", reduce_single=False)
        return results if isinstance(results, list) else []

    def search_archive(self, criteria: Dict[str, Any]) -> int:
        if self._orm:
            numrows, self.archive_results = archive_orm.search(self.db, criteria)
            return numrows
        enable_did_routing = criteria.get("enable_did_routing", False)
        restricted_user_mode = criteria.get("restricted_user_mode", False)
        superuser = criteria.get("superuser", False)

        start_date = criteria.get("start_date")
        end_date = criteria.get("end_date")
        keywords = criteria.get("keywords")
        companyid = criteria.get("companyid")
        sentrecvd = criteria.get("sentrecvd")
        category = criteria.get("category")
        faxid = criteria.get("faxid")
        userid = criteria.get("userid")
        categories = criteria.get("categories")
        modemdevs = criteria.get("modemdevs")
        didroutes = criteria.get("didroutes")
        pagelimit = criteria.get("pagelimit", 25)
        pageindex = criteria.get("pageindex", 0)

        query = (
            "SELECT FaxArchive.fid FROM FaxArchive "
            "LEFT JOIN AddressBookFAX ON (FaxArchive.faxnumid = AddressBookFAX.abookfax_id) "
            "WHERE inbox = 0 "
        )

        query_didroutes = self._prepare_routes_clause("didr_id", didroutes)
        query_categories = self._prepare_routes_clause("FaxArchive.faxcatid", categories)
        query_modemdevs = self._prepare_routes_clause("modemdev", modemdevs)
        query_category = self.faxarchive.quote(category) if category else None
        query_userid = self.faxarchive.quote(userid) if userid else None

        if query_didroutes == "didr_id = ''":
            query_didroutes = "didr_id = 'X'"

        if sentrecvd == "s":
            if userid:
                query += f" AND userid = {query_userid} "
            else:
                query += " AND userid is not null "
            query += " AND modemdev is null "

        elif sentrecvd == "r":
            if enable_did_routing:
                if not superuser:
                    if category:
                        if query_didroutes:
                            query += f" AND ({query_didroutes})"
                    else:
                        if query_didroutes and query_categories:
                            op = "AND" if restricted_user_mode else "OR"
                            query += (
                                f" AND ((({query_didroutes}) {op} ({query_categories})) "
                                f"OR (({query_didroutes}) AND FaxArchive.faxcatid is null))"
                            )
                        elif not query_didroutes and query_categories:
                            query += f" AND ({query_categories})"
                        elif query_didroutes and not query_categories:
                            query += f" AND ({query_didroutes})"
                else:
                    query += " AND modemdev is not null "
            else:
                if not superuser:
                    if category:
                        if query_modemdevs:
                            query += f" AND ({query_modemdevs})"
                    else:
                        if query_modemdevs and query_categories:
                            op = "AND" if restricted_user_mode else "OR"
                            query += (
                                f" AND ((({query_modemdevs}) {op} ({query_categories})) "
                                f"OR (({query_modemdevs}) AND FaxArchive.faxcatid is null))"
                            )
                        elif not query_modemdevs and query_categories:
                            query += f" AND ({query_categories})"
                        elif query_modemdevs and not query_categories:
                            query += f" AND ({query_modemdevs})"
                else:
                    query += " AND modemdev is not null "

            if category:
                query += f" AND FaxArchive.faxcatid = {query_category} "
            query += " AND (userid = 0 OR userid is null) "

        elif sentrecvd == "*":
            target_routes = query_didroutes if enable_did_routing else query_modemdevs
            if not superuser:
                if category:
                    if target_routes:
                        query += f" AND ({target_routes} OR userid = {query_userid})"
                else:
                    if target_routes and query_categories:
                        op = "AND" if restricted_user_mode else "OR"
                        query += (
                            f" AND ((({target_routes}) {op} ({query_categories})) "
                            f"OR (({target_routes}) AND FaxArchive.faxcatid is null) OR userid = {query_userid})"
                        )
                    elif not target_routes and query_categories:
                        query += f" AND ({query_categories} OR userid = {query_userid})"
                    elif target_routes and not query_categories:
                        query += f" AND ({target_routes} OR userid = {query_userid})"
            else:
                if userid:
                    query += f" AND userid = {query_userid} "

            if category:
                query += f" AND FaxArchive.faxcatid = {query_category} "

        else:
            target_routes = query_didroutes if enable_did_routing else query_modemdevs
            if not superuser:
                query += f" AND ({target_routes} OR userid = {query_userid}) "
            else:
                if userid:
                    query += f" AND userid = {query_userid} "

        if start_date and end_date:
            qs = self.faxarchive.quote(str(start_date))
            qe = self.faxarchive.quote(str(end_date))
            query += f" AND (archstamp > {qs} AND archstamp < {qe}) "
        elif start_date:
            qs = self.faxarchive.quote(f"{start_date}%")
            query += f" AND archstamp LIKE {qs} "

        if faxid:
            query += f" AND FaxArchive.fid = {self.faxarchive.quote(faxid)}"

        if keywords:
            kw = str(keywords).strip().replace(" ", "%")
            qkw = self.faxarchive.quote(f"%{kw}%")
            query += (
                f" AND (FaxArchive.description LIKE {qkw} "
                f" OR FaxArchive.faxcontent LIKE {qkw}) "
            )

        if companyid:
            qcid = self.faxarchive.quote(companyid)
            query += f" AND (AddressBookFAX.abook_id = {qcid} OR FaxArchive.companyid = {qcid}) "

        query += " ORDER BY fid DESC"

        all_rows = self.faxarchive.query(query, reduce_single=False)
        numrows = len(all_rows) if isinstance(all_rows, list) else 0

        numpages = math.ceil(numrows / pagelimit) if numrows > pagelimit else 0
        if pageindex > (numpages - 1):
            pageindex = max(0, numpages - 1)
        if pageindex < 0:
            pageindex = 0

        offset = pageindex * pagelimit
        query += f" LIMIT {offset}, {pagelimit}"

        self.archive_results = self.faxarchive.query(query, reduce_single=False)
        return numrows

    def _prepare_routes_clause(self, col: str, items: Any) -> Optional[str]:
        if items is None:
            return None
        if not isinstance(items, list):
            items = [items]
        if not items:
            return None
        clauses = [f"{col} = {self.faxarchive.quote(x)}" for x in items if x is not None]
        return " OR ".join(clauses) if clauses else None

    def next_archive_entry(self) -> Optional[int]:
        if isinstance(self.archive_results, list) and self.archive_results:
            row = self.archive_results.pop(0)
            return row.get("fid")
        self.archive_results = None
        return None

    def list_inbox(
        self,
        devices: Optional[List[Any]] = None,
        index: int = 0,
        limit: int = 25,
        faxcats: Optional[List[Any]] = None,
        enable_did_routing: bool = False,
        order_by_modem: bool = False,
    ) -> List[Dict[str, Any]]:
        self.viewable_devices(devices, faxcats, enable_did_routing)
        order_by = "modemdev, fid DESC" if order_by_modem else "fid DESC"
        if index < 0:
            index = 0
        offset = index * limit

        if self._orm:
            rows = archive_orm.list_inbox(self.db, self._route_filters, offset, limit, order_by_modem)
        else:
            query = f"SELECT FaxArchive.* FROM FaxArchive WHERE inbox = 1 {self.sqlroutes} ORDER BY {order_by} LIMIT {offset}, {limit}"
            rows = self.faxarchive.query(query, reduce_single=False)
        if not isinstance(rows, list):
            return []

        for r in rows:
            self._format_row_dates(r)
        return rows

    def load_fax(self, faxid: int) -> bool:
        if not faxid:
            self.error = "No faxid to load"
            return False

        row = self.faxarchive.find({"fid": faxid}, reduce_single=True)
        if isinstance(row, dict):
            self.load_vals(row)
            return True
        elif isinstance(row, list) and row:
            self.load_vals(row[0])
            return True

        self.error = f"load_fax error: {faxid} didn't load"
        return False

    def set_category(self, catid: Optional[int], userid: int = 0) -> bool:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        self.dbdata["faxcatid"] = catid
        self.dbdata["lastmoduser"] = userid
        return bool(self.faxarchive.update_entry(self.dbdata))

    def remove_category(self, catid: int) -> bool:
        if not catid:
            self.error = "No valid catid sent"
            return False

        self.faxarchive.update_where({"faxcatid": catid}, {"faxcatid": None})
        return True

    def set_note(self, description: str, category: Optional[int], userid: int) -> bool:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        self.dbdata["faxcatid"] = category
        self.dbdata["description"] = description
        self.dbdata["lastmoduser"] = userid
        self.dbdata["lastmoddate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.faxarchive.update_entry(self.dbdata)
        return True

    def set_faxcontent(self, faxcontent: str) -> bool:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        self.dbdata["faxcontent"] = faxcontent
        self.faxarchive.update_entry(self.dbdata)
        return True

    def delete_fax(self, fid: Optional[int] = None) -> bool:
        if fid:
            if not self.load_fax(fid):
                self.error = "Invalid fid"
                return False
        elif "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        # Delete database entry
        self.faxarchive.delete_entry({"fid": self.dbdata["fid"]})

        # Remove preview images
        faxpath = self.dbdata.get("faxpath", "")
        pages = self.dbdata.get("pages") or 0
        if self.dbdata.get("inbox"):
            for i in range(pages):
                img_path = os.path.join(self._on_disk(faxpath), f"{PREVIMG}{i}{PREVIMGSFX}")
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except OSError:
                        pass

        # Remove thumbnail, tiff, pdf
        for fpath in [self.thumbnail, self.tiffpath, self.pdfpath]:
            if fpath:
                full_p = self._on_disk(fpath)
                if os.path.exists(full_p):
                    try:
                        os.remove(full_p)
                    except OSError:
                        pass

        # Remove directory if empty
        if faxpath:
            full_dir = self._on_disk(faxpath)
            if os.path.exists(full_dir):
                try:
                    os.rmdir(full_dir)
                except OSError:
                    pass

        return True

    def _on_disk(self, path: str) -> str:
        """The file system location of a stored path.

        With an install directory the stored path is relative to it. Without one (faxrcvd stores the
        absolute archive path) it is used as it is; joining it onto an empty directory turned
        ``/var/spool/...`` into the relative ``var/spool/...``, so deleting a fax never removed its files.
        """
        return os.path.join(self.installdir, path.lstrip("/")) if self.installdir else path

    def prune_archive(self, days: int) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")
        count = 0
        for fid in self._fids_older_than(cutoff):
            if fid:
                self.delete_fax(fid)
                count += 1
        return count

    def _fids_older_than(self, cutoff: str, inbox: Optional[int] = None) -> List[int]:
        if self._orm:
            return archive_orm.fids_older_than(self.db, cutoff, inbox)
        where = f"archstamp < {self.faxarchive.quote(cutoff)}" + (f" AND inbox = {int(inbox)}" if inbox is not None else "")
        results = self.faxarchive.query(f"SELECT fid FROM FaxArchive WHERE {where}", reduce_single=False)
        return [r.get("fid") for r in results] if isinstance(results, list) else []

    def set_faxnumid(self, id: int) -> bool:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        self.dbdata["faxnumid"] = id
        if not self.faxarchive.update_entry(self.dbdata):
            self.error = "faxnumid not updated"
            return False
        return True

    def set_companyid(self, id: int) -> bool:
        if "fid" not in self.dbdata:
            self.error = "No fid loaded"
            return False

        self.dbdata["companyid"] = id
        if not self.faxarchive.update_entry(self.dbdata):
            self.error = "companyid not updated"
            return False
        return True

    def reassign(self, oldcid: int, newcid: int) -> bool:
        if not newcid or not oldcid:
            return False

        self.faxarchive.update_where({"companyid": oldcid}, {"companyid": newcid})
        return True

    def create_fax(
        self,
        path: str,
        faxnid: int,
        faxnumber: str,
        pages: int,
        date: Optional[str] = None,
        didr_id: Optional[int] = None,
    ) -> bool:
        # Normalize relative path from installdir
        rel_path = path
        if self.installdir and path.startswith(self.installdir):
            rel_path = path[len(self.installdir) :]

        self.dbdata = {
            "faxpath": rel_path,
            "faxnumid": faxnid,
            "origfaxnum": clean_faxnum(faxnumber),
            "pages": pages,
            "didr_id": didr_id,
            "archstamp": date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self.faxarchive.new_entry(self.dbdata):
            self.dbdata["fid"] = self.faxarchive.get_id()
            self.load_vals(self.dbdata)
            return True

        self.error = "No id created"
        return False

    def load_vals(self, data: Dict[str, Any]) -> None:
        raw = dict(data)
        self._format_row_dates(raw)
        self.m_archstamp = raw.pop("m_archstamp", None)
        self.m_lastmoddate = raw.pop("m_lastmoddate", None)
        self.m_lastoperation = raw.pop("m_lastoperation", None)

        self.dbdata = raw
        faxpath = self.dbdata.get("faxpath") or ""

        self.pdfpath = os.path.join(faxpath, PDFNAME)
        self.thumbnail = os.path.join(faxpath, THUMBNAIL)
        self.tiffpath = os.path.join(faxpath, TIFFNAME)

        self.faximages = []
        pages = self.dbdata.get("pages") or 0
        for i in range(pages):
            self.faximages.append(os.path.join(faxpath, f"{PREVIMG}{i}{PREVIMGSFX}"))

    def _format_row_dates(self, row: Dict[str, Any]) -> None:
        for col in ["archstamp", "lastmoddate", "lastoperation"]:
            val = row.get(col)
            formatted = None
            if val:
                val_str = str(val)
                try:
                    dt = datetime.fromisoformat(val_str)
                    formatted = dt.strftime(self.date_format)
                except ValueError:
                    formatted = val_str[:16]
            row[f"m_{col}"] = formatted

    # Getters
    def get_fid(self) -> Optional[int]:
        return self.dbdata.get("fid")

    def get_userid(self) -> Optional[int]:
        return self.dbdata.get("userid")

    def get_description(self) -> Optional[str]:
        return self.dbdata.get("description")

    def get_lastmoduser(self) -> Optional[int]:
        return self.dbdata.get("lastmoduser")

    def get_faxnumid(self) -> Optional[int]:
        return self.dbdata.get("faxnumid")

    def get_origfaxnum(self) -> Optional[str]:
        return self.dbdata.get("origfaxnum")

    def get_pages(self) -> Optional[int]:
        return self.dbdata.get("pages")

    def get_inbox(self) -> Optional[int]:
        return self.dbdata.get("inbox")

    def get_companyid(self) -> Optional[int]:
        return self.dbdata.get("companyid")

    def get_didr_id(self) -> Optional[int]:
        return self.dbdata.get("didr_id")

    def get_modemdev(self) -> Optional[str]:
        return self.dbdata.get("modemdev")

    def get_tiffpath(self) -> Optional[str]:
        return self.tiffpath

    def get_pdfpath(self) -> Optional[str]:
        return self.pdfpath

    def get_thumbnail(self) -> Optional[str]:
        return self.thumbnail

    def get_faximages(self) -> List[str]:
        return self.faximages

    def get_archstamp(self) -> Optional[str]:
        return self.m_archstamp

    def get_lastmoddate(self) -> Optional[str]:
        return self.m_lastmoddate
