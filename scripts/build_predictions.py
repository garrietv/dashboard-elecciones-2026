#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKING = ROOT / 'data' / 'tracking.json'
ONPE_LIVE = ROOT / 'data' / 'onpe_live.json'
MODEL_INPUT = ROOT / 'data' / 'model_input.json'
OUT = ROOT / 'data' / 'predictions.json'

CANDS = ['fujimori', 'rla', 'nieto', 'sanchez', 'belmont']
LABELS = {
    'fujimori': ('fuji', 'Fujimori'),
    'rla': ('rla', 'López Aliaga'),
    'nieto': ('nieto', 'Nieto'),
    'sanchez': ('sanch', 'Sánchez'),
    'belmont': ('belm', 'Belmont'),
}
SECOND_ROUND = ['rla', 'nieto', 'sanchez', 'belmont']
RURAL_SANCHEZ = {'Amazonas', 'Apurímac', 'Ayacucho', 'Cajamarca', 'Cusco', 'Huancavelica', 'Huánuco', 'Puno', 'San Martín'}
URBAN_RLA = {'Lima', 'Callao', 'Ica', 'La Libertad', 'Extranjero'}
SOUTH_NIETO = {'Arequipa', 'Moquegua', 'Tacna'}
EXTRANJERO_BASE = {'fujimori': 0.1557, 'rla': 0.2868, 'nieto': 0.1184, 'sanchez': 0.0196, 'belmont': 0.0844}


def load_tracking():
    return json.loads(TRACKING.read_text())


def load_onpe_live():
    return json.loads(ONPE_LIVE.read_text())


def load_model_input():
    return json.loads(MODEL_INPUT.read_text()) if MODEL_INPUT.exists() else None


def slope(cuts, key, n=4):
    sample = cuts[-n:]
    if len(sample) < 2:
        return 0.0
    first, last = sample[0], sample[-1]
    dp = last['pct'] - first['pct']
    if dp <= 0:
        return 0.0
    return (last[key] - first[key]) / dp


def adjusted_region_shares(region):
    shares = {c: region[c]['pct'] / 100 for c in CANDS}
    name = region['name']
    pct = region['pctActas'] / 100

    if name in RURAL_SANCHEZ:
        shares['sanchez'] *= 1.06
        shares['rla'] *= 0.97
        shares['nieto'] *= 0.985
    if name in URBAN_RLA:
        shares['rla'] *= 1.035
        shares['sanchez'] *= 0.94
    if name in SOUTH_NIETO:
        shares['nieto'] *= 1.02
        shares['sanchez'] *= 0.985
    if pct > 0.88:
        shares['sanchez'] *= 0.97
        shares['rla'] *= 1.01
    if pct < 0.60:
        shares['sanchez'] *= 1.04

    total = sum(shares.values()) or 1.0
    return {k: v / total for k, v in shares.items()}


