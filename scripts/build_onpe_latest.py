#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
LATEST = DATA / 'latest'
TRACKING = DATA / 'tracking.json'
ONPE_LIVE = DATA / 'onpe_live.json'
ROOT_TRACKING = ROOT / 'tracking.json'


def main():
    tracking = json.loads(TRACKING.read_text())
    onpe_live = json.loads(ONPE_LIVE.read_text())
    latest = {
        'lastUpdate': onpe_live.get('lastUpdate') or tracking.get('lastUpdate'),
        'nationalPct': onpe_live.get('nationalPct') or tracking.get('nationalPct'),
        'lastCut': tracking['cuts'][-1] if tracking.get('cuts') else None,
        'cuts': tracking.get('cuts', []),
        'regions': onpe_live.get('regions', []),
        'references': tracking.get('references', {}),
    }
    LATEST.mkdir(parents=True, exist_ok=True)
    (LATEST / 'onpe_latest.json').write_text(json.dumps(latest, ensure_ascii=False, indent=2))
    ROOT_TRACKING.write_text(TRACKING.read_text())
    print(json.dumps({'latest': str(LATEST / 'onpe_latest.json'), 'nationalPct': latest['nationalPct']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
