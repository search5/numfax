#!/usr/bin/env python3
"""Inspect rendered forms, inputs, buttons, and dynamic state hooks for web scenarios."""

import json
from pathlib import Path
from bs4 import BeautifulSoup

GOLDEN_WEB_DIR = Path(__file__).parent / "web"

def inspect_all_forms():
    results = {}
    for scn_dir in sorted(GOLDEN_WEB_DIR.iterdir()):
        if not scn_dir.is_dir():
            continue
        resp_file = scn_dir / "response.html"
        contract_file = scn_dir / "contract.json"
        if not resp_file.exists() or not contract_file.exists():
            continue

        html = resp_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        forms = soup.find_all("form")
        if not forms:
            continue

        form_data = []
        for i, f in enumerate(forms):
            action = f.get("action", "")
            method = f.get("method", "get").upper()
            
            # Extract inputs, selects, textareas in exact DOM sequence
            fields = []
            for el in f.find_all(["input", "select", "textarea"]):
                tag = el.name
                el_type = el.get("type", "text") if tag == "input" else tag
                name = el.get("name", "")
                el_id = el.get("id", "")
                is_hidden = (el_type == "hidden") or ("hidden" in el.get("class", []))
                fields.append({
                    "tag": tag,
                    "type": el_type,
                    "name": name,
                    "id": el_id,
                    "required": el.has_attr("required"),
                })

            # Extract buttons
            buttons = []
            for b in f.find_all(["button", "input"]):
                b_type = b.get("type", "")
                if b.name == "button" or b_type in ("submit", "button", "reset"):
                    buttons.append({
                        "tag": b.name,
                        "type": b_type or "submit",
                        "name": b.get("name", ""),
                        "text": b.get_text(strip=True) or b.get("value", "")
                    })

            form_data.append({
                "index": i,
                "action": action,
                "method": method,
                "total_fields": len(fields),
                "total_buttons": len(buttons),
                "fields": fields,
                "buttons": buttons
            })

        results[scn_dir.name] = {
            "total_forms": len(forms),
            "forms": form_data
        }

    print(f"Discovered {len(results)} scenarios with forms.")
    out_file = Path(__file__).parent / "inspected_forms.json"
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved inspection to {out_file}")

if __name__ == "__main__":
    inspect_all_forms()
