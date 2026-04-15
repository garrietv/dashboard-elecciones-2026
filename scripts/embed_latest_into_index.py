#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'
TRACKING = ROOT / 'data' / 'tracking.json'
ONPE = ROOT / 'data' / 'onpe_live.json'


def js_obj_from_tracking(data):
    return "const TRACKING = " + json.dumps(data, ensure_ascii=False, indent=2) + ";"


def js_obj_from_onpe(onpe):
    regions = []
    for r in onpe.get('regions', []):
        regions.append({
            'name': r['name'],
            'pct': round(float(r.get('pctActas', 0)), 1),
            'vv': int(r.get('vv', 0)),
            'fuji': round(float(r.get('fujimori', {}).get('pct', 0)), 2),
            'rla': round(float(r.get('rla', {}).get('pct', 0)), 2),
            'nieto': round(float(r.get('nieto', {}).get('pct', 0)), 2),
            'belm': round(float(r.get('belmont', {}).get('pct', 0)), 2),
            'sanch': round(float(r.get('sanchez', {}).get('pct', 0)), 2),
        })
    return "const ONPE_REGIONS = " + json.dumps(regions, ensure_ascii=False, indent=2) + ";"


def replace_block(text, const_name, new_block):
    pattern = rf"const {const_name} = .*?;\n\n"
    return re.sub(pattern, new_block + "\n\n", text, count=1, flags=re.S)


def main():
    tracking = json.loads(TRACKING.read_text())
    onpe = json.loads(ONPE.read_text())
    text = INDEX.read_text()
    text = replace_block(text, 'TRACKING', js_obj_from_tracking(tracking))
    text = replace_block(text, 'ONPE_REGIONS', js_obj_from_onpe(onpe))
    INDEX.write_text(text)
    print(json.dumps({
        'updated': str(INDEX),
        'nationalPct': onpe.get('nationalPct') or tracking.get('nationalPct'),
        'cuts': len(tracking.get('cuts', [])),
        'regions': len(onpe.get('regions', []))
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
