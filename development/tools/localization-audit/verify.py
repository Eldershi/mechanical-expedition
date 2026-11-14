#!/usr/bin/env python3
"""Verify supplemental language coverage, formatting and localized manual pages."""

import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import re


HAN = re.compile(r"[\u3400-\u9fff]")
PRINTF = re.compile(r"%(?:(\d+)\$)?[-#+0,(]*\d*(?:\.\d+)?([a-zA-Z%])")
STYLE = re.compile(r"§[0-9a-fk-orx]", re.I)
MACRO = re.compile(r"\$\([^)]*\)")
URL = re.compile(r"https?://[^\s<>\"']+")
RESOURCE = re.compile(r"\b[a-z0-9_]+:[a-z0-9_./-]+\b")


def signature(text):
    sequential = 0
    values = []
    for match in PRINTF.finditer(text):
        if match.group(2) == "%":
            values.append((0, "%"))
            continue
        if match.group(1):
            index = int(match.group(1))
        else:
            sequential += 1
            index = sequential
        values.append((index, match.group(2)))
    return Counter(values)


def format_failures(english, chinese):
    failures = []
    for name, left, right in (
        ("printf", signature(english), signature(chinese)),
        ("formatting", Counter(STYLE.findall(english)), Counter(STYLE.findall(chinese))),
        ("Patchouli macros", Counter(MACRO.findall(english)), Counter(MACRO.findall(chinese))),
        ("URLs", Counter(URL.findall(MACRO.sub("", english))), Counter(URL.findall(MACRO.sub("", chinese)))),
        ("resource identifiers", Counter(RESOURCE.findall(MACRO.sub("", english))), Counter(RESOURCE.findall(MACRO.sub("", chinese)))),
    ):
        if left != right:
            failures.append(name)
    return failures


def numbers(text):
    text = PRINTF.sub("", STYLE.sub("", MACRO.sub("", text)))
    # Legacy tooltips commonly use '-' as a list bullet immediately before a
    # positive value. Compare magnitudes here; review wording for signs and
    # conditions separately when checking weapon mechanics.
    return Counter(re.findall(r"(?<![\d.])\d+(?:\.\d+)?", text))


def get_path(data, path):
    for part in path:
        data = data[part]
    return data


def set_path(data, path, value):
    for part in path[:-1]:
        data = data[part]
    data[path[-1]] = value


