#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const snbt = require("../../../tools/quest-workbench/editor/snbt.js");

const anchorTexture = "quest_enhance:textures/icons/decorative_anchor.png";
const anchorPrefix = "quest_enhance:decorative_anchor:";
const lineField = "quest_enhance_decorative_lines";
const nodeKey = (kind, id) => `${kind}:${BigInt(`0x${id}`).toString(16)}`;
const position = ({x, y}) => `${snbt.asNumber(x)},${snbt.asNumber(y)}`;

function anchorId(image) {
    const data = image.click_action?.replace(/^none:/, "") ?? image.click;
    return data?.startsWith(anchorPrefix) ? `a:${data.slice(anchorPrefix.length)}` : undefined;
}

function readChapters(directory) {
    return fs.readdirSync(directory).filter(name => name.endsWith(".snbt")).sort().map(name => {
        const text = fs.readFileSync(path.join(directory, name), "utf8");
        const chapter = snbt.parse(text);
        const anchors = (chapter.images ?? []).filter(image => image.image === anchorTexture);
        const nodes = new Map();
        for (const [kind, field] of [["q", "quests"], ["l", "quest_links"]]) {
            for (const node of chapter[field] ?? []) nodes.set(nodeKey(kind, node.id), node);
        }
        const lines = chapter[lineField] ?? [];
        return {name, text, chapter, anchors, nodes, lines, refs: new Set(lines.flatMap(line => line.nodes))};
    });
}

function chooseReference(target, references) {
    const scoring = reference => {
        const ids = reference.anchors.map(anchorId).filter(Boolean);
        const shared = ids.filter(id => target.refs.has(id)).length;
        const matchingNodes = [...reference.nodes.keys()].filter(id => target.refs.has(id)).length;
        const sameName = reference.name.replaceAll("-", "") === target.name.replaceAll("-", "");
        return 4 * shared + 2 * matchingNodes + Number(sameName);
    };
    return [...references].sort((a, b) => scoring(b) - scoring(a))[0];
}

function restore(target, reference) {
    const idsByPosition = new Map();
    for (const image of reference.anchors) {
        const id = anchorId(image);
        if (!id || !target.refs.has(id)) continue;
        const coordinate = position(image);
        if (!idsByPosition.has(coordinate)) idsByPosition.set(coordinate, []);
        idsByPosition.get(coordinate).push(id);
    }
    const recorded = new Set(target.anchors.map(anchorId).filter(Boolean));
    const available = new Set(target.nodes.keys());
    let restored = 0;
    for (const image of target.anchors) {
        const id = anchorId(image) ?? idsByPosition.get(position(image))?.find(ref => !recorded.has(ref));
        if (!id) continue;
        const action = `none:${anchorPrefix}${id.slice(2)}`;
        if (image.click_action !== action || image.click !== undefined) restored++;
        image.click_action = action;
        delete image.click;
        available.add(id);
        recorded.add(id);
    }

    // A separately serialized copy can have all new quest IDs while retaining its original canvas.
    const remap = new Map();
    for (const kind of ["q:", "l:"]) {
        const entries = chapter => [...chapter.nodes].filter(([id]) => id.startsWith(kind));
        const original = entries(reference);
        const current = entries(target);
        const byPosition = new Map(current.map(([id, node]) => [position(node), id]));
        const sameCanvas = original.length === current.length && byPosition.size === current.length
            && original.every(([, node]) => byPosition.has(position(node)));
        if (sameCanvas && original.every(([id]) => !target.nodes.has(id))) {
            for (const [id, node] of original) remap.set(id, byPosition.get(position(node)));
        }
    }

    const lines = target.lines.map(line => ({...line, nodes: line.nodes.map(id => remap.get(id) ?? id)}));
    let connected = lines.filter(line => line.nodes.every(id => available.has(id)));
    // Remove the remaining fragments of routes whose quests or links were removed from this chapter.
    let length;
    do {
        length = connected.length;
        const starts = new Set(connected.map(line => line.nodes[0]));
        const ends = new Set(connected.map(line => line.nodes.at(-1)));
        connected = connected.filter(line => {
            const start = line.nodes[0], end = line.nodes.at(-1);
            return (!start.startsWith("a:") || ends.has(start)) && (!end.startsWith("a:") || starts.has(end));
        });
    } while (connected.length !== length);

    let text = target.text;
    if (restored) text = replaceList(text, "images", target.chapter.images);
    if (JSON.stringify(connected) !== JSON.stringify(target.lines)) text = replaceList(text, lineField, connected);
    if (text === target.text) return undefined;
    const result = snbt.parse(text);
    assert.equal(JSON.stringify(result), JSON.stringify({...target.chapter, [lineField]: connected}), target.name);
    return {text, restored, remapped: remap.size, removedSegments: lines.length - connected.length};
}

function replaceList(text, field, entries) {
    const list = new RegExp(`^\\t${field}: \\[[^\\n]*\\n[\\s\\S]*?^\\t\\}?\\]$`, "m");
    assert.match(text, list, `Could not locate ${field}`);
    return text.replace(list, () => `\t${field}: ${snbt.stringify(entries, 1)}`);
}

const [targetDirectory, outputDirectory, ...referenceDirectories] = process.argv.slice(2);
assert(targetDirectory && outputDirectory && referenceDirectories.length,
    "Usage: restore_anchors.js TARGET_CHAPTERS OUTPUT_DIR REFERENCE_CHAPTERS [REFERENCE_CHAPTERS ...]");
const targets = readChapters(targetDirectory);
const references = referenceDirectories.flatMap(readChapters);
fs.mkdirSync(outputDirectory, {recursive: true});
for (const target of targets.filter(chapter => chapter.lines.length
    && (chapter.anchors.length || /^(research_|staged_|expedition_)/.test(chapter.name)))) {
    const reference = chooseReference(target, references);
    assert(reference, `No research reference for ${target.name}`);
    const output = restore(target, reference);
    if (!output) continue;
    fs.writeFileSync(path.join(outputDirectory, target.name), output.text);
    const {text, ...stats} = output;
    console.log(JSON.stringify({chapter: target.name, ...stats}));
}
