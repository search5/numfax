"""Bring the original AvantFAX's English wording and translations into the catalogs.

1. WORDING: where a screen text of NamiFAX means exactly what a text of the original means, NamiFAX uses the original's English
   (``RENAMES`` below, chosen one by one: the same screen and the same role; a short text that NamiFAX also uses elsewhere is not
   renamed). The English texts in the templates and views are changed, and so are the catalogs (the template, and the Korean
   translation, which is kept).
2. TRANSLATIONS: for a text that is now the same English as an original text, the original's translation fills a language that has
   none (empty or fuzzy). A translation that is already there is kept. Positional placeholders (``%s``, ``%d``) become the named
   ones (``%(name)s``) in order; a text with markup, or a conflict between two original keys, is left alone.

Run ``python tools/i18n_import_legacy.py`` for a report and add ``--apply`` to write. Safe to run again.
"""

from __future__ import annotations

import argparse
import html
import io
import os
import re
import sys
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "namifax"
LOCALES = SRC / "locale"
LEGACY = ROOT / "legacy" / "avantfax" / "includes" / "langs"

# original language file -> NamiFAX locale
LANGS = {"ar": "ar", "bg": "bg", "cz": "cs", "de": "de", "el": "el", "es": "es", "fr": "fr", "hu": "hu", "it": "it", "ja": "ja",
         "nl": "nl", "no": "no", "pl": "pl", "pt-br": "pt_BR", "pt-pt": "pt_PT", "ro": "ro", "rs": "sr", "ru": "ru", "sv": "sv",
         "tr": "tr", "zh-tw": "zh_TW", "zh": "zh_CN"}

# (original key, NamiFAX text now, the original's English)
RENAMES = [
    ("ADD_NOTE_FAX", "Add Note", "Add a note"),
    ("ADMIN_ACC_ENABLED", "Account enabled", "Account active"),
    ("ADMIN_COVER_UPDATED", "Cover page template updated successfully", "The cover page was updated"),
    ("ADMIN_MODEM_CREATED", "Modem created", "The modem was created"),
    ("ADMIN_MODEM_DELETED", "Modem deleted", "The modem was deleted"),
    ("ADMIN_MODEM_UPDATED", "Modem updated", "The modem was updated"),
    ("ARCHIVE_SHOW", "Archive shows", "Archive - show"),
    ("INBOX_SHOW", "Inbox shows", "Inbox - show"),
    ("ASSIGN_CNAME", "Assign company name", "Assign a company name"),
    ("ASSIGN_MISSING", "Please enter a company name", "You must enter a company name"),
    ("CONTACT_SAVED", "Contact saved.", "Contact details saved"),
    ("DISTROLIST_REMOVE", "Remove selected", "Remove entries"),
    ("DISTROLIST_SAVENAME", "Save name", "Save list name"),
    ("EMAIL_FAILURE", "Failed to send email", "The email failed to send."),
    ("EMAIL_SUCCESS", "Email sent successfully", "The email was sent successfully."),
    ("FAX_DEST", "Destination Number", "Destination fax numbers"),
    ("MISSING_ALIAS_NAME", "Please enter an alias", "You must enter an alias"),
    ("MISSING_DEVICE_NAME", "Please enter a device name", "You must enter a device name"),
    ("MODIFY_FAXJOB", "Modify Fax Job", "Modify Job"),
    ("NAME_MISSING", "Please enter a name", "You must enter a name."),
    ("NOTIFY_REQUEUE", "Notify on retry", "Notify on requeue"),
    ("SEND_EMAIL_HEADER", "Send Fax via Email", "Forward fax via email"),
    ("TO_PERSON", "Attention Person", "To person"),
    ("USER_CANDEL", "Can Delete Faxes", "User can delete faxes"),
    ("USER_DETAILS_SAVED", "User details saved", "User settings have been saved."),
    ("SELECT_ALL_FAXES", "Select All", "Select All Faxes"),
]


# translations in the original's own language files that say the opposite of the English (checked by reading them); not imported
KNOWN_WRONG = {
    ("ja", "ADMIN_MODEM_CREATED"),      # "モデムは作成されませんでした" = "the modem was not created"
    ("ja", "ADMIN_MODEM_DELETED"),      # "モデムは削除できませんでした" = "the modem could not be deleted"
}


def php_langs(path: Path) -> dict[str, tuple[str, bool]]:
    """key -> (text, True when the original builds the text with a constant, which this does not follow)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out = {}
    for key, raw, tail in re.findall(r"\$LANG\['([A-Z0-9_]+)'\]\s*=\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')\s*(\.[^;]*)?;", text, re.S):
        out[key] = (raw[1:-1].replace('\\"', '"').replace("\\'", "'").replace("\\n", "\n"), bool(tail))
    return out


def plain(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(text)))).strip()


def norm(text: str) -> str:
    text = re.sub(r"%\(\w+\)[sd]|%[sd]", "%s", plain(text))
    return re.sub(r"[\s:.!?…]+", " ", text).strip().lower()


def named(translation: str, msgid: str) -> str | None:
    """The original's translation with its positional placeholders as the named ones of ``msgid`` (None: they do not fit)."""
    wanted = re.findall(r"%\(\w+\)([sd])", msgid)
    positional = re.findall(r"%([sd])", re.sub(r"%\(\w+\)[sd]", "", translation))
    if not wanted and not positional:
        return translation
    if re.search(r"%\(\w+\)[sd]", translation) or len(wanted) != len(positional) or wanted != positional:
        return None
    names = iter(re.findall(r"%\(\w+\)[sd]", msgid))
    return re.sub(r"%[sd]", lambda m: next(names), translation)


