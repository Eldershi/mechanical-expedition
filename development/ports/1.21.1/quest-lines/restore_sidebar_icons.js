#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const snbt = require("../../../tools/quest-workbench/editor/snbt.js");
const icons = require("./sidebar_icons.json");

const [input, output] = process.argv.slice(2);
assert(input && output, "Usage: restore_sidebar_icons.js INPUT_CHAPTERS OUTPUT_DIR");
fs.mkdirSync(output, {recursive: true});
for (const file of fs.readdirSync(input).filter(name => name.endsWith(".snbt")).sort()) {
    const text = fs.readFileSync(path.join(input, file), "utf8");
    const chapter = snbt.parse(text);
    const name = path.basename(file, ".snbt");
    const icon = icons[name] ?? (typeof chapter.icon === "string" ? chapter.icon : undefined);
    if (!icon || chapter.icon?.id === icon) continue;

    // FTB Quests reads a single item from a compound and otherwise animates the quest icons.
    const field = /^(\t| {2})("icon"|icon): (?:"[^"\n]*"|\{[^\n]*\}|\{\n[\s\S]*?^\1\})(,?)$/m;
    const idField = /^(\t| {2})("id"|id): "[A-Fa-f0-9]+"(,?)$/m;
    const item = `{ id: "${icon}" }`;
    const changed = text.replace(field, (_, indent, key, comma) => `${indent}${key}: ${item}${comma}`);
    const updated = changed !== text ? changed : text.replace(idField, (line, indent, key, comma) => {
        const iconKey = key === '"id"' ? '"icon"' : "icon";
        return `${indent}${iconKey}: ${item}${comma}\n${line}`;
    });
    const parsed = snbt.parse(updated);
    assert.deepEqual({...parsed}, {...chapter, icon: snbt.parse(item)}, file);
    fs.writeFileSync(path.join(output, file), updated);
    console.log(`${file} ${icon}`);
}
