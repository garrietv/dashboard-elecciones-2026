#!/usr/bin/env python3
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TRACKING = DATA / 'tracking.json'
ONPE = DATA / 'onpe_live.json'
WORKER_URL = 'https://onpe-proxy.renzonunez-af.workers.dev'


def fetch_json(path, params=None):
    qs = '?' + urlencode(params or {}) if params else ''
    req = Request(WORKER_URL + path + qs, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def build_tracking():
    data = fetch_json('/api/tracking')
    cuts = data.get('cuts', [])
    if cuts:
        latest_cut = max(cuts, key=lambda c: float(c.get('pct') or 0))
    else:
        latest_cut = {}
    payload = {
        'lastUpdate': latest_cut.get('ts'),
        'nationalPct': latest_cut.get('pct'),
        'cuts': cuts,
        'count': data.get('count')
    }
    TRACKING.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    (ROOT / 'tracking.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def normalize_region(r):
    return {
        'name': r['name'],
        'pctActas': r.get('pct'),
        'vv': r.get('vv'),
        'fujimori': {'pct': r.get('fuji'), 'v': round((r.get('vv') or 0) * (r.get('fuji') or 0) / 100)},
        'rla': {'pct': r.get('rla'), 'v': round((r.get('vv') or 0) * (r.get('rla') or 0) / 100)},
        'nieto': {'pct': r.get('nieto'), 'v': round((r.get('vv') or 0) * (r.get('nieto') or 0) / 100)},
        'belmont': {'pct': r.get('belm'), 'v': round((r.get('vv') or 0) * (r.get('belm') or 0) / 100)},
        'sanchez': {'pct': r.get('sanch'), 'v': round((r.get('vv') or 0) * (r.get('sanch') or 0) / 100)},
    }


def build_onpe_live():
    half1 = fetch_json('/api/snapshot', {'half': 1})
    half2 = fetch_json('/api/snapshot', {'half': 2})
    regions = [normalize_region(r) for r in ((half1.get('regions') or []) + (half2.get('regions') or []))]
    national = half1.get('national') or {}
    payload = {
        'lastUpdate': half1.get('timestamp') or national.get('timestamp'),
        'nationalPct': national.get('pct'),
        'totalActas': national.get('totalActas'),
        'actasContabilizadas': national.get('contabilizadas'),
        'regions': regions,
    }
    ONPE.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main():
    tracking = build_tracking()
    onpe = build_onpe_live()
    print(json.dumps({
        'worker': WORKER_URL,
        'trackingCuts': len(tracking.get('cuts', [])),
        'nationalPct': onpe.get('nationalPct'),
        'regions': len(onpe.get('regions', []))
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