def regional_projection(onpe_live):
    current_votes = {c: 0.0 for c in CANDS}
    projected_votes = {c: 0.0 for c in CANDS}
    region_edges = {c: [] for c in SECOND_ROUND}

    for region in onpe_live['regions']:
        pct = region['pctActas'] / 100
        if pct <= 0:
            continue
        vv = region['vv']
        final_vv = vv / pct
        pending_vv = max(0.0, final_vv - vv)
        adj = adjusted_region_shares(region)
        raw = {c: region[c]['pct'] / 100 for c in CANDS}

        for c in CANDS:
            current_votes[c] += region[c]['v']
            projected_votes[c] += region[c]['v'] + pending_vv * adj[c]

        region_edges['sanchez'].append({
            'region': region['name'],
            'pendingVotes': round(pending_vv),
            'vsRla': round(pending_vv * (adj['sanchez'] - adj['rla'])),
            'vsNieto': round(pending_vv * (adj['sanchez'] - adj['nieto'])),
            'rawSanchez': raw['sanchez'],
            'rawRla': raw['rla'],
            'rawNieto': raw['nieto'],
        })

    extranjero_pct = 0.157
    extranjero_vv = 51740
    extranjero_total = extranjero_vv / extranjero_pct
    extranjero_pending = extranjero_total - extranjero_vv
    ext = dict(EXTRANJERO_BASE)
    ext['rla'] *= 1.05
    ext['sanchez'] *= 0.95
    total = sum(ext.values()) or 1.0
    ext = {k: v / total for k, v in ext.items()}

    for c in CANDS:
        current_votes[c] += extranjero_vv * ext[c]
        projected_votes[c] += extranjero_vv * ext[c] + extranjero_pending * ext[c]

    # Normalize top-5 regional model back to national valid-vote frame.
    projection_total = sum(projected_votes.values()) or 1.0
    projection_pct = {c: round(projected_votes[c] / projection_total * 100, 2) for c in CANDS}
    current_total = sum(current_votes.values()) or 1.0
    current_pct = {c: round(current_votes[c] / current_total * 100, 3) for c in CANDS}

    return {
        'currentVotes': current_votes,
        'projectedVotes': projected_votes,
        'projectionPct': projection_pct,
        'currentPctRegionalized': current_pct,
        'regionEdges': region_edges,
        'projectionTotal': projection_total,
    }


def weighted_projection_from_scenarios(scenarios):
    agg = {}
    total_w = sum(s['probability'] for s in scenarios) or 1
    for s in scenarios:
        w = s['probability'] / total_w
        for row in s['ranking']:
            agg.setdefault(row['candidate'], 0.0)
            agg[row['candidate']] += row['pct'] * w
    return agg


def build_probability_history(cuts):
    structural = { 'rla': -0.25, 'nieto': -0.10, 'sanchez': 0.70, 'belmont': -0.55 }
    contenders = ['rla', 'nieto', 'sanchez', 'belmont']
    history = []
    for i in range(2, len(cuts)):
        cur = cuts[i]
        prev = cuts[i - 2]
        dp = max(0.1, cur['pct'] - prev['pct'])
        scores = {}
        for k in contenders:
            slope = (cur[k] - prev[k]) / dp
            scores[k] = (cur[k] * 1.2) + (slope * 18) + (structural[k] * 2.5) - (0.35 if k in {'rla','nieto'} else 0)
        min_score = min(scores.values())
        shifted = {k: max(0.05, v - min_score + 0.05) for k, v in scores.items()}
        total = sum(shifted.values()) or 1
        probs = {k: round(v / total * 100) for k, v in shifted.items()}
        if probs['sanchez'] > 65:
            excess = probs['sanchez'] - 65
            probs['sanchez'] = 65
            probs['rla'] += round(excess * 0.75)
            probs['nieto'] += round(excess * 0.20)
            probs['belmont'] += excess - round(excess * 0.75) - round(excess * 0.20)
        if probs['belmont'] > 8:
            excess = probs['belmont'] - 8
            probs['belmont'] = 8
            probs['rla'] += round(excess * 0.6)
            probs['sanchez'] += excess - round(excess * 0.6)
        diff = 100 - sum(probs.values())
        top = max(probs, key=probs.get)
        probs[top] += diff
        history.append({'pct': cur['pct'], **probs})
    return history


