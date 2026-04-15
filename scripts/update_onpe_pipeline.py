#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TRACKING = DATA / 'tracking.json'
ONPE_LIVE = DATA / 'onpe_live.json'
PREDICTIONS = DATA / 'predictions.json'
STATE = DATA / 'latest' / 'pipeline_state.json'


def load_json(path: Path):
    return json.loads(path.read_text())


def run(script: str):
    subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], cwd=ROOT, check=True)


def current_signature():
    tracking = load_json(TRACKING)
    onpe = load_json(ONPE_LIVE)
    last_cut = (tracking.get('cuts') or [{}])[-1]
    return {
        'lastUpdate': onpe.get('lastUpdate') or tracking.get('lastUpdate'),
        'nationalPct': float(onpe.get('nationalPct') or tracking.get('nationalPct') or 0),
        'cutPct': float(last_cut.get('pct') or 0),
        'cut': last_cut,
    }


def load_previous_state():
    if not STATE.exists():
        return None
    try:
        return load_json(STATE)
    except Exception:
        return None


def main():
    sig = current_signature()
    prev = load_previous_state()
    changed = (not prev) or any(prev.get(k) != sig.get(k) for k in ['lastUpdate', 'nationalPct', 'cutPct'])

    if not changed:
        print(json.dumps({'updated': False, 'reason': 'no_new_cut', 'signature': sig}, ensure_ascii=False, indent=2))
        return

    run('store_onpe_snapshot.py')
    run('build_onpe_latest.py')
    run('build_model_input.py')
    run('build_predictions.py')

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(sig, ensure_ascii=False, indent=2))

    predictions = load_json(PREDICTIONS)
    print(json.dumps({
        'updated': True,
        'signature': sig,
        'predictionsGeneratedAt': predictions.get('generatedAt'),
        'probabilities': predictions.get('secondRoundProbabilities'),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