def load_layers(source):
    language = {}
    resources = {}
    for layer in ("upstream", "manual"):
        root = source / layer
        for path in sorted((root / "assets").rglob("*.json")):
            relative = path.relative_to(root).as_posix()
            value = json.loads(path.read_text())
            if relative.endswith("/lang/zh_cn.json"):
                language.update(value)
            else:
                resources[relative] = value
        for path in sorted(root.glob("*.json")):
            if path.name not in {"SOURCE.json", "manifest.json", "allowlist.json"}:
                language.update(json.loads(path.read_text()))
    return language, resources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches", type=Path, required=True)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--page-jobs", type=Path)
    parser.add_argument("--page-allowlist", type=Path, default=Path(__file__).with_name("page-allowlist.json"))
    parser.add_argument("--format-exceptions", type=Path, default=Path(__file__).with_name("format-exceptions.json"))
    parser.add_argument("--numeric-exceptions", type=Path, default=Path(__file__).with_name("numeric-exceptions.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    language, resources = load_layers(args.translations)
    allowlist = json.loads(args.allowlist.read_text())
    page_allowlist = json.loads(args.page_allowlist.read_text()) if args.page_allowlist.exists() else []
    format_exceptions = json.loads(args.format_exceptions.read_text()) if args.format_exceptions.exists() else {}
    numeric_exceptions = json.loads(args.numeric_exceptions.read_text()) if args.numeric_exceptions.exists() else {}
    numeric_language = numeric_exceptions.get("language", {})
    numeric_pages = {(entry["resource"], tuple(entry["path"]), entry["value"]): entry["reason"]
                     for entry in numeric_exceptions.get("pages", [])}
    allowed_page_values = {(entry["resource"], tuple(entry["path"]), entry["value"]): entry["reason"]
                           for entry in page_allowlist}
    rows = []
    for path in sorted(args.batches.glob("*.json")):
        if path.name != "manifest.json":
            rows.extend(json.loads(path.read_text()))
    missing = []
    latin = []
    formatting = []
    numeric = []
    intentional = []
    reviewed_formats = []
    reviewed_numbers = []
    covered = Counter()
    for row in rows:
        value = language.get(row["key"])
        exception = allowlist.get(row["key"])
        if value is None:
            if exception and exception["value"] in {row["en"], row.get("currentZh")}:
                intentional.append({"namespace": row["namespace"], "key": row["key"], **exception})
                covered[row["namespace"]] += 1
            else:
                missing.append(row)
            continue
        if not isinstance(value, str):
            missing.append(dict(row, reason="Translation is not a string"))
            continue
        covered[row["namespace"]] += 1
        if not HAN.search(value) and re.search(r"[A-Za-z]{3,}", value):
            if exception and value == exception["value"]:
                intentional.append({"namespace": row["namespace"], "key": row["key"], **exception})
            else:
                latin.append(dict(row, value=value))
        kinds = format_failures(row["en"], value)
        exception = format_exceptions.get(row["key"])
        if exception and exception["value"] == value:
            accepted = [kind for kind in kinds if kind in exception["kinds"]]
            if accepted:
                reviewed_formats.append({"namespace": row["namespace"], "key": row["key"], **exception})
            kinds = [kind for kind in kinds if kind not in accepted]
        if kinds:
            formatting.append({"namespace": row["namespace"], "key": row["key"], "kinds": kinds,
                               "en": row["en"], "zh": value})
        if numbers(row["en"]) != numbers(value):
            reviewed = numeric_language.get(row["key"])
            if reviewed and reviewed["value"] == value:
                reviewed_numbers.append({"namespace": row["namespace"], "key": row["key"], **reviewed})
            else:
                numeric.append({"namespace": row["namespace"], "key": row["key"], "en": row["en"], "zh": value})
    page_rows = json.loads(args.page_jobs.read_text()) if args.page_jobs else []
    page_missing = []
    page_formats = []
    page_numeric = []
    page_literals = []
    page_structure = []
    page_reviewed_numbers = []
    translated_pages = 0
    translated_fields = 0
    skipped_fields = []
    for page in page_rows:
        resource = page["resource"]
        if resource.startswith("data/"):
            resource = "assets/" + resource.removeprefix("data/")
        fields = [field for field in page["fields"] if not re.fullmatch(r"#[\w.]+#?", field["en"])]
        skipped_fields.extend({"resource": resource, **field} for field in page["fields"] if field not in fields)
        if not fields:
            continue
        data = resources.get(resource)
        if data is None:
            page_missing.append({"resource": resource, "reason": "Localized page absent"})
            continue
        before = copy.deepcopy(page["data"])
        after = copy.deepcopy(data)
        translated_pages += 1
        for field in fields:
            try:
                value = get_path(data, field["path"])
            except (KeyError, IndexError, TypeError):
                page_missing.append({"resource": resource, "path": field["path"], "reason": "Localized field absent"})
                continue
            translated_fields += 1
            if not HAN.search(value) and re.search(r"[A-Za-z]{3,}", value):
                identity = (resource, tuple(field["path"]), value)
                if identity in allowed_page_values:
                    page_literals.append({"resource": resource, "path": field["path"], "value": value,
                                          "reason": allowed_page_values[identity]})
                else:
                    page_missing.append({"resource": resource, "path": field["path"], "value": value,
                                         "reason": "Unreviewed Latin-only page text"})
            kinds = format_failures(field["en"], value)
            if kinds:
                page_formats.append({"resource": resource, "path": field["path"], "kinds": kinds,
                                     "en": field["en"], "zh": value})
            if numbers(field["en"]) != numbers(value):
                identity = (resource, tuple(field["path"]), value)
                if identity in numeric_pages:
                    page_reviewed_numbers.append({"resource": resource, "path": field["path"], "value": value,
                                                  "reason": numeric_pages[identity]})
                else:
                    page_numeric.append({"resource": resource, "path": field["path"], "en": field["en"], "zh": value})
            set_path(before, field["path"], None)
            set_path(after, field["path"], None)
        if before != after:
            page_structure.append({"resource": resource, "reason": "Non-translatable page data changed"})
    report = {
        "scope": "Actionable language batches and literal Patchouli page fields; explicit proper-name exceptions remain visible. Runtime hard-coded strings require the in-game tooltip probe.",
        "language": {"expected": len(rows), "covered": sum(covered.values()), "byNamespace": dict(covered),
                     "missing": missing, "unreviewedLatin": latin, "formatFailures": formatting,
                     "reviewedFormatExceptions": reviewed_formats,
                     "numericReview": numeric, "reviewedNumericExceptions": reviewed_numbers,
                     "intentionalLiteralValues": intentional},
        "pages": {"expectedFiles": len(page_rows), "translatedFiles": translated_pages,
                  "translatedFields": translated_fields, "missing": page_missing, "formatFailures": page_formats,
                  "nonTextDataChanges": page_structure, "numericReview": page_numeric,
                  "reviewedNumericExceptions": page_reviewed_numbers,
                  "intentionalLiteralValues": page_literals, "templatePlaceholders": skipped_fields},
        "passed": not any((missing, latin, formatting, numeric, page_missing, page_formats, page_structure, page_numeric)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "expectedKeys": len(rows), "coveredKeys": sum(covered.values()),
                      "missingKeys": len(missing), "unreviewedLatinKeys": len(latin), "formatFailures": len(formatting),
                      "numericReview": len(numeric), "translatedPages": translated_pages,
                      "missingPageFields": len(page_missing), "pageFormatFailures": len(page_formats),
                      "pageNonTextChanges": len(page_structure), "pageNumericReview": len(page_numeric)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
