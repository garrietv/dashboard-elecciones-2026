#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TRACKING = DATA / 'tracking.json'
ONPE_LIVE = DATA / 'onpe_live.json'
OUT = DATA / 'model_input.json'


def main():
    tracking = json.loads(TRACKING.read_text())
    onpe_live = json.loads(ONPE_LIVE.read_text())
    cuts = tracking.get('cuts', [])
    latest_cut = max(cuts, key=lambda c: float(c.get('pct') or 0)) if cuts else {}
    model_input = {
        'source': 'canonical-model-input-v1',
        'tracking': {
            'lastUpdate': tracking.get('lastUpdate'),
            'nationalPct': tracking.get('nationalPct'),
            'latestCut': latest_cut,
            'cuts': cuts,
        },
        'onpeLive': {
            'lastUpdate': onpe_live.get('lastUpdate'),
            'nationalPct': onpe_live.get('nationalPct'),
            'totalActas': onpe_live.get('totalActas'),
            'actasContabilizadas': onpe_live.get('actasContabilizadas'),
            'regions': onpe_live.get('regions', []),
        },
        'canonical': {
            'nationalPct': onpe_live.get('nationalPct') if onpe_live.get('nationalPct') is not None else latest_cut.get('pct'),
            'trackingPct': latest_cut.get('pct'),
            'livePct': onpe_live.get('nationalPct'),
            'trackingLastUpdate': latest_cut.get('ts') or tracking.get('lastUpdate'),
            'liveLastUpdate': onpe_live.get('lastUpdate'),
        }
    }
    OUT.write_text(json.dumps(model_input, ensure_ascii=False, indent=2))
    print(json.dumps(model_input['canonical'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
