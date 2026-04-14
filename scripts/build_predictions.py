#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKING = ROOT / 'data' / 'tracking.json'
OUT = ROOT / 'data' / 'predictions.json'

CANDS = ['fujimori', 'rla', 'nieto', 'sanchez', 'belmont']
LABELS = {
    'fujimori': ('fuji', 'Fujimori'),
    'rla': ('rla', 'López Aliaga'),
    'nieto': ('nieto', 'Nieto'),
    'sanchez': ('sanch', 'Sánchez'),
    'belmont': ('belm', 'Belmont'),
}
COLLISION_GROUP = {'rla', 'nieto'}
# Structural priors from our regional methodology
STRUCTURAL_PRIOR = {
    'fujimori': 0.15,
    'rla': -0.25,
    'nieto': -0.10,
    'sanchez': 0.70,
    'belmont': -0.55,
}
SECOND_ROUND = ['rla', 'nieto', 'sanchez', 'belmont']


def load_tracking():
    return json.loads(TRACKING.read_text())


def slope(cuts, key, n=4):
    sample = cuts[-n:]
    if len(sample) < 2:
        return 0.0
    first, last = sample[0], sample[-1]
    dp = last['pct'] - first['pct']
    if dp <= 0:
        return 0.0
    return (last[key] - first[key]) / dp


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
    data = load_tracking()
    cuts = data['cuts']
    current = cuts[-1]
    prev = cuts[-2] if len(cuts) > 1 else cuts[-1]
    current_pct = float(current['pct'])
    remaining = max(0.1, 100 - current_pct)

    recent_slopes = {c: slope(cuts, c) for c in CANDS}
    # Normalize acceleration vs median slope to avoid runaway projections
    slope_values = sorted(recent_slopes.values())
    median = slope_values[len(slope_values)//2] if slope_values else 0.0
    median = median if abs(median) > 1e-6 else 0.01

    projected = {}
    for c in CANDS:
        cur = current[c]
        base_slope = recent_slopes[c]
        accel_factor = max(-1.5, min(2.0, base_slope / median))
        structural = STRUCTURAL_PRIOR[c]
        adjustment = 0.18 * accel_factor + 0.12 * structural
        if c in COLLISION_GROUP:
            adjustment -= 0.05
        projected[c] = round(cur + max(-1.5, min(1.8, base_slope * remaining * (1 + adjustment))), 2)

    # keep ordering realistic around current leader
    projected['fujimori'] = max(projected['fujimori'], current['fujimori'] + 0.55)
    projected['belmont'] = max(projected['belmont'], current['belmont'] + 0.10)

    # 2nd round probabilities from projected share, recent slope and structural bias
    race_scores = {}
    for c in SECOND_ROUND:
        score = projected[c] * 1.2
        score += recent_slopes[c] * 18
        score += STRUCTURAL_PRIOR.get(c, 0) * 2.5
        if c in COLLISION_GROUP:
            score -= 0.35
        race_scores[c] = score

    min_score = min(race_scores.values())
    shifted = {k: max(0.05, v - min_score + 0.05) for k, v in race_scores.items()}
    total = sum(shifted.values())
    probs = {k: round(v / total * 100) for k, v in shifted.items()}
    # soft caps for realism under this methodology
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

    ranking = sorted(CANDS, key=lambda c: projected[c], reverse=True)
    table = []
    for i, c in enumerate(ranking, start=1):
        key, label = LABELS[c]
        table.append({
            'pos': i,
            'key': key,
            'candidate': label,
            'actual': round(current[c], 2),
            'projected': round(projected[c], 2),
            'delta': round(projected[c] - current[c], 2),
        })

    scenarios = [
        {
            'id': 'base',
            'name': 'Escenario base',
            'probability': max(35, min(55, probs['sanchez'])),
            'assumptions': [
                'La pendiente final mantiene el patrón reciente del tracking ONPE',
                'Sánchez sostiene ventaja relativa en tramos pendientes',
                'RLA sigue limitado por zonas más avanzadas del conteo'
            ],
            'ranking': [{'candidate': LABELS[c][1] if c in LABELS else c, 'pct': projected[c]} for c in ranking[:4]]
        },
        {
            'id': 'sanchez-upside',
            'name': 'Sánchez acelera en bastiones',
            'probability': max(20, probs['sanchez'] - 10),
            'assumptions': [
                'El tramo pendiente pesa más en Cajamarca, Amazonas y otras zonas favorables',
                'Se mantiene la canibalización relativa entre RLA y Nieto',
                'La pendiente rural empuja a Sánchez por encima de la línea base'
            ],
            'ranking': [
                {'candidate': 'Fujimori', 'pct': round(projected['fujimori'] + 0.10, 2)},
                {'candidate': 'Sánchez', 'pct': round(projected['sanchez'] + 0.35, 2)},
                {'candidate': 'López Aliaga', 'pct': round(projected['rla'] - 0.10, 2)},
                {'candidate': 'Nieto', 'pct': round(projected['nieto'] - 0.05, 2)}
            ]
        },
        {
            'id': 'rla-holds',
            'name': 'RLA retiene el 2° lugar',
            'probability': max(15, probs['rla']),
            'assumptions': [
                'El tramo pendiente converge al promedio nacional',
                'Sánchez desacelera fuera de sus regiones fuertes',
                'RLA conserva suficiente piso para quedar delante'
            ],
            'ranking': [
                {'candidate': 'Fujimori', 'pct': round(projected['fujimori'], 2)},
                {'candidate': 'López Aliaga', 'pct': round(projected['rla'] + 0.18, 2)},
                {'candidate': 'Sánchez', 'pct': round(projected['sanchez'] - 0.22, 2)},
                {'candidate': 'Nieto', 'pct': round(projected['nieto'], 2)}
            ]
        }
    ]

    weighted = weighted_projection_from_scenarios(scenarios)
    display_projection = {
        'Fujimori': round(weighted.get('Keiko Fujimori', projected['fujimori']), 2),
        'López Aliaga': round(weighted.get('Rafael López Aliaga', projected['rla']), 2),
        'Nieto': round(weighted.get('Jorge Nieto', projected['nieto']), 2),
        'Sánchez': round(weighted.get('Roberto Sánchez', projected['sanchez']), 2),
        'Belmont': round(projected['belmont'], 2)
    }
    name_to_key = {'Fujimori':'fuji','López Aliaga':'rla','Nieto':'nieto','Sánchez':'sanch','Belmont':'belm'}
    actual_map = {'Fujimori': current['fujimori'], 'López Aliaga': current['rla'], 'Nieto': current['nieto'], 'Sánchez': current['sanchez'], 'Belmont': current['belmont']}
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

    insights = []
    if probs['sanchez'] > probs['rla']:
        insights.append('Sánchez pasa a liderar la carrera por el 2° lugar en el modelo por mejor pendiente reciente.')
    else:
        insights.append('RLA conserva una ventaja estrecha en la carrera por el 2° lugar, pero sin mucho margen.')
    insights.append(f"La pendiente reciente favorece a Sánchez ({recent_slopes['sanchez']:.3f} pp por punto) sobre RLA ({recent_slopes['rla']:.3f}).")
    insights.append('Nieto sigue en la conversación, pero su probabilidad cae si no recorta más rápido en los siguientes cortes.')

    out = {
        'generatedAt': datetime.now().astimezone().isoformat(timespec='seconds'),
        'source': 'Modelo Hannah v2 automático sobre tracking ONPE',
        'nationalPct': current_pct,
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
