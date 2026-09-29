#!/usr/bin/env python3
"""CLI Bridge for calling modern DatabaseEngine from legacy PHP or external processes."""

import json
import os
import sys

# Ensure src/ directory is available in sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from avantfax.db.engine import DatabaseEngine, SQL_ALL, SQL_NONE

_GLOBAL_ENGINE = DatabaseEngine()
if os.environ.get("AVANTFAX_DB_FILE"):
    _GLOBAL_ENGINE.connect_sqlite(os.environ["AVANTFAX_DB_FILE"])


def handle_request(req: dict) -> dict:
    action = req.get("action")
    
    if action == "connect":
        engine_type = req.get("engine", "sqlite")
        if engine_type == "sqlite":
            success = _GLOBAL_ENGINE.connect_sqlite(req.get("database", ":memory:"))
        else:
            success = _GLOBAL_ENGINE.connect(
                db_user=req.get("user", ""),
                db_pass=req.get("password", ""),
                db_name=req.get("database", ""),
                db_host=req.get("host", "localhost"),
                db_engine=engine_type,
            )
        return {"success": success, "error": _GLOBAL_ENGINE.get_error()}

    elif action == "query":
        sql = req.get("sql", "")
        params = req.get("params")
        fetch_type = SQL_ALL if req.get("fetch_all") else SQL_NONE
        res = _GLOBAL_ENGINE.query(sql, params=params, fetch_type=fetch_type)
        return {
            "executed": res.executed,
            "row_count": res.row_count,
            "affected_rows": res.affected_rows,
            "insert_id": _GLOBAL_ENGINE.get_insert_id(),
            "records": _GLOBAL_ENGINE.get_records(),
            "error": _GLOBAL_ENGINE.get_error(),
        }

    elif action == "insert":
        from avantfax.db.query import QueryBuilder
        qb = QueryBuilder(_GLOBAL_ENGINE)
        insert_id = qb.insert(req.get("table"), req.get("data", {}), req.get("id_col"))
        return {"insert_id": insert_id, "error": _GLOBAL_ENGINE.get_error()}

    elif action == "update":
        from avantfax.db.query import QueryBuilder
        qb = QueryBuilder(_GLOBAL_ENGINE)
        success = qb.update(req.get("table"), req.get("data", {}), req.get("where", {}))
        return {"success": success, "error": _GLOBAL_ENGINE.get_error()}

    elif action == "get":
        from avantfax.db.query import QueryBuilder
        qb = QueryBuilder(_GLOBAL_ENGINE)
        record = qb.get(req.get("table"), req.get("id_col"), req.get("id_val"))
        return {"record": record, "error": _GLOBAL_ENGINE.get_error()}

    elif action == "find":
        from avantfax.db.query import QueryBuilder
        qb = QueryBuilder(_GLOBAL_ENGINE)
        records = qb.find(
            table=req.get("table"),
            conditions=req.get("conditions"),
            logic=req.get("logic", " AND "),
            limit=req.get("limit"),
            offset=req.get("offset"),
            reduce_single=req.get("reduce_single", True),
        )
        return {"records": records, "num_results": qb.num_results, "error": _GLOBAL_ENGINE.get_error()}

    elif action == "delete":
        from avantfax.db.query import QueryBuilder
        qb = QueryBuilder(_GLOBAL_ENGINE)
        success = qb.delete(req.get("table"), req.get("id_col"), req.get("id_val"))
        return {"success": success, "error": _GLOBAL_ENGINE.get_error()}

    elif action == "quote":
        from avantfax.db.query import QueryBuilder
        qb = QueryBuilder(_GLOBAL_ENGINE)
        val = req.get("value")
        return {"quoted": qb.quote(val)}

    elif action == "validate_email":
        from avantfax.common.validators import is_valid_email
        email = req.get("email", "")
        return {"valid": is_valid_email(email)}

    elif action == "validate_form":
        from avantfax.common.validators import FormRules
        fr = FormRules()
        for r in req.get("rules", []):
            fr.new_rule(
                varname=r["varname"],
                defaultval=r.get("defaultval"),
                vartype=r.get("vartype", 11),
                minlen=r.get("minlen"),
                maxlen=r.get("maxlen"),
                error_str=r.get("error_str"),
                required=r.get("required", False),
                sanitize=r.get("sanitize", True),
            )
        valid = fr.process_form(req.get("data", {}))
        return {
            "valid": valid,
            "errors": fr.get_form_errors(),
            "css_errors": fr.get_css_error_ids(),
            "html_ready": fr.html_ready(),
            "db_ready": fr.db_ready(),
        }

    elif action == "auth_pwauth":
        from avantfax.auth.password import PWAuthBackend
        backend = PWAuthBackend(binary_path=req.get("binary_path", "/usr/local/bin/pwauth"))
        success = backend.login(req.get("username", ""), req.get("password", ""))
        return {"success": success, "error": backend.last_error}

    elif action == "auth_pam":
        from avantfax.auth.pam import PAMAuthBackend
        backend = PAMAuthBackend()
        success = backend.login(req.get("username", ""), req.get("password", ""), service=req.get("service", "login"))
        return {"success": success, "error": backend.last_error}

    elif action == "hash_password":
        from avantfax.auth.password import PasswordManager
        h = PasswordManager.hash_password(req.get("password", ""))
        return {"hash": h}

    elif action == "verify_password":
        from avantfax.auth.password import PasswordManager
        matched = PasswordManager.verify_password(req.get("plain", ""), req.get("hash", ""))
        return {"matched": matched}

    elif action == "upload_sanitize_filename":
        from avantfax.common.upload import FileUpload
        fu = FileUpload()
        return {"clean": fu.sanitize_filename(req.get("filename", ""))}

    elif action == "upload_process":
        from avantfax.common.upload import FileUpload
        fu = FileUpload()
        if req.get("mimelimit"):
            fu.limit_mimetype(req["mimelimit"])
        if req.get("sizelimit"):
            fu.limit_size(req["sizelimit"])
        success = fu.load_file(req.get("file_info", {}))
        if success and req.get("randname"):
            fu.set_randname(req.get("randname_len", 9))
        moved = False
        if success and req.get("dest_dir"):
            moved = fu.movefile(req["dest_dir"])
        return {
            "success": success,
            "error": fu.get_error(),
            "name": fu.get_name(),
            "mimetype": fu.get_mimetype(),
            "size": fu.get_filesize(),
            "moved": moved,
        }

    elif action == "mailer_send":
        from avantfax.services.mailer import MailerService
        mailer = MailerService(
            smtp_server=req.get("smtp_server"),
            smtp_port=req.get("smtp_port", 25),
            smtp_user=req.get("smtp_user"),
            smtp_password=req.get("smtp_password"),
            use_ssl=req.get("use_ssl", False),
            use_tls=req.get("use_tls", False),
            admin_email=req.get("admin_email", "root@localhost"),
            email_sig_text=req.get("email_sig_text", ""),
            email_sig_html=req.get("email_sig_html", ""),
            spool_mode=req.get("spool_mode", False),
        )
        mailer.set_message(req.get("text", ""), subject=req.get("subject"))
        for att in req.get("attachments", []):
            mailer.attach_file(att["file"], alt_name=att.get("altname"))
        for img in req.get("images", []):
            mailer.embed_image(img["file"], cid=img.get("cid"))
        success = mailer.sendmail(req.get("to", ""), subject=req.get("subject"))
        return {"success": success, "error": mailer.get_error()}

    elif action == "covers":
        from avantfax.services.covers import Covers
        c = Covers(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "create":
            ok = c.create(req.get("title"), req.get("file"))
            return {"success": ok, "cover_id": c.get_cover_id(), "error": c.error}
        elif method == "delete":
            ok = c.delete_cover(req.get("cover_id"))
            return {"success": ok, "error": c.error}
        elif method == "get_covers":
            covers_list = c.get_covers()
            return {"covers": covers_list, "error": c.error}
        elif method == "list_all":
            return {"covers": c.list_all(), "error": c.error}
        elif method == "load":
            ok = c.load_cover(req.get("file"))
            return {
                "success": ok,
                "cover_id": c.get_cover_id(),
                "title": c.get_title(),
                "file": c.get_file(),
                "all_data": c.all_data,
                "error": c.error,
            }
        elif method == "set_title":
            if c.load_cover(req.get("file")):
                ok = c.set_title(req.get("title"))
                return {"success": ok, "error": c.error}
            return {"success": False, "error": c.error}
        elif method == "set_file":
            if c.load_cover(req.get("old_file")):
                ok = c.set_file(req.get("new_file"))
                return {"success": ok, "error": c.error}
            return {"success": False, "error": c.error}
        return {"error": f"Unknown covers method: {method}"}

    elif action == "categories":
        from avantfax.services.categories import FaxPDFCategory
        cat = FaxPDFCategory(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "create":
            ok = cat.create(req.get("name"))
            return {"success": ok, "error": cat.get_error()}
        elif method == "set_name":
            ok = cat.set_name(req.get("name"), req.get("catid"))
            return {"success": ok, "error": cat.get_error()}
        elif method == "get_name":
            name = cat.get_name(req.get("catid"))
            return {"name": name, "error": cat.get_error()}
        elif method == "get_categories":
            return {"categories": cat.get_categories(), "error": cat.get_error()}
        elif method == "delete":
            ok = cat.delete_category(req.get("catid"))
            return {"success": ok, "error": cat.get_error()}
        return {"error": f"Unknown categories method: {method}"}

    elif action == "user_passwords":
        from avantfax.services.user_passwords import AFUserPasswords
        up = AFUserPasswords(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "log_password":
            ok = up.log_password(req.get("pwd"), req.get("uid"))
            return {"success": ok}
        elif method == "password_used":
            used = up.password_used(req.get("pwd"), req.get("uid"))
            return {"used": used}
        elif method == "clear_hashes":
            ok = up.clear_hashes(req.get("uid"))
            return {"success": ok}
        return {"error": f"Unknown user_passwords method: {method}"}

    elif action == "dynconf":
        from avantfax.services.dynconf import DynamicConfig
        dc = DynamicConfig(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "lookup":
            match = dc.lookup(req.get("device"), req.get("callid"))
            return {"match": match}
        elif method == "list_rules":
            return {"rules": dc.list_rules()}
        elif method == "create":
            ok = dc.create(req.get("device"), req.get("callid"))
            return {"success": ok, "dynconf_id": dc.get_dynconf_id(), "error": dc.get_error()}
        elif method == "load":
            ok = dc.load_rule(req.get("id"))
            return {
                "success": ok,
                "dynconf_id": dc.get_dynconf_id(),
                "device": dc.get_device(),
                "callid": dc.get_callid(),
                "error": dc.get_error(),
            }
        elif method == "save":
            if dc.load_rule(req.get("id")):
                ok = dc.save_rule(req.get("device"), req.get("callid"))
                return {"success": ok, "error": dc.get_error()}
            return {"success": False, "error": dc.get_error()}
        elif method == "remove":
            ok = dc.remove(req.get("id"))
            return {"success": ok, "error": dc.get_error()}
        return {"error": f"Unknown dynconf method: {method}"}

    elif action == "barcode":
        from avantfax.services.barcode import BarcodeRouting
        bc = BarcodeRouting(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "create":
            ok = bc.create(
                barcode=req.get("barcode"),
                alias=req.get("alias"),
                contact=req.get("contact"),
                printer=req.get("printer"),
                faxcatid=req.get("faxcatid"),
            )
            return {"success": ok, "barcode_id": bc.get_barcode_id(), "error": bc.get_error()}
        elif method == "delete":
            ok = bc.delete_route(req.get("barcode_id"))
            return {"success": ok, "error": bc.get_error()}
        elif method == "get_routes":
            return {"routes": bc.get_routes(), "error": bc.get_error()}
        elif method == "list_all":
            return {"routes": bc.list_all()}
        elif method == "load_route":
            ok = bc.load_route(req.get("barcode"))
            return {
                "success": ok,
                "barcode_id": bc.get_barcode_id(),
                "alias": bc.get_alias(),
                "barcode": bc.get_barcode(),
                "contact": bc.get_contact(),
                "printer": bc.get_printer(),
                "faxcatid": bc.get_faxcatid(),
                "error": bc.get_error(),
            }
        elif method == "loadbyid":
            ok = bc.loadbyid(req.get("barcode_id"))
            return {
                "success": ok,
                "barcode_id": bc.get_barcode_id(),
                "alias": bc.get_alias(),
                "barcode": bc.get_barcode(),
                "contact": bc.get_contact(),
                "printer": bc.get_printer(),
                "faxcatid": bc.get_faxcatid(),
                "error": bc.get_error(),
            }
        elif method == "update":
            if bc.loadbyid(req.get("barcode_id")):
                field = req.get("field")
                val = req.get("value")
                if field == "alias":
                    ok = bc.set_alias(val)
                elif field == "barcode":
                    ok = bc.set_barcode(val)
                elif field == "contact":
                    ok = bc.set_contact(val)
                elif field == "printer":
                    ok = bc.set_printer(val)
                elif field == "faxcatid":
                    ok = bc.set_faxcatid(val)
                else:
                    return {"success": False, "error": f"Unknown field: {field}"}
                return {"success": ok, "error": bc.get_error()}
            return {"success": False, "error": bc.get_error()}
        return {"error": f"Unknown barcode method: {method}"}

    elif action == "did":
        from avantfax.services.did import DIDRouting
        did = DIDRouting(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "create":
            ok = did.create(
                route=req.get("route"),
                alias=req.get("alias"),
                contact=req.get("contact"),
                printer=req.get("printer"),
                faxcatid=req.get("faxcatid"),
            )
            return {"success": ok, "didr_id": did.get_didr_id(), "error": did.get_error()}
        elif method == "delete":
            ok = did.delete_route(req.get("didr_id"))
            return {"success": ok, "error": did.get_error()}
        elif method == "get_routes":
            return {"routes": did.get_routes(), "error": did.get_error()}
        elif method == "list_all":
            return {"routes": did.list_all()}
        elif method == "load_route":
            ok = did.load_route(req.get("route"))
            return {
                "success": ok,
                "didr_id": did.get_didr_id(),
                "alias": did.get_alias(),
                "routecode": did.get_route(),
                "contact": did.get_contact(),
                "printer": did.get_printer(),
                "faxcatid": did.get_faxcatid(),
                "error": did.get_error(),
            }
        elif method == "loadbyid":
            ok = did.loadbyid(req.get("didr_id"))
            return {
                "success": ok,
                "didr_id": did.get_didr_id(),
                "alias": did.get_alias(),
                "routecode": did.get_route(),
                "contact": did.get_contact(),
                "printer": did.get_printer(),
                "faxcatid": did.get_faxcatid(),
                "error": did.get_error(),
            }
        elif method == "update":
            if did.loadbyid(req.get("didr_id")):
                field = req.get("field")
                val = req.get("value")
                if field == "alias":
                    ok = did.set_alias(val)
                elif field == "routecode":
                    ok = did.set_routecode(val)
                elif field == "contact":
                    ok = did.set_contact(val)
                elif field == "printer":
                    ok = did.set_printer(val)
                elif field == "faxcatid":
                    ok = did.set_faxcatid(val)
                else:
                    return {"success": False, "error": f"Unknown field: {field}"}
                return {"success": ok, "error": did.get_error()}
            return {"success": False, "error": did.get_error()}
        return {"error": f"Unknown did method: {method}"}

    elif action == "distro":
        from avantfax.services.distro import DistributionList
        dl = DistributionList(db=_GLOBAL_ENGINE)
        method = req.get("method")
        user = req.get("user")
        if user is not None:
            dl.set_moduser(user)

        if method == "create":
            ok = dl.create(req.get("listname"))
            return {"success": ok, "dl_id": dl.get_dl_id(), "error": dl.get_error()}
        elif method == "delete":
            ok = dl.delete_list(req.get("list_id"))
            return {"success": ok, "error": dl.get_error()}
        elif method == "get_distrolists":
            return {"lists": dl.get_distrolists(), "error": dl.get_error()}
        elif method == "load":
            ok = dl.load_list(req.get("list_id"))
            return {
                "success": ok,
                "dl_id": dl.get_dl_id(),
                "listname": dl.get_listname(),
                "lastmod": dl.get_lastmod(),
                "entries": dl.list_entries(),
                "error": dl.get_error(),
            }
        elif method == "set_listname":
            if dl.load_list(req.get("list_id")):
                ok = dl.set_listname(req.get("listname"))
                return {"success": ok, "error": dl.get_error()}
            return {"success": False, "error": dl.get_error()}
        elif method == "list_entries":
            if dl.load_list(req.get("list_id")):
                return {"entries": dl.list_entries(), "error": dl.get_error()}
            return {"entries": [], "error": dl.get_error()}
        elif method == "add_entries":
            if dl.load_list(req.get("list_id")):
                ok = dl.add_entries(req.get("entries", []))
                return {"success": ok, "entries": dl.list_entries(), "error": dl.get_error()}
            return {"success": False, "error": dl.get_error()}
        elif method == "remove_entries":
            if dl.load_list(req.get("list_id")):
                ok = dl.remove_entries(req.get("entries", []))
                return {"success": ok, "entries": dl.list_entries(), "error": dl.get_error()}
            return {"success": False, "error": dl.get_error()}
        return {"error": f"Unknown distro method: {method}"}

    elif action == "modem":
        from avantfax.services.modem import FaxModem
        fm = FaxModem(db=_GLOBAL_ENGINE)
        method = req.get("method")
        if method == "create":
            ok = fm.create(
                device=req.get("device"),
                alias=req.get("alias"),
                contact=req.get("contact"),
                printer=req.get("printer"),
                faxcatid=req.get("faxcatid"),
            )
            return {"success": ok, "devid": fm.get_devid(), "error": fm.get_error()}
        elif method == "delete":
            ok = fm.delete_device(req.get("device"))
            return {"success": ok, "error": fm.get_error()}
        elif method == "get_modems":
            return {"modems": fm.get_modems(), "error": fm.get_error()}
        elif method == "list_all":
            return {"modems": fm.list_all()}
        elif method == "load":
            ok = fm.load_device(req.get("device"))
            return {
                "success": ok,
                "devid": fm.get_devid(),
                "alias": fm.get_alias(),
                "device": fm.get_device(),
                "contact": fm.get_contact(),
                "printer": fm.get_printer(),
                "faxcatid": fm.get_faxcatid(),
                "error": fm.get_error(),
            }
        elif method == "loadbyid":
            ok = fm.loadbyid(req.get("devid"))
            return {
                "success": ok,
                "devid": fm.get_devid(),
                "alias": fm.get_alias(),
                "device": fm.get_device(),
                "contact": fm.get_contact(),
                "printer": fm.get_printer(),
                "faxcatid": fm.get_faxcatid(),
                "error": fm.get_error(),
            }
        elif method == "get_status":
            if fm.load_device(req.get("device")):
                return {"status": fm.get_status(req.get("raw_output"))}
            return {"status": {"class": "modem-wait", "status": "Please wait"}}
        elif method == "update":
            if fm.loadbyid(req.get("devid")):
                field = req.get("field")
                val = req.get("value")
                if field == "alias":
                    ok = fm.set_alias(val)
                elif field == "contact":
                    ok = fm.set_contact(val)
                elif field == "printer":
                    ok = fm.set_printer(val)
                elif field == "faxcatid":
                    ok = fm.set_faxcatid(val)
                else:
                    return {"success": False, "error": f"Unknown field: {field}"}
                return {"success": ok, "error": fm.get_error()}
            return {"success": False, "error": fm.get_error()}
        return {"error": f"Unknown modem method: {method}"}

    elif action == "abook":
        from avantfax.services.addressbook import AFAddressBook
        ab = AFAddressBook(db=_GLOBAL_ENGINE)
        method = req.get("method")
        cid = req.get("cid")
        if cid:
            ab.loadbycid(cid)

        if method == "create":
            ok = ab.create(req.get("company"))
            return {"success": ok, "abook_id": ab.get_companyid(), "error": ab.get_error()}
        elif method == "loadbycid":
            ok = ab.loadbycid(req.get("cid"))
            return {"success": ok, "abook_id": ab.get_companyid(), "company": ab.get_company(), "error": ab.get_error()}
        elif method == "get_companies":
            return {"companies": ab.get_companies(req.get("with_reserved", False)), "error": ab.get_error()}
        elif method == "search_companies":
            return {"companies": ab.search_companies(req.get("query", "")), "error": ab.get_error()}
        elif method == "delete_cid":
            ok = ab.delete_cid(req.get("cid"))
            return {"success": ok, "error": ab.get_error()}
        elif method == "create_faxnumid":
            ok = ab.create_faxnumid(req.get("faxnumber"))
            return {"success": ok, "abookfax_id": ab.get_faxnumid(), "error": ab.get_error()}
        elif method == "loadbyfaxnum":
            ok, mult = ab.loadbyfaxnum(req.get("faxnumber"))
            return {
                "success": ok,
                "multiple": mult,
                "abookfax_id": ab.get_faxnumid(),
                "company": ab.get_company(),
                "error": ab.get_error(),
            }
        elif method == "loadbyfaxnumid":
            ok = ab.loadbyfaxnumid(req.get("abookfax_id"))
            return {
                "success": ok,
                "abookfax_id": ab.get_faxnumid(),
                "faxnumber": ab.get_faxnumber(),
                "company": ab.get_company(),
                "error": ab.get_error(),
            }
        elif method == "save_settings":
            if ab.loadbyfaxnumid(req.get("abookfax_id")):
                ok = ab.save_settings(req.get("data", {}))
                return {"success": ok, "error": ab.get_error()}
            return {"success": False, "error": ab.get_error()}
        elif method == "create_contact":
            ok = ab.create_contact(req.get("name"), req.get("email"))
            return {"success": ok, "error": ab.get_error()}
        elif method == "get_contacts":
            return {"contacts": ab.get_contacts(), "error": ab.get_error()}
        elif method == "remove_contact":
            ok = ab.remove_contact(req.get("abookemail_id"))
            return {"success": ok, "error": ab.get_error()}
        return {"error": f"Unknown abook method: {method}"}

    elif action == "archive_base":
        from avantfax.services.archive_base import FaxPDFArchive
        archive = FaxPDFArchive(db=_GLOBAL_ENGINE, installdir=req.get("installdir", ""))
        method = req.get("method")
        fid = req.get("fid")
        if fid:
            archive.load_fax(fid)

        if method == "create_fax":
            ok = archive.create_fax(
                path=req.get("path", ""),
                faxnid=req.get("faxnid", 0),
                faxnumber=req.get("faxnumber", ""),
                pages=req.get("pages", 1),
                date=req.get("date"),
                didr_id=req.get("didr_id"),
            )
            return {"success": ok, "fid": archive.get_fid(), "error": archive.get_error()}
        elif method == "load_fax":
            ok = archive.load_fax(req.get("faxid"))
            data = archive.dbdata if ok else {}
            return {
                "success": ok,
                "data": data,
                "fid": archive.get_fid(),
                "faxcatid": archive.get_faxcatid(),
                "description": archive.get_description(),
                "pages": archive.get_pages(),
                "companyid": archive.get_companyid(),
                "didr_id": archive.get_didr_id(),
                "modemdev": archive.get_modemdev(),
                "origfaxnum": archive.get_origfaxnum(),
                "tiffpath": archive.get_tiffpath(),
                "pdfpath": archive.get_pdfpath(),
                "thumbnail": archive.get_thumbnail(),
                "faximages": archive.get_faximages(),
                "archstamp": archive.get_archstamp(),
                "lastmoddate": archive.get_lastmoddate(),
                "error": archive.get_error(),
            }
        elif method == "get_num_faxes":
            count = archive.get_num_faxes(
                devices=req.get("devices"),
                faxcats=req.get("faxcats"),
                enable_did_routing=req.get("enable_did_routing", False),
            )
            return {"count": count, "error": archive.get_error()}
        elif method == "user_has_rights":
            ok = archive.user_has_rights(
                userid=req.get("userid", 0),
                modems=req.get("modems", []),
                routes=req.get("routes", []),
                faxcat=req.get("faxcat", []),
            )
            return {"has_rights": ok, "error": archive.get_error()}
        elif method == "get_fid_prev":
            archive.viewable_devices(req.get("devices"), req.get("faxcats"), req.get("enable_did_routing", False))
            return {"fid": archive.get_fid_prev(), "error": archive.get_error()}
        elif method == "get_fid_next":
            archive.viewable_devices(req.get("devices"), req.get("faxcats"), req.get("enable_did_routing", False))
            return {"fid": archive.get_fid_next(), "error": archive.get_error()}
        elif method == "search_archive":
            total = archive.search_archive(req.get("criteria", {}))
            entries = []
            while True:
                e = archive.next_archive_entry()
                if e is None:
                    break
                entries.append(e)
            return {"total": total, "entries": entries, "error": archive.get_error()}
        elif method == "list_inbox":
            items = archive.list_inbox(
                devices=req.get("devices"),
                index=req.get("index", 0),
                limit=req.get("limit", 25),
                faxcats=req.get("faxcats"),
                enable_did_routing=req.get("enable_did_routing", False),
                order_by_modem=req.get("order_by_modem", False),
            )
            return {"items": items, "error": archive.get_error()}
        elif method == "set_category":
            ok = archive.set_category(req.get("catid"), req.get("userid", 0))
            return {"success": ok, "error": archive.get_error()}
        elif method == "remove_category":
            ok = archive.remove_category(req.get("catid"))
            return {"success": ok, "error": archive.get_error()}
        elif method == "set_note":
            ok = archive.set_note(req.get("description", ""), req.get("category"), req.get("userid", 0))
            return {"success": ok, "error": archive.get_error()}
        elif method == "set_faxcontent":
            ok = archive.set_faxcontent(req.get("faxcontent", ""))
            return {"success": ok, "error": archive.get_error()}
        elif method == "delete_fax":
            ok = archive.delete_fax(req.get("fid"))
            return {"success": ok, "error": archive.get_error()}
        elif method == "prune_archive":
            pruned = archive.prune_archive(req.get("days", 0))
            return {"pruned": pruned, "error": archive.get_error()}
        elif method == "set_faxnumid":
            ok = archive.set_faxnumid(req.get("id"))
            return {"success": ok, "error": archive.get_error()}
        elif method == "set_companyid":
            ok = archive.set_companyid(req.get("id"))
            return {"success": ok, "error": archive.get_error()}
        elif method == "reassign":
            ok = archive.reassign(req.get("oldcid"), req.get("newcid"))
            return {"success": ok, "error": archive.get_error()}
        return {"error": f"Unknown archive_base method: {method}"}

    elif action == "user_account":
        from avantfax.services.user_account import AFUserAccount
        user_svc = AFUserAccount(db=_GLOBAL_ENGINE)
        method = req.get("method")
        uid = req.get("uid")
        if uid:
            user_svc.load(uid)

        if method == "create":
            ok = user_svc.create(req.get("details", {}))
            return {"success": ok, "uid": user_svc.get_uid(), "error": user_svc.get_error()}
        elif method == "load":
            ok = user_svc.load(req.get("userid"))
            return {"success": ok, "values": user_svc.get_allvalues(), "uid": user_svc.get_uid(), "error": user_svc.get_error()}
        elif method == "load_username":
            ok = user_svc.load_username(req.get("username"))
            return {"success": ok, "values": user_svc.get_allvalues(), "uid": user_svc.get_uid(), "error": user_svc.get_error()}
        elif method == "loadbyemail":
            ok = user_svc.loadbyemail(req.get("email"))
            return {"success": ok, "values": user_svc.get_allvalues(), "uid": user_svc.get_uid(), "error": user_svc.get_error()}
        elif method == "login":
            ok = user_svc.login(
                username=req.get("username", ""),
                password=req.get("password", ""),
                admin=req.get("admin", False),
                remote_ip=req.get("remote_ip", "127.0.0.1"),
            )
            return {
                "success": ok,
                "uid": user_svc.get_uid(),
                "values": user_svc.get_allvalues(),
                "is_expired": user_svc.is_expired(),
                "logged_in": user_svc.check_login(),
                "admin_logged_in": user_svc.check_admin_login(),
                "error": user_svc.get_error(),
            }
        elif method == "login_webauth":
            ok = user_svc.login_webauth(
                username=req.get("username", ""),
                admin=req.get("admin", False),
                remote_ip=req.get("remote_ip", "127.0.0.1"),
            )
            return {
                "success": ok,
                "uid": user_svc.get_uid(),
                "values": user_svc.get_allvalues(),
                "logged_in": user_svc.check_login(),
                "admin_logged_in": user_svc.check_admin_login(),
                "error": user_svc.get_error(),
            }
        elif method == "change_password":
            ok = user_svc.change_password(req.get("pwd", ""))
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "reset_password":
            ok, newpwd = user_svc.reset_password(req.get("email", ""))
            return {"success": ok, "newpwd": newpwd, "error": user_svc.get_error()}
        elif method == "set_newpassword":
            ok = user_svc.set_newpassword(req.get("oldpwd", ""), req.get("newpwd", ""))
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "update":
            user_svc.load_vals(req.get("data", {}))
            ok = user_svc.update()
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "remove":
            ok = user_svc.remove(req.get("userid"))
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "list_accounts":
            accounts = user_svc.list_accounts()
            return {"accounts": accounts, "error": user_svc.get_error()}
        elif method == "get_modemdevs":
            return {"modemdevs": user_svc.get_modemdevs(), "error": user_svc.get_error()}
        elif method == "set_modemdevs":
            ok = user_svc.set_modemdevs(req.get("modemdevs"))
            user_svc.update()
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "get_faxcats":
            return {"faxcats": user_svc.get_faxcats(), "error": user_svc.get_error()}
        elif method == "set_faxcats":
            ok = user_svc.set_faxcats(req.get("faxcats"))
            user_svc.update()
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "get_didrouting":
            return {"didrouting": user_svc.get_didrouting(), "error": user_svc.get_error()}
        elif method == "set_didrouting":
            ok = user_svc.set_didrouting(req.get("didrouting"))
            user_svc.update()
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "set_username":
            ok = user_svc.set_username(req.get("username", ""))
            if ok:
                user_svc.update()
            return {"success": ok, "error": user_svc.get_error()}
        elif method == "set_email":
            ok = user_svc.set_email(req.get("email", ""))
            if ok:
                user_svc.update()
            return {"success": ok, "error": user_svc.get_error()}
        return {"error": f"Unknown user_account method: {method}"}

    elif action == "archive_in":
        from avantfax.services.archive_in import ArchiveIn
        archive_in = ArchiveIn(db=_GLOBAL_ENGINE, installdir=req.get("installdir", ""))
        method = req.get("method")
        fid = req.get("fid")
        if fid:
            archive_in.load_fax(fid)

        if method == "create":
            ok = archive_in.create(
                path=req.get("path", ""),
                faxnid=req.get("faxnid", 0),
                faxnumber=req.get("faxnumber", ""),
                modem=req.get("modem", ""),
                pages=req.get("pages", 1),
                date=req.get("date"),
                didr_id=req.get("didr_id"),
            )
            return {"success": ok, "fid": archive_in.get_fid(), "error": archive_in.get_error()}
        elif method == "set_archivebox":
            ok = archive_in.set_archivebox(req.get("faxid"))
            return {"success": ok, "error": archive_in.get_error()}
        elif method == "rotate_fax":
            ok = archive_in.rotate_fax()
            return {"success": ok, "error": archive_in.get_error()}
        elif method == "prune_inbox":
            count = archive_in.prune_inbox(req.get("days", 0))
            return {"count": count, "error": archive_in.get_error()}
        return {"error": f"Unknown archive_in method: {method}"}

    elif action == "archive_out":
        from avantfax.services.archive_out import ArchiveOut
        archive_out = ArchiveOut(db=_GLOBAL_ENGINE, installdir=req.get("installdir", ""))
        method = req.get("method")
        fid = req.get("fid")
        if fid:
            archive_out.load_fax(fid)

        if method == "create":
            ok = archive_out.create(
                path=req.get("path", ""),
                userid=req.get("userid", 0),
                cid=req.get("cid"),
                origfaxnum=req.get("origfaxnum", ""),
                pages=req.get("pages", 1),
            )
            return {"success": ok, "fid": archive_out.get_fid(), "error": archive_out.get_error()}
        return {"error": f"Unknown archive_out method: {method}"}

    elif action == "faxqueue":
        from avantfax.services.faxqueue import FaxQueue
        from avantfax.services.user_account import AFUserAccount

        user_svc = AFUserAccount(db=_GLOBAL_ENGINE)
        method = req.get("method")
        fq = FaxQueue(user_account=user_svc, auto_process=False)

        if method == "get_queue":
            fq.process_queue(req.get("raw_output"))
            return {"queue": fq.get_queue()}
        elif method == "get_failed_queue":
            fq.process_failed_queue(req.get("raw_output"))
            return {"queue": fq.get_queue()}
        elif method == "list_owner":
            fq.process_queue(req.get("raw_output"))
            return {"queue": fq.list_owner(req.get("owner", ""))}
        elif method == "killjob":
            ok = fq.killjob(req.get("user", ""), req.get("jid", 0))
            return {"success": ok}
        elif method == "faxalter":
            ok = fq.faxalter(req.get("user", ""), req.get("jid", 0), req.get("operations", {}))
            return {"success": ok}
        return {"error": f"Unknown faxqueue method: {method}"}

    elif action == "xml":
        xml = _GLOBAL_ENGINE.gen_xml(
            xml_title=req.get("xml_title", True),
            mysql_style=req.get("mysql_style", False),
            root_tag=req.get("root_tag", "response"),
            row_tag=req.get("row_tag", "row"),
        )
        return {"xml": xml}

    return {"error": f"Unknown action: {action}"}


def main():
    if len(sys.argv) > 1:
        # Argument mode
        raw = sys.argv[1]
        req = json.loads(raw)
        res = handle_request(req)
        print(json.dumps(res))
    else:
        # Stdin stream mode
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                res = handle_request(req)
                print(json.dumps(res))
                sys.stdout.flush()
            except Exception as e:
                print(json.dumps({"error": str(e)}))
                sys.stdout.flush()


if __name__ == "__main__":
    main()
