#!/usr/bin/env python3
"""Extract live form structures and JS dynamic hooks from running WSGI app."""

import json
from pathlib import Path
from bs4 import BeautifulSoup
from webtest import TestApp

from namifax import create_app
from golden_master.web_runner import GOLDEN_WEB_DIR

def extract_live_form_structures():
    app = TestApp(create_app({}))
    app.post("/login", {"username": "admin", "password": "password", "_submit_check": "1"})

    live_specs = {}

    for s_dir in sorted(GOLDEN_WEB_DIR.iterdir()):
        if not s_dir.is_dir():
            continue
        meta_file = s_dir / "meta.json"
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if meta.get("method") != "GET":
            continue

        route = meta["route"]
        s_id = s_dir.name

        try:
            client = TestApp(create_app({})) if not meta.get("authenticated", True) else app
            res = client.get(route, expect_errors=True)
            if res.status_code != 200 or not res.content_type.startswith("text/html"):
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            forms = soup.find_all("form")
            if not forms:
                continue

            form_list = []
            for idx, f in enumerate(forms):
                action = f.get("action", "")
                method = f.get("method", "GET").upper()
                
                inputs = f.find_all(["input", "select", "textarea"])
                field_sequence = []
                for el in inputs:
                    name = el.get("name", "")
                    tag = el.name
                    el_type = el.get("type", tag) if tag == "input" else tag
                    field_sequence.append({
                        "name": name,
                        "tag": tag,
                        "type": el_type,
                        "id": el.get("id", ""),
                        "required": el.has_attr("required")
                    })

                buttons = f.find_all("button") + [
                    b for b in f.find_all("input") if b.get("type") in ("submit", "button", "reset")
                ]
                button_sequence = []
                for b in buttons:
                    button_sequence.append({
                        "tag": b.name,
                        "type": b.get("type", "submit"),
                        "name": b.get("name", ""),
                        "text": b.get_text(strip=True) or b.get("value", "")
                    })

                form_list.append({
                    "index": idx,
                    "action": action,
                    "method": method,
                    "inputs_count": len(inputs),
                    "buttons_count": len(buttons),
                    "field_sequence": field_sequence,
                    "button_sequence": button_sequence
                })

            live_specs[s_id] = {
                "total_forms": len(forms),
                "forms": form_list
            }

        except Exception as e:
            print(f"Error on {s_id}: {e}")

    out_file = Path(__file__).parent / "live_form_structures.json"
    out_file.write_text(json.dumps(live_specs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Extracted live form structures for {len(live_specs)} scenarios -> {out_file}")

if __name__ == "__main__":
    extract_live_form_structures()