def rename_in_source(apply: bool) -> int:
    total = 0
    files = [p for p in SRC.rglob("*") if p.suffix in (".py", ".jinja2", ".js") and "locale" not in p.parts
             and "alembic" not in p.parts and "__pycache__" not in p.parts]
    for _, old, new in RENAMES:
        assert "'" not in new and '"' not in new and "\\" not in new, new
        count = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            changed = text
            for quote in ("'", '"'):
                changed = changed.replace(f"{quote}{old}{quote}", f"{quote}{new}{quote}")
            if changed != text:
                count += sum(text.count(f"{q}{old}{q}") for q in ("'", '"'))
                if apply:
                    path.write_text(changed, encoding="utf-8")
        total += count
        print(f"  source  {count:2}x  {old!r} -> {new!r}")
    return total


def rename_textual(path: Path, apply: bool) -> int:
    """Rename msgids in a catalog file as text (the template and the Korean file are kept exactly as they are otherwise)."""
    text = path.read_text(encoding="utf-8")
    count = 0
    for _, old, new in RENAMES:
        needle, replacement = f'\nmsgid "{old}"\n', f'\nmsgid "{new}"\n'
        if needle in text and f'\nmsgid "{new}"\n' not in text:
            text = text.replace(needle, replacement)
            count += 1
    if apply and count:
        path.write_text(text, encoding="utf-8")
    return count


def live(message) -> bool:
    return bool(message.id) and bool(message.string) and not message.fuzzy and message.string != message.id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes (without it: a report)")
    args = parser.parse_args()
    apply = args.apply
    print("sources" + ("" if apply else " (report only)"))
    rename_in_source(apply)

    print("catalog template and Korean")
    for path in (LOCALES / "namifax.pot", LOCALES / "ko" / "LC_MESSAGES" / "namifax.po"):
        print(f"  {path.relative_to(ROOT)}: {rename_textual(path, apply)} text(s) renamed")
    if apply:
        ko = LOCALES / "ko" / "LC_MESSAGES"
        with open(ko / "namifax.po", "rb") as fh, open(ko / "namifax.mo", "wb") as out:
            write_mo(out, read_po(fh, locale="ko"))

    english = {k: v[0] for k, v in php_langs(LEGACY / "en.php").items()}
    renamed = {new: key for key, _, new in RENAMES}
    print("translations")
    grand = 0
    for legacy_code, locale in LANGS.items():
        path = LOCALES / locale / "LC_MESSAGES" / "namifax.po"
        legacy = php_langs(LEGACY / f"{legacy_code}.php")
        with open(path, "rb") as fh:
            raw = fh.read()
        catalog = read_po(io.BytesIO(raw), locale=locale)
        by_norm: dict[str, list] = {}
        for message in catalog:
            if message.id and isinstance(message.id, str):
                by_norm.setdefault(norm(message.id), []).append(message)
        for key, old, new in RENAMES:                              # the original's wording and translation for a renamed text
            message = catalog.get(old)
            if message is not None and catalog.get(new) is None:
                catalog.delete(old)
                catalog.add(new, string=message.string, locations=message.locations, flags=message.flags,
                            auto_comments=message.auto_comments, user_comments=message.user_comments)
                by_norm.setdefault(norm(new), []).append(catalog.get(new))
        added = skipped = 0
        chosen: dict[str, set] = {}
        for key, (translation, built) in legacy.items():
            if key not in english or built or "<" in translation or "<" in english[key] or (locale, key) in KNOWN_WRONG:
                continue
            if plain(translation) == plain(english[key]) or not plain(translation):
                continue                                           # not translated in the original either
            if re.search(r"avantfax|avant\s*fax", translation + english[key], re.I):
                continue                                           # names the old product
            for message in by_norm.get(norm(english[key]), []):
                final = named(plain(translation), message.id)
                if final is None:
                    skipped += 1
                    continue
                chosen.setdefault(message.id, set()).add(final)
        for msgid, finals in chosen.items():
            message = catalog.get(msgid)
            if len(finals) != 1:
                skipped += 1                                       # two original keys disagree
                continue
            final = next(iter(finals))
            renamed_now = msgid in renamed
            if live(message) and not renamed_now:
                continue                                           # a translation is there: kept
            if message.string != final or message.fuzzy:
                message.string = final
                message.flags.discard("fuzzy")
                added += 1
        grand += added
        print(f"  {locale:6} {added:3} translation(s) filled from {legacy_code}.php, {skipped} left alone")
        if apply:
            buffer = io.BytesIO()
            write_po(buffer, catalog, width=76, sort_output=False)
            path.write_bytes(buffer.getvalue())
            with open(path.with_suffix(".mo"), "wb") as out:
                write_mo(out, catalog)
    print(f"total translations filled: {grand}" + ("" if apply else "  (report only: nothing written; run with --apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
