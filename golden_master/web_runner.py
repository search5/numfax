#!/usr/bin/env python3
"""Web E2E Differential Verification Runner for NamiFAX / AvantFAX.

Runs the Pyramid web application via webtest.TestApp and verifies
rendered responses against recorded Golden Master contracts (status, forms, texts, links).
"""

import argparse
import contextlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from webtest import TestApp

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from namifax import create_app as make_app

GOLDEN_WEB_DIR = ROOT_DIR / "golden_master" / "web"


def normalize_text(text: str) -> str:
    """Normalize whitespace in text for loose semantic comparison."""
    return re.sub(r"\s+", " ", text).strip()


@contextlib.contextmanager
def isolated_database():
    """A new throw-away SQLite database with the demo data, for the duration of the block.

    (Without this the golden master tools used the working tree's namifax.db, whose layout and contents depend on what a
    developer last ran, so scenarios failed or passed by accident.)
    """
    folder = tempfile.mkdtemp(prefix="namifax-golden-")
    wanted = {"DATABASE_URL": f"sqlite:///{folder}/golden.db", "NAMIFAX_DB_PATH": f"{folder}/golden.db",
              "NAMIFAX_DEMO_DATA": "1", "NAMIFAX_SECRET_KEY": os.environ.get("NAMIFAX_SECRET_KEY") or "golden-master-run"}
    saved = {key: os.environ.get(key) for key in (*wanted, "AFDB_URL")}
    os.environ.update(wanted)
    os.environ.pop("AFDB_URL", None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(folder, ignore_errors=True)


def _client_with_pending_password_change() -> TestApp:
    """A browser that has just signed in with an account that must choose a new password (it is sent to /pwdexpired)."""
    from sqlalchemy.orm import Session

    from namifax.services.user_account import AFUserAccount

    application = make_app({})
    with Session(application.registry["dbengine"]) as session:
        account = AFUserAccount(db=session)
        assert account.create({"username": "mustchange", "password": "Secret123!", "email": "must@change.test",
                               "name": "Must Change"}), account.get_error()      # never signed in: has to change it
        session.commit()
    client = TestApp(application)
    client.post("/login", {"username": "mustchange", "password": "Secret123!", "_submit_check": "1"})
    return client


def run_web_verification(target_scenario: str | None = None) -> int:
    """Execute differential check for all web scenarios (on an isolated database)."""
    with isolated_database():
        return _verify_all_scenarios(target_scenario)


def _verify_all_scenarios(target_scenario: str | None = None) -> int:
    if not GOLDEN_WEB_DIR.exists():
        print(f"[-] Web Golden Master dir {GOLDEN_WEB_DIR} does not exist.")
        return 1

    app = TestApp(make_app({}))
    
    # Authenticate admin user by default for authenticated routes
    # Simulate a login session
    session_cookies = {}
    login_res = app.post("/login", {"username": "admin", "password": "password", "_submit_check": "1"})
    if login_res.status_code == 302:
        session_cookies = app.cookies

    scenario_dirs = sorted([p for p in GOLDEN_WEB_DIR.iterdir() if p.is_dir()])
    if target_scenario:
        scenario_dirs = [p for p in scenario_dirs if p.name == target_scenario]

    print(f"[*] Verifying {len(scenario_dirs)} Web E2E Golden Master Scenarios...")
    passed = 0
    failed = 0

    for s_dir in scenario_dirs:
        s_id = s_dir.name
        meta = json.loads((s_dir / "meta.json").read_text(encoding="utf-8"))
        contract = json.loads((s_dir / "contract.json").read_text(encoding="utf-8"))

        route = meta["route"]
        method = meta["method"]
        exp_status = contract.get("status_code", 200)

        errors = []
        try:
            # Dispatch request
            test_client = app
            if s_id.startswith("W01_") or not meta.get("authenticated", True):
                # Clean client for unauthenticated tests
                test_client = TestApp(make_app({}))
            if meta.get("setup") == "pwd_change_pending":
                test_client = _client_with_pending_password_change()

            headers = meta.get("headers", {})

            if method == "GET":
                res = test_client.get(route, headers=headers, expect_errors=True)
            elif method == "POST":
                # Prepare mock post data
                post_data = {"_submit_check": "1"}
                if s_id == "W02_login_fail":
                    post_data = {"username": "baduser", "password": "wrongpassword", "_submit_check": "1"}
                elif s_id == "W03_login_success":
                    post_data = {"username": "admin", "password": "password", "_submit_check": "1"}
                elif s_id == "W10_sendfax_err":
                    post_data = {"faxnumber": "", "_submit_check": "1"}
                elif s_id == "W11_sendfax_post":
                    post_data = {"to_person": "Receiver", "faxnumber": "1234567", "_submit_check": "1"}
                
                res = test_client.post(route, post_data, headers=headers, expect_errors=True)
            else:
                errors.append(f"Unsupported method: {method}")
                res = None

            if res is not None:
                # 1. Status Code Check
                if res.status_code != exp_status:
                    errors.append(f"Status mismatch: expected {exp_status}, got {res.status_code}")

                # 2. Redirect Location Check
                if "redirect_location" in contract:
                    exp_loc = contract["redirect_location"]
                    act_loc = res.headers.get("Location", "")
                    if exp_loc not in act_loc:
                        errors.append(f"Location mismatch: expected {exp_loc} in '{act_loc}'")

                # 3. Content Type Check
                if "content_type" in contract:
                    exp_ct = contract["content_type"]
                    act_ct = res.content_type
                    if exp_ct not in act_ct:
                        errors.append(f"Content-Type mismatch: expected {exp_ct}, got {act_ct}")

                # 4. Form and Input Contract Check
                soup = BeautifulSoup(res.text, "html.parser")
                if "forms" in contract:
                    for position, f_spec in enumerate(contract["forms"]):
                        forms = soup.find_all("form")
                        if not forms:
                            errors.append("Expected <form> tag, but none found in rendered HTML")
                            break
                        if position >= len(forms):
                            errors.append(f"Expected form at index {position}, but only {len(forms)} forms exist")
                            break
                        matched_form = forms[position]       # the n-th spec describes the n-th form of the page
                        if "inputs" in f_spec:
                            for inp in f_spec["inputs"]:
                                name = inp["name"]
                                found = matched_form.find(["input", "select", "textarea"], {"name": name})
                                if not found:
                                    errors.append(f"Missing required form input: {name}")

                # 4-1. Strict Form Structure & Exact Element Count Check
                if "form_structure" in contract:
                    f_struct = contract["form_structure"]
                    forms = soup.find_all("form")
                    exp_total_forms = f_struct.get("total_forms")
                    if exp_total_forms is not None and len(forms) != exp_total_forms:
                        errors.append(f"Exact form count mismatch: expected {exp_total_forms}, found {len(forms)}")

                    for idx, exp_form in enumerate(f_struct.get("forms", [])):
                        if idx >= len(forms):
                            errors.append(f"Expected form at index {idx}, but only {len(forms)} forms exist")
                            break
                        act_form = forms[idx]

                        if "action" in exp_form and exp_form["action"] not in act_form.get("action", ""):
                            errors.append(f"Form[{idx}] action mismatch: expected '{exp_form['action']}', got '{act_form.get('action')}'")
                        if "method" in exp_form and exp_form["method"].upper() != act_form.get("method", "GET").upper():
                            errors.append(f"Form[{idx}] method mismatch: expected '{exp_form['method']}', got '{act_form.get('method')}'")

                        all_inputs = act_form.find_all(["input", "select", "textarea"])
                        if "inputs_count" in exp_form:
                            has_collection = any("[]" in f.get("name", "") for f in exp_form.get("field_sequence", []))
                            if has_collection:
                                if len(all_inputs) < exp_form["inputs_count"]:
                                    errors.append(f"Form[{idx}] inputs count below baseline: expected at least {exp_form['inputs_count']}, found {len(all_inputs)}")
                            else:
                                if len(all_inputs) != exp_form["inputs_count"]:
                                    errors.append(f"Form[{idx}] exact inputs count mismatch: expected {exp_form['inputs_count']}, found {len(all_inputs)}")


                        all_buttons = act_form.find_all(["button"]) + [
                            b for b in act_form.find_all("input") if b.get("type") in ("submit", "button", "reset")
                        ]
                        if "buttons_count" in exp_form and len(all_buttons) != exp_form["buttons_count"]:
                            errors.append(f"Form[{idx}] exact buttons count mismatch: expected {exp_form['buttons_count']}, found {len(all_buttons)}")

                        if "field_sequence" in exp_form:
                            act_field_names = [el.get("name", "") for el in all_inputs if el.get("name")]
                            for exp_field in exp_form["field_sequence"]:
                                exp_name = exp_field.get("name", "")
                                if not exp_name:
                                    continue
                                if exp_name not in act_field_names:
                                    errors.append(f"Form[{idx}] missing field '{exp_name}' in sequence")


                # 4-2. Dynamic States and JS Interaction Hooks Check
                if "dynamic_states" in contract:
                    dyn_states = contract["dynamic_states"]
                    for state_key, state_spec in dyn_states.items():
                        if "trigger_selector" in state_spec:
                            sel = state_spec["trigger_selector"]
                            trigger = soup.select_one(sel)
                            if not trigger:
                                errors.append(f"Dynamic state '{state_key}': trigger '{sel}' not found in DOM")

                        if "target_container" in state_spec:
                            c_sel = state_spec["target_container"]
                            container = soup.select_one(c_sel)
                            if not container:
                                errors.append(f"Dynamic state '{state_key}': target container '{c_sel}' not found in DOM")

                        if "affected_inputs" in state_spec:
                            for inp_name in state_spec["affected_inputs"]:
                                found = soup.find(["input", "select", "textarea"], {"name": inp_name})
                                if not found:
                                    errors.append(f"Dynamic state '{state_key}': affected input '{inp_name}' not found in DOM")


                # 5. Required Links Check
                if "required_links" in contract:
                    all_hrefs = [a.get("href", "") for a in soup.find_all("a")]
                    for req_link in contract["required_links"]:
                        req_alt = req_link.replace("avantfax.com", "namifax.local")
                        if not any(req_link in h for h in all_hrefs) and not any(req_alt in h for h in all_hrefs):
                            errors.append(f"Missing required link: {req_link}")

                # 6. Required Texts Check
                if "required_text" in contract:
                    page_text = normalize_text(soup.get_text())
                    raw_text = normalize_text(res.text)
                    for req_txt in contract["required_text"]:
                        req_alt = req_txt.replace("AvantFAX", "NamiFAX").replace("avantfax", "namifax")
                        matched = (
                            req_txt.lower() in page_text.lower()
                            or req_txt.lower() in raw_text.lower()
                            or req_alt.lower() in page_text.lower()
                            or req_alt.lower() in raw_text.lower()
                        )
                        if not matched:
                            errors.append(f"Missing required text: '{req_txt}'")


        except Exception as e:
            errors.append(f"Exception during request: {e}")

        if not errors:
            print(f"  [PASS] {s_id} - {meta['description']}")
            passed += 1
        else:
            print(f"  [FAIL] {s_id} - {meta['description']}")
            for err in errors:
                print(f"         x {err}")
            failed += 1

    print(f"\n[Web E2E Result] Total: {len(scenario_dirs)}, Passed: {passed}, Failed: {failed}")
    return 0 if failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Web E2E Golden Master Differential Runner")
    parser.add_argument("--verify", action="store_true", help="Run differential check against golden master")
    parser.add_argument("--scenario", type=str, default=None, help="Run only specific scenario")
    args = parser.parse_args()

    sys.exit(run_web_verification(args.scenario))


if __name__ == "__main__":
    main()