def build():
    model_input = load_model_input()
    data = model_input['tracking'] if model_input else load_tracking()
    onpe_live = model_input['onpeLive'] if model_input else load_onpe_live()
    canonical = model_input['canonical'] if model_input else {}
    cuts = data['cuts']
    current = data.get('latestCut') or cuts[-1]
    prev = cuts[-2] if len(cuts) > 1 else current
    current_pct = float(canonical.get('nationalPct') or onpe_live.get('nationalPct') or current['pct'])

    regional = regional_projection(onpe_live)
    projected_raw = regional['projectionPct']
    current_regionalized = regional['currentPctRegionalized']
    recent_slopes = {c: slope(cuts, c) for c in CANDS}

    current_top5_national = sum(current[c] for c in CANDS)
    projected = {
        c: round(projected_raw[c] / 100 * current_top5_national, 2)
        for c in CANDS
    }

    # Regionalized race scores, bastions/topes first, recent national slope second
    race_scores = {
        'rla': projected['rla'] * 1.15 + recent_slopes['rla'] * 6,
        'nieto': projected['nieto'] * 1.10 + recent_slopes['nieto'] * 5,
        'sanchez': projected['sanchez'] * 1.18 + recent_slopes['sanchez'] * 6.5,
        'belmont': projected['belmont'] * 1.00 + recent_slopes['belmont'] * 4,
    }
    # foreign vote assumption favors RLA, plus urban ceiling for Sanchez
    race_scores['rla'] += 1.10
    race_scores['sanchez'] -= 0.75
    race_scores['belmont'] -= 0.60

    # If Sánchez already overtook RLA in the observed tracking cut, shift from chase-mode to hold-mode.
    current_gap_sr = float(current['sanchez']) - float(current['rla'])
    if current_gap_sr > 0:
        race_scores['sanchez'] += 0.85 + min(0.35, current_gap_sr * 4)
        race_scores['rla'] -= 0.45

    min_score = min(race_scores.values())
    shifted = {k: max(0.05, v - min_score + 0.05) for k, v in race_scores.items()}
    total = sum(shifted.values()) or 1.0
    probs = {k: round(v / total * 100) for k, v in shifted.items()}
    diff = 100 - sum(probs.values())
    probs[max(probs, key=probs.get)] += diff

    ranking = sorted(CANDS, key=lambda c: projected[c], reverse=True)
    table = []
    for i, c in enumerate(ranking, start=1):
        key, label = LABELS[c]
        actual_base = float(current[c]) if c in current else float(current_regionalized.get(c, 0))
        table.append({
            'pos': i,
            'key': key,
            'candidate': label,
            'actual': round(actual_base, 2),
            'projected': round(projected[c], 2),
            'delta': round(projected[c] - actual_base, 2),
        })

    scenarios = [
        {
            'id': 'base',
            'name': 'Base regionalizado',
            'probability': max(30, min(45, probs['sanchez'])),
            'assumptions': [
                'Se usa el pendiente por regiones, no solo slope nacional',
                'Sánchez mantiene fuerza en bastiones rurales andinos y amazónicos',
                'Extranjero se asume favorable a López Aliaga'
            ],
            'ranking': [{'candidate': LABELS[c][1], 'pct': projected[c]} for c in ranking[:4]]
        },
        {
            'id': 'sanchez-upside',
            'name': 'Sánchez capitaliza bastiones al máximo razonable',
            'probability': max(20, probs['sanchez'] - 5),
            'assumptions': [
                'Cajamarca, Puno, Cusco, Apurímac y San Martín rinden por encima del promedio actual',
                'Lima no acelera adicionalmente para RLA más allá del patrón observado',
                'El extranjero sigue ayudando a RLA pero no alcanza para neutralizar todo el bloque rural'
            ],
            'ranking': [
                {'candidate': 'Fujimori', 'pct': round(projected['fujimori'] + 0.05, 2)},
                {'candidate': 'Sánchez', 'pct': round(projected['sanchez'] + 0.22, 2)},
                {'candidate': 'López Aliaga', 'pct': round(projected['rla'] - 0.18, 2)},
                {'candidate': 'Nieto', 'pct': round(projected['nieto'] - 0.04, 2)}
            ]
        },
        {
            'id': 'rla-holds',
            'name': 'RLA retiene por Lima + Extranjero',
            'probability': max(20, probs['rla']),
            'assumptions': [
                'Lima y Extranjero pesan más en el tramo final útil',
                'Sánchez encuentra topes fuera de sus bastiones más claros',
                'RLA conserva ventaja estrecha por composición del pendiente urbano/exterior'
            ],
            'ranking': [
                {'candidate': 'Fujimori', 'pct': round(projected['fujimori'], 2)},
                {'candidate': 'López Aliaga', 'pct': round(projected['rla'] + 0.14, 2)},
                {'candidate': 'Sánchez', 'pct': round(projected['sanchez'] - 0.16, 2)},
                {'candidate': 'Nieto', 'pct': round(projected['nieto'], 2)}
            ]
        }
    ]

    weighted = weighted_projection_from_scenarios(scenarios)
    display_projection = {
        'Fujimori': round(weighted.get('Fujimori', projected['fujimori']), 2),
        'López Aliaga': round(weighted.get('López Aliaga', projected['rla']), 2),
        'Nieto': round(weighted.get('Nieto', projected['nieto']), 2),
        'Sánchez': round(weighted.get('Sánchez', projected['sanchez']), 2),
        'Belmont': round(projected['belmont'], 2)
    }
    name_to_key = {'Fujimori':'fuji','López Aliaga':'rla','Nieto':'nieto','Sánchez':'sanch','Belmont':'belm'}
    actual_map = {'Fujimori': float(current['fujimori']), 'López Aliaga': float(current['rla']), 'Nieto': float(current['nieto']), 'Sánchez': float(current['sanchez']), 'Belmont': float(current['belmont'])}
    display_table = []
    for i, name in enumerate(sorted(display_projection, key=lambda n: display_projection[n], reverse=True), start=1):
        display_table.append({
            'pos': i,
            'key': name_to_key[name],
            'candidate': name,
            'actual': round(actual_map[name], 2),
            'projected': round(display_projection[name], 2),
            'delta': round(display_projection[name] - actual_map[name], 2),
        })

    top_san_edges = sorted(regional['regionEdges']['sanchez'], key=lambda x: x['vsRla'], reverse=True)[:8]
    top_rla_edges = sorted(regional['regionEdges']['sanchez'], key=lambda x: x['vsRla'])[:8]
    insights = []
    if current_gap_sr > 0:
        insights.append('Sánchez ya aparece 2° en el conteo observado y el modelo pasa de escenario de alcance a escenario de defensa del sorpasso.')
    elif probs['sanchez'] > probs['rla']:
        insights.append('Sánchez lidera la carrera por el 2° lugar en el modelo regionalizado, pero con margen todavía sensible a Lima y Extranjero.')
    else:
        insights.append('López Aliaga conserva ventaja estrecha en el modelo regionalizado, sostenido por Lima y el supuesto favorable en Extranjero.')
    insights.append(f"Pendiente reciente nacional: Sánchez {recent_slopes['sanchez']:.3f} pp por punto vs RLA {recent_slopes['rla']:.3f}, pero la decisión la dominan bastiones y topes regionales.")
    insights.append('Bastiones netos pro-Sánchez vs RLA: ' + ', '.join(f"{r['region']} ({r['vsRla']:+,})" for r in top_san_edges[:5]))

    out = {
        'generatedAt': datetime.now().astimezone().isoformat(timespec='seconds'),
        'source': 'Modelo regionalizado Hannah v3 (bastiones, topes, pendiente regional y Extranjero pro-RLA)',
        'nationalPct': current_pct,
        'canonicalMeta': canonical,
        'secondRoundProbabilities': {
            'rla': probs['rla'],
            'nieto': probs['nieto'],
            'sanchez': probs['sanchez'],
            'belmont': probs['belmont'],
        },
        'projectionTableRaw': table,
        'projectionTable': display_table,
        'scenarios': scenarios,
        'insights': insights,
        'probabilityHistory': build_probability_history(cuts),
        'debug': {
            'recentSlopes': recent_slopes,
            'currentCut': current,
            'previousCut': prev,
            'currentPctRegionalized': current_regionalized,
            'regionalProjectionPct': projected,
            'topRegionalEdgesSanchezVsRla': top_san_edges,
            'topRegionalEdgesRlaVsSanchez': top_rla_edges,
        }
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == '__main__':
    result = build()
    print(json.dumps({
        'generatedAt': result['generatedAt'],
        'nationalPct': result['nationalPct'],
        'probabilities': result['secondRoundProbabilities'],
        'top4': result['projectionTable'][:4]
    }, ensure_ascii=False, indent=2))
