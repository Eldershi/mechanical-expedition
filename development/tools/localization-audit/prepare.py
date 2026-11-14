#!/usr/bin/env python3
"""Prepare licensed upstream supplements and manageable translation batches."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

HAN = re.compile(r"[\u3400-\u9fff]")
FORMAT = re.compile(r"%(?:\d+\$)?[-#+ 0,(]*\d*(?:\.\d+)?([a-zA-Z%])")


def tokens(value):
    return sorted(x for x in FORMAT.findall(value) if x != "%")


def nonprose(value):
    value = re.sub(r"§[0-9a-fk-or]", "", value, flags=re.I)
    value = re.sub(r"\$\([^)]*\)", "", value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"%(?:\d+\$)?[-#+ 0,(]*\d*(?:\.\d+)?[a-zA-Z%]", "", value)
    value = re.sub(r"\{[\w.]+\}", "", value)
    return value.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True, action="append")
    parser.add_argument("--source-output", type=Path, required=True)
    parser.add_argument("--batch-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--memory", type=Path)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    upstream = {}
    provenance = {}
    upstream_pages = {}
    upstream_assets = []
    for package in args.upstream:
        package_name = "Minecraft-Mod-Language-Modpack-" + package.stem.removeprefix("CFPA-") + ".zip"
        upstream_assets.append({"asset": "https://github.com/CFPAOrg/Minecraft-Mod-Language-Package/releases/download/autobuild/" + package_name,
                                "sha256": hashlib.sha256(package.read_bytes()).hexdigest()})
        with ZipFile(package) as archive:
            for name in archive.namelist():
                if name.endswith("/lang/zh_cn.json"):
                    try:
                        values = json.loads(archive.read(name).decode("utf-8-sig"), strict=False)
                        for key, value in values.items():
                            if isinstance(value, str) and (key not in upstream or not HAN.search(upstream[key])):
                                upstream[key] = value
                                provenance[key] = {"package": package_name, "resource": name}
                    except (ValueError, UnicodeError):
                        pass
                elif "/patchouli_books/" in name and "/zh_cn/" in name and name.endswith(".json"):
                    upstream_pages.setdefault(name, archive.read(name))
            license_text = archive.read("LICENSE")
    args.source_output.mkdir(parents=True, exist_ok=True)
    for previous in (args.source_output / "assets").glob("*/lang/zh_cn.json"):
        previous.unlink()
    (args.source_output / "LICENSE-CFPA.txt").write_bytes(license_text)
    namespace_values = defaultdict(dict)
    adopted = []
    rejected = []
    remaining = defaultdict(list)
    skipped = []
    memory = json.loads(args.memory.read_text()) if args.memory else {}
    memory_adopted = []
    candidates = audit["missing"] + audit["latinOnlyChinese"]
    active_owners = set(audit.get("loadedModIds", [])) | set(audit.get("installedResourceNamespaces", []))
    for entry in candidates:
        key, english, namespace = entry["key"], entry["english"], entry["namespace"]
        owner = re.match(r"^(?:item|block|entity|enchantment|effect|fluid)\.([\w-]+)\.", key)
        if owner and active_owners and owner.group(1) not in active_owners:
            skipped.append({"namespace": namespace, "key": key, "reason": "optional content namespace absent from installed mods"})
            continue
        chinese = upstream.get(key)
        if chinese and HAN.search(chinese):
            if tokens(chinese) == tokens(english):
                namespace_values[namespace][key] = chinese
                adopted.append({"namespace": namespace, "key": key, "source": provenance[key]})
                continue
            rejected.append({"namespace": namespace, "key": key, "reason": "printf placeholder mismatch", "en": english, "zh": chinese})
        remembered = memory.get(english)
        if remembered and tokens(remembered["zh"]) == tokens(english):
            namespace_values[namespace][key] = remembered["zh"]
            memory_adopted.append({"namespace": namespace, "key": key, "source": remembered["source"]})
            continue
        plain = nonprose(entry.get("chinese") or english)
        kind = "missing" if "chinese" not in entry else "latin_only_chinese"
        # Keep mod names, variable placeholders, resource IDs and technical
        # abbreviations out of the actionable natural-language workload.
        reason = None
        if not re.search(r"[A-Za-z]{3,}", plain):
            reason = "only formatting, numbers or short symbols"
        elif re.fullmatch(r"[#@]?[\w.-]+:[\w/.-]+", plain):
            reason = "resource identifier"
        elif re.fullmatch(r"#[\w.-]+", plain):
            reason = "Patchouli template placeholder"
        elif re.fullmatch(r"[A-Z\d\W_]+", plain) and len(plain.split()) <= 2:
            reason = "technical abbreviation or model identifier"
        elif plain.replace(" ", "_").lower() == namespace.lower() and not entry["category"] == "function_or_description":
            reason = "mod name"
        row = {"key": key, "en": english, "currentZh": entry.get("chinese"),
               "namespace": namespace, "kind": kind, "category": entry["category"]}
        if reason:
            skipped.append(dict(row, reason=reason))
        else:
            remaining[namespace].append(row)
    for namespace, values in namespace_values.items():
        target = args.source_output / "assets" / namespace / "lang/zh_cn.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n")
    upstream_meta = {
        "name": "Minecraft Mod Language Package",
        "authors": "CFPA team and contributors",
        "project": "https://github.com/CFPAOrg/Minecraft-Mod-Language-Package",
        "contributors": "https://github.com/CFPAOrg/Minecraft-Mod-Language-Package/graphs/contributors",
        "assets": upstream_assets,
        "license": "CC-BY-NC-SA-4.0",
        "licenseUrl": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "modifications": "Selected only missing or Latin-only translations for installed mods; retained existing Chinese translations.",
    }
    (args.source_output / "SOURCE.json").write_text(json.dumps(upstream_meta, ensure_ascii=False, indent=2) + "\n")
    args.batch_output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for namespace, rows in sorted(remaining.items()):
        # Description-heavy resources use smaller batches to keep reviewable
        # English input below a predictable reading budget.
        batch = []
        size = 0
        index = 1
        def emit():
            nonlocal batch, size, index
            if not batch:
                return
            filename = f"{namespace}-{index:02d}.json"
            (args.batch_output / filename).write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n")
            manifest.append({"file": filename, "namespace": namespace, "entries": len(batch), "englishCharacters": size})
            batch = []
            size = 0
            index += 1
        for row in rows:
            if batch and (len(batch) >= 100 or size + len(row["en"]) > 14000):
                emit()
            batch.append(row)
            size += len(row["en"])
        emit()
    (args.batch_output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    report = {"upstream": upstream_meta, "adoptedCount": len(adopted), "adopted": adopted,
              "translationMemoryAdopted": memory_adopted,
              "rejected": rejected, "skipped": skipped, "remainingCount": sum(map(len, remaining.values())),
              "remainingByNamespace": dict(sorted(((key, len(values)) for key, values in remaining.items()), key=lambda x: -x[1])),
              "batches": manifest,
              "upstreamPatchouliFiles": len(upstream_pages)}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"adopted": len(adopted), "translationMemoryAdopted": len(memory_adopted), "skipped": len(skipped), "remaining": report["remainingCount"],
                      "batches": len(manifest), "upstreamPatchouliFiles": len(upstream_pages),
                      "remainingByNamespace": report["remainingByNamespace"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
