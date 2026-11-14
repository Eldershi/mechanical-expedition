#!/usr/bin/env python3
"""Audit effective Minecraft language resources and Patchouli page coverage."""

import argparse
from collections import Counter, defaultdict
from io import BytesIO
import json
from pathlib import Path
import re
import tomllib
from zipfile import ZipFile, BadZipFile


HAN = re.compile(r"[\u3400-\u9fff]")
LATIN_WORD = re.compile(r"[A-Za-z]{3,}")
LANG = re.compile(r"^assets/([^/]+)/lang/(en_us|zh_cn)\.json$")
PAGE = re.compile(r"^(assets|data)/([^/]+)/patchouli_books/([^/]+)/(en_us|zh_cn)/(.+\.json)$")
FUNCTION = re.compile(r"tooltip|description|\.desc(?:\.|$)|\.info(?:\.|$)|ability|effect|weapon|armor|armour|enchant|spell|\.lore(?:\.|$)|instruction|usage|\.tip(?:\.|$)", re.I)
DISPLAY_FIELDS = {"name", "text", "title", "subtitle", "description", "link_text", "caption",
                  "header", "heading", "flavor", "label", "button_text", "tooltip", "landing_text"}


def load_json(raw):
    text = raw.decode("utf-8-sig")
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        # Several shipped language files use Gson's accepted trailing commas.
        return json.loads(re.sub(r",\s*([}\]])", r"\1", text), strict=False)


