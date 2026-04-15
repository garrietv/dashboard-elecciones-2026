#!/usr/bin/env python3
import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DB = DATA / 'onpe_history.db'
TRACKING = DATA / 'tracking.json'
ONPE_LIVE = DATA / 'onpe_live.json'
MODEL_INPUT = DATA / 'model_input.json'
PREDICTIONS = DATA / 'predictions.json'


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def unique_key(tracking, onpe_live):
    last_cut = (tracking.get('cuts') or [{}])[-1]
    parts = [
        str(onpe_live.get('lastUpdate') or ''),
        str(onpe_live.get('nationalPct') or ''),
        str(last_cut.get('ts') or ''),
        str(last_cut.get('pct') or ''),
    ]
    return '|'.join(parts)


def main():
    tracking = load_json(TRACKING, {})
    onpe_live = load_json(ONPE_LIVE, {})
    model_input = load_json(MODEL_INPUT)
    predictions = load_json(PREDICTIONS)

    if not tracking or not onpe_live:
        raise SystemExit('tracking.json or onpe_live.json missing')

    key = unique_key(tracking, onpe_live)
    captured_at = datetime.now().astimezone().isoformat(timespec='seconds')
    cuts = tracking.get('cuts') or []
    last_cut = cuts[-1] if cuts else {}
    canonical = (model_input or {}).get('canonical', {})
    probs = (predictions or {}).get('secondRoundProbabilities', {})

    conn = sqlite3.connect(DB)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        cur = conn.cursor()
        cur.execute(
            '''INSERT OR IGNORE INTO captures (
                captured_at, source_last_update, national_pct, total_actas, actas_contabilizadas,
                tracking_last_update, tracking_pct, live_last_update, live_pct, tracking_count,
                raw_tracking_json, raw_onpe_live_json, model_input_json, predictions_json, unique_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                captured_at,
                onpe_live.get('lastUpdate') or tracking.get('lastUpdate'),
                onpe_live.get('nationalPct') or tracking.get('nationalPct'),
                onpe_live.get('totalActas'),
                onpe_live.get('actasContabilizadas'),
                canonical.get('trackingLastUpdate') or tracking.get('lastUpdate') or last_cut.get('ts'),
                canonical.get('trackingPct') or last_cut.get('pct'),
                canonical.get('liveLastUpdate') or onpe_live.get('lastUpdate'),
                canonical.get('livePct') or onpe_live.get('nationalPct'),
                tracking.get('count') or len(cuts),
                json.dumps(tracking, ensure_ascii=False),
                json.dumps(onpe_live, ensure_ascii=False),
                json.dumps(model_input, ensure_ascii=False) if model_input else None,
                json.dumps(predictions, ensure_ascii=False) if predictions else None,
                key,
            )
        )
        conn.commit()
        cur.execute('SELECT id FROM captures WHERE unique_key = ?', (key,))
        row = cur.fetchone()
        capture_id = row[0]

        cur.execute('DELETE FROM tracking_cuts WHERE capture_id = ?', (capture_id,))
        for c in cuts:
            cur.execute(
                '''INSERT INTO tracking_cuts (
                    capture_id, ts, pct, fujimori, rla, nieto, belmont, sanchez, jee, contabilizadas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    capture_id, c.get('ts'), c.get('pct'), c.get('fujimori'), c.get('rla'),
                    c.get('nieto'), c.get('belmont'), c.get('sanchez'), c.get('jee'), c.get('contabilizadas')
                )
            )

        cur.execute('DELETE FROM regional_results WHERE capture_id = ?', (capture_id,))
        for r in onpe_live.get('regions', []):
            cur.execute(
                '''INSERT INTO regional_results (
                    capture_id, region_name, pct_actas, vv,
                    fujimori_pct, fujimori_votes, rla_pct, rla_votes, nieto_pct, nieto_votes,
                    belmont_pct, belmont_votes, sanchez_pct, sanchez_votes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    capture_id, r.get('name'), r.get('pctActas'), r.get('vv'),
                    (r.get('fujimori') or {}).get('pct'), (r.get('fujimori') or {}).get('v'),
                    (r.get('rla') or {}).get('pct'), (r.get('rla') or {}).get('v'),
                    (r.get('nieto') or {}).get('pct'), (r.get('nieto') or {}).get('v'),
                    (r.get('belmont') or {}).get('pct'), (r.get('belmont') or {}).get('v'),
                    (r.get('sanchez') or {}).get('pct'), (r.get('sanchez') or {}).get('v'),
                )
            )

        if predictions:
            cur.execute('DELETE FROM prediction_runs WHERE capture_id = ?', (capture_id,))
            cur.execute(
                '''INSERT INTO prediction_runs (
                    capture_id, generated_at, national_pct, live_pct, tracking_pct,
                    rla_prob, nieto_prob, sanchez_prob, belmont_prob, source,
                    probabilities_json, projection_table_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    capture_id,
                    predictions.get('generatedAt'),
                    predictions.get('nationalPct'),
                    canonical.get('livePct'),
                    canonical.get('trackingPct'),
                    probs.get('rla'), probs.get('nieto'), probs.get('sanchez'), probs.get('belmont'),
                    predictions.get('source'),
                    json.dumps(probs, ensure_ascii=False),
                    json.dumps(predictions.get('projectionTable'), ensure_ascii=False),
                )
            )

        conn.commit()
        print(json.dumps({'captureId': capture_id, 'uniqueKey': key, 'cuts': len(cuts), 'regions': len(onpe_live.get('regions', [])), 'hasPredictions': bool(predictions)}, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
