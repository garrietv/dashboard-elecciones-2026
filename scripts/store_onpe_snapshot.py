#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SNAPSHOTS = DATA / 'onpe_snapshots'
NORMALIZED = DATA / 'normalized'
LATEST = DATA / 'latest'
TRACKING = DATA / 'tracking.json'
ONPE_LIVE = DATA / 'onpe_live.json'
TRACKING_ROOT = ROOT / 'tracking.json'

SNAPSHOTS.mkdir(parents=True, exist_ok=True)
NORMALIZED.mkdir(parents=True, exist_ok=True)
LATEST.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    return json.loads(path.read_text())


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def snapshot_name(ts: str, pct: float) -> str:
    safe_ts = ts.replace(':', '-').replace('T', '_')
    return f"{safe_ts}_{pct:.3f}.json"


def main():
    tracking = load_json(TRACKING)
    onpe_live = load_json(ONPE_LIVE)

    ts = onpe_live.get('lastUpdate') or tracking.get('lastUpdate') or datetime.now().astimezone().isoformat(timespec='seconds')
    pct = float(onpe_live.get('nationalPct') or tracking.get('nationalPct') or 0)

    raw_snapshot = {
        'capturedAt': datetime.now().astimezone().isoformat(timespec='seconds'),
        'sourceLastUpdate': ts,
        'nationalPct': pct,
        'tracking': tracking,
        'regional': onpe_live,
    }

    normalized = {
        'capturedAt': raw_snapshot['capturedAt'],
        'sourceLastUpdate': ts,
        'nationalPct': pct,
        'lastCut': tracking['cuts'][-1] if tracking.get('cuts') else None,
        'cuts': tracking.get('cuts', []),
        'regions': onpe_live.get('regions', []),
        'totalActas': onpe_live.get('totalActas'),
        'actasContabilizadas': onpe_live.get('actasContabilizadas'),
    }

    name = snapshot_name(ts, pct)
    save_json(SNAPSHOTS / name, raw_snapshot)
    save_json(NORMALIZED / name, normalized)
    save_json(LATEST / 'onpe_latest.json', normalized)
    save_json(LATEST / 'onpe_latest_raw.json', raw_snapshot)

    history_path = DATA / 'onpe_tracking_history.jsonl'
    with history_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps({
            'capturedAt': raw_snapshot['capturedAt'],
            'sourceLastUpdate': ts,
            'nationalPct': pct,
            'lastCut': normalized['lastCut'],
        }, ensure_ascii=False) + '\n')

    if TRACKING_ROOT.exists():
        TRACKING_ROOT.write_text(TRACKING.read_text())

    print(json.dumps({
        'savedSnapshot': str(SNAPSHOTS / name),
        'savedNormalized': str(NORMALIZED / name),
        'latest': str(LATEST / 'onpe_latest.json'),
        'nationalPct': pct,
        'sourceLastUpdate': ts,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
