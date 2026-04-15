# Database Layer (isolated sidecar)

## Objetivo
Agregar una capa de persistencia histórica más robusta **sin romper** el flujo actual basado en JSON.

## Principio
- `data/*.json` siguen siendo la fuente operativa del frontend actual.
- `data/onpe_history.db` funciona como **sidecar** aislado para auditoría, histórico y modelado futuro.
- Si la DB falla, el flujo actual debe seguir funcionando.

## Componentes
- `scripts/db_init.py` - crea el esquema SQLite
- `scripts/record_pipeline_state.py` - registra un capture completo después del pipeline
- `data/onpe_history.db` - base SQLite local

## Tablas
- `captures` - snapshot maestro por corte/captura
- `tracking_cuts` - historial de cuts asociado a una captura
- `regional_results` - resultados regionales normalizados por captura
- `prediction_runs` - salida de predicciones asociada a una captura

## Flujo
1. `sync_from_worker.py`
2. `store_onpe_snapshot.py`
3. `build_onpe_latest.py`
4. `build_model_input.py`
5. `build_predictions.py`
6. `record_pipeline_state.py`  ← sidecar DB

## Uso manual
```bash
python3 scripts/db_init.py
python3 scripts/full_auto_sync.py
python3 scripts/record_pipeline_state.py
sqlite3 data/onpe_history.db ".tables"
```

## Garantía de aislamiento
Esta capa no reemplaza ni muta la lógica actual del dashboard. Solo registra el estado ya generado por el pipeline existente.
