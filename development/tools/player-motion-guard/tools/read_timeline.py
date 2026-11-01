#!/usr/bin/env python3
"""Read bounded local diagnostic JSONL files without uploading player data."""
from pathlib import Path
import argparse
import json
import sys
import time


def contains(value, needle):
    if isinstance(value, dict):
        return any(contains(child, needle) for child in value.values())
    if isinstance(value, list):
        return any(contains(child, needle) for child in value)
    return isinstance(value, str) and value == needle


def read_events(root, *, player=None, since_millis=0, types=(), limit=100, byte_limit=64*1024*1024):
    files = sorted((root/'events').glob('events-*.jsonl'), key=lambda path: path.stat().st_mtime, reverse=True)
    selected, selected_bytes = [], 0
    for path in files[:64]:
        size = path.stat().st_size
        if selected_bytes+size > byte_limit:
            break
        selected.append(path)
        selected_bytes += size
    records, incomplete, invalid = [], 0, 0
    for path in selected:
        with path.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'):
                    incomplete += 1
                    continue
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    invalid += 1
                    continue
                if isinstance(record, dict):
                    records.append(record)
    identities = {}
    for record in sorted(records, key=lambda item: item.get('timeMillis', 0)):
        if record.get('type') == 'player_identity':
            data = record.get('data', {})
            if data.get('playerName') and data.get('playerId'):
                identities[data['playerName']] = data['playerId']
    resolved = identities.get(player, player)
    matches = [record for record in records if record.get('timeMillis', 0) >= since_millis
               and (not types or record.get('type') in types)
               and (not resolved or contains(record.get('data'), resolved))]
    matches.sort(key=lambda item: (item.get('timeMillis', 0), item.get('bootId', ''), item.get('sequence', 0)))
    return matches[-limit:], {'scannedFiles': len(selected), 'scannedBytes': selected_bytes,
        'boundedScan': len(selected) < len(files), 'incompleteTailLinesIgnored': incomplete,
        'invalidLinesIgnored': invalid, 'matchedRecords': len(matches), 'returnedRecords': min(limit, len(matches)),
        'identities': identities, 'resolvedPlayer': resolved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Local expedition-diagnostics directory')
    parser.add_argument('--player', help='Exact player UUID, or name present in retained identity events')
    parser.add_argument('--since-seconds', type=int, default=900)
    parser.add_argument('--type', action='append', default=[], help='Exact event type; may be repeated')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--max-mib', type=int, default=64)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000 or not 1 <= args.max_mib <= 512 or args.since_seconds < 0:
        parser.error('limit must be 1..10000, max-mib 1..512, since-seconds nonnegative')
    root = args.root.expanduser().resolve()
    if not (root/'events').is_dir():
        parser.error('Missing events directory: '+str(root/'events'))
    records, report = read_events(root, player=args.player,
        since_millis=int((time.time()-args.since_seconds)*1000) if args.since_seconds else 0,
        types=args.type, limit=args.limit, byte_limit=args.max_mib*1024*1024)
    for record in records:
        print(json.dumps(record, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps({'scan':report}, ensure_ascii=False), file=sys.stderr)


if __name__ == '__main__':
    main()