def classify(key, english):
    if FUNCTION.search(key):
        return "function_or_description"
    if key.startswith(("item.", "block.", "entity.", "fluid.", "enchantment.", "effect.")):
        return "name"
    if any(x in key.lower() for x in ("config", "option", "key.", "keybind")):
        return "configuration_or_keybind"
    return "interface_or_other"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-output", type=Path)
    parser.add_argument("--page-jobs-output", type=Path)
    parser.add_argument("--effective-language-output", type=Path)
    parser.add_argument("--extra-pack", type=Path, action="append", default=[])
    args = parser.parse_args()
    instance = args.instance.resolve()
    languages = {"en_us": {}, "zh_cn": {}}
    origins = {"en_us": {}, "zh_cn": {}}
    pages = {"en_us": {}, "zh_cn": {}}
    errors = []
    sources = []
    installed_namespaces = set()
    loaded_mod_ids = {"minecraft", "forge"}

    def ingest(name, raw, source):
        language = LANG.match(name)
        page = PAGE.match(name)
        if not language and not page:
            return
        try:
            data = load_json(raw)
        except (ValueError, UnicodeError) as exc:
            errors.append({"source": source, "resource": name, "error": str(exc)})
            return
        if language:
            namespace, locale = language.groups()
            if not isinstance(data, dict):
                errors.append({"source": source, "resource": name, "error": "Language resource is not an object"})
                return
            for key, value in data.items():
                if isinstance(value, str):
                    languages[locale][key] = value
                    origins[locale][key] = {"source": source, "namespace": namespace, "resource": name}
        if page:
            domain, namespace, book, locale, relative = page.groups()
            identity = namespace + ":" + book + "/" + relative
            pages[locale][identity] = {"source": source, "resource": name, "data": data}

    def read_zip(archive, source, nested=False):
        for name in archive.namelist():
            if name in {"META-INF/mods.toml", "META-INF/neoforge.mods.toml", "fabric.mod.json"}:
                metadata = archive.read(name).decode("utf-8", errors="replace")
                if name.endswith(".toml"):
                    try:
                        loaded_mod_ids.update(row["modId"] for row in tomllib.loads(metadata).get("mods", []) if "modId" in row)
                    except (ValueError, TypeError):
                        for block in re.findall(r"(?ms)^\s*\[\[mods\]\](.*?)(?=^\s*\[|\Z)", metadata):
                            loaded_mod_ids.update(re.findall(r"(?m)^\s*modId\s*=\s*[\"']([^\"']+)[\"']", block))
                else:
                    try:
                        loaded_mod_ids.add(json.loads(metadata)["id"])
                    except (ValueError, KeyError):
                        pass
            if LANG.match(name) or PAGE.match(name):
                if source.startswith("mods/") and LANG.match(name):
                    installed_namespaces.add(LANG.match(name).group(1))
                ingest(name, archive.read(name), source)
            elif not nested and name.startswith("META-INF/jarjar/") and name.endswith(".jar"):
                try:
                    with ZipFile(BytesIO(archive.read(name))) as embedded:
                        read_zip(embedded, source + "!" + name.rsplit("/", 1)[-1], nested=True)
                except BadZipFile:
                    errors.append({"source": source, "resource": name, "error": "Invalid embedded JAR"})

    def read_source(path, source):
        sources.append(source)
        if path.is_dir():
            for folder in ("assets", "data"):
                root = path / folder
                if root.exists():
                    for file in sorted(root.rglob("*.json")):
                        name = file.relative_to(path).as_posix()
                        if LANG.match(name) or PAGE.match(name):
                            ingest(name, file.read_bytes(), source)
        else:
            try:
                with ZipFile(path) as archive:
                    read_zip(archive, source)
            except BadZipFile:
                errors.append({"source": source, "error": "Invalid ZIP/JAR"})

    mods = sorted((instance / "mods").glob("*.jar"))
    for jar in mods:
        read_source(jar, "mods/" + jar.name)
    # KubeJS supplies its generated pack as part of mod resources. Explicit
    # packs later in options.txt may replace these same keys.
    if (instance / "kubejs/assets").exists():
        read_source(instance / "kubejs", "kubejs")
    configured = []
    options = instance / "options.txt"
    if options.exists():
        for line in options.read_text().splitlines():
            if line.startswith("resourcePacks:"):
                configured = json.loads(line.split(":", 1)[1])
                break
    if not configured:
        paxi = instance / "config/paxi/resourcepack_load_order.json"
        if paxi.exists():
            configured = json.loads(paxi.read_text()).get("loadOrder", [])
    unresolved = []
    for pack in configured:
        name = pack.removeprefix("file/")
        found = False
        for folder in ("resourcepacks", "config/paxi/resourcepacks"):
            path = instance / folder / name
            if path.exists():
                read_source(path, folder + "/" + name)
                found = True
                break
        if not found and pack not in {"vanilla", "mod_resources"}:
            unresolved.append(pack)
    for pack in args.extra_pack:
        read_source(pack, "extra/" + pack.name)

    missing = []
    english_as_chinese = []
    by_namespace = defaultdict(Counter)
    for key, english in languages["en_us"].items():
        origin = origins["en_us"][key]
        namespace = origin["namespace"]
        by_namespace[namespace]["englishKeys"] += 1
        chinese = languages["zh_cn"].get(key)
        if chinese is not None:
            by_namespace[namespace]["chineseKeys"] += 1
        if not english.strip() or not LATIN_WORD.search(english):
            continue
        row = {"key": key, "english": english, "namespace": namespace,
               "category": classify(key, english), "englishSource": origin["source"]}
        if chinese is None or not chinese.strip():
            missing.append(row)
            by_namespace[namespace]["missing"] += 1
        elif not HAN.search(chinese) and LATIN_WORD.search(chinese):
            row.update(chinese=chinese, chineseSource=origins["zh_cn"][key]["source"], sameAsEnglish=chinese == english)
            english_as_chinese.append(row)
            by_namespace[namespace]["latinOnlyChinese"] += 1

    def page_strings(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in DISPLAY_FIELDS and isinstance(item, str):
                    yield item
                elif isinstance(item, (dict, list)):
                    yield from page_strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from page_strings(item)

    patchouli_missing = []
    patchouli_latin = []
    page_jobs = []
    def readable(value):
        # With i18n enabled, Patchouli page fields contain language keys, and
        # localized pages are unnecessary when zh_cn.lang translates them.
        if value in languages["zh_cn"]:
            return languages["zh_cn"][value]
        return languages["en_us"].get(value, value)

    for identity, entry in pages["en_us"].items():
        strings = [readable(s) for s in page_strings(entry["data"])]
        strings = [s for s in strings if LATIN_WORD.search(s)]
        if not strings:
            continue
        if identity not in pages["zh_cn"]:
            # An explicitly Chinese English fallback file is already readable.
            if any(not HAN.search(s) for s in strings):
                patchouli_missing.append({"page": identity, "source": entry["source"], "strings": strings})
        else:
            candidates = [readable(s) for s in page_strings(pages["zh_cn"][identity]["data"])]
            candidates = [s for s in candidates
                          if LATIN_WORD.search(s) and not HAN.search(s)]
            if candidates:
                patchouli_latin.append({"page": identity, "source": pages["zh_cn"][identity]["source"], "strings": candidates})
        base = pages["zh_cn"].get(identity, entry)
        jobs = []
        def fields(value, path=()):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in DISPLAY_FIELDS and isinstance(item, str):
                        display = readable(item)
                        # Language-key fields remain references. Literal prose
                        # fields can be safely localized without changing links,
                        # recipe IDs, advancement gates or custom page types.
                        visible = re.sub(r"\$\([^)]*\)", "", display)
                        if (item == display and LATIN_WORD.search(visible) and not HAN.search(visible)
                                and not re.fullmatch(r"#[\w.]+#?", visible)
                                and not re.fullmatch(r"[\w-]+(?:\.[\w-]+){2,}", visible)):
                            jobs.append({"path": list(path + (key,)), "en": item})
                    elif isinstance(item, (dict, list)):
                        fields(item, path + (key,))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    fields(item, path + (index,))
        fields(base["data"])
        if jobs:
            page_jobs.append({"identity": identity, "resource": re.sub(r"/(en_us|zh_cn)/", "/zh_cn/", base["resource"]),
                              "source": base["source"], "data": base["data"], "fields": jobs})

    report = {
        "schemaVersion": 1,
        "scope": "Effective mod language files, KubeJS assets and configured resource packs; Patchouli localized JSON pages. Hard-coded Java strings and non-Patchouli manual formats require separate review.",
        "modJarCount": len(mods), "sourceCount": len(sources), "sources": sources,
        "loadedModIds": sorted(loaded_mod_ids), "installedResourceNamespaces": sorted(installed_namespaces),
        "unresolvedBuiltinPacks": unresolved, "parseErrors": errors,
        "summary": {"englishKeys": len(languages["en_us"]), "chineseKeys": len(languages["zh_cn"]),
                    "missing": len(missing), "latinOnlyChinese": len(english_as_chinese),
                    "missingFunctional": sum(x["category"] == "function_or_description" for x in missing),
                    "latinOnlyFunctional": sum(x["category"] == "function_or_description" for x in english_as_chinese),
                    "patchouliEnglishPages": len(pages["en_us"]), "patchouliChinesePages": len(pages["zh_cn"]),
                    "patchouliMissingLocalizedPages": len(patchouli_missing), "patchouliLatinOnlyLocalizedPages": len(patchouli_latin)},
        "byNamespace": {k: dict(v) for k, v in sorted(by_namespace.items())},
        "missing": missing, "latinOnlyChinese": english_as_chinese,
        "patchouliMissingLocalizedPages": patchouli_missing, "patchouliLatinOnlyLocalizedPages": patchouli_latin,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.memory_output:
        choices = defaultdict(dict)
        for key, english in languages["en_us"].items():
            chinese = languages["zh_cn"].get(key)
            if chinese and HAN.search(chinese):
                choices[english][chinese] = {"key": key, **origins["zh_cn"][key]}
        memory = {english: {"zh": next(iter(values)), "source": next(iter(values.values()))}
                  for english, values in choices.items() if len(values) == 1}
        args.memory_output.write_text(json.dumps(memory, ensure_ascii=False, indent=2) + "\n")
    if args.page_jobs_output:
        args.page_jobs_output.write_text(json.dumps(page_jobs, ensure_ascii=False, indent=2) + "\n")
    if args.effective_language_output:
        args.effective_language_output.write_text(json.dumps({
            "en_us": languages["en_us"], "zh_cn": languages["zh_cn"], "origins": origins,
        }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("Largest untranslated namespaces:")
    for namespace, count in sorted(by_namespace.items(), key=lambda pair: pair[1]["missing"] + pair[1]["latinOnlyChinese"], reverse=True)[:30]:
        print(namespace, dict(count))


if __name__ == "__main__":
    main()
