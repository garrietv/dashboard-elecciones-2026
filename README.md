# Dashboard Elecciones 2026

Dashboard electoral para seguimiento ONPE en tiempo real + capa analítica de predicciones.

## Estado actual

El proyecto combina dos capas:

1. **ONPE en Vivo**
   - extracción en tiempo real vía Worker/API ONPE
   - mapa, tracking y evolución visual

2. **Predicciones**
   - capa separada con probabilidades de 2° lugar
   - escenarios probables
   - tabla `ONPE actual → Proyección 100%`
   - insights cualitativos
   - gráfica histórica de probabilidad

## Arquitectura

### Capa 1: ingestión en tiempo real
- fuente principal: `data/tracking.json`
- fuente regional: `data/onpe_live.json`
- snapshots persistidos: `data/onpe_snapshots/`
- normalizados persistidos: `data/normalized/`
- latest estable: `data/latest/onpe_latest.json`
- frontend consulta ONPE vía `WORKER_URL`, pero la verdad persistida vive en archivos

### Capa 2: predicción
- script: `scripts/build_predictions.py`
- salida persistida: `data/predictions.json`
- fuente canónica: archivos persistidos, no recálculo heurístico en frontend

### Capa 3: visualización
- `index.html`
- pestañas:
  - `ONPE en Vivo`
  - `Predicciones`
  - `Datum CR 100%`

## Archivos clave

- `index.html` → dashboard principal
- `data/tracking.json` → historial de cortes ONPE
- `data/onpe_live.json` → data regional embebida
- `data/predictions.json` → predicciones persistidas
- `scripts/build_predictions.py` → generador de predicciones
- `SETUP.md` → notas de setup heredadas del dashboard base

## Qué hace hoy la pestaña Predicciones

- muestra probabilidades de pase a 2° vuelta
- muestra tabla de proyección basada en media ponderada de escenarios
- muestra escenarios y supuestos
- muestra insights cualitativos
- muestra histórica de probabilidad en el tiempo

## Cómo se actualiza hoy

### ONPE en vivo
Se actualiza automáticamente desde el frontend cuando el Worker responde con nueva data, pero ahora el repo ya tiene pipeline para persistir y resincronizar el estado completo.

### Persistencia recomendada

```bash
cd /home/garrieta/.openclaw/workspace/check_dashboard
python3 scripts/update_onpe_pipeline.py
```

Este comando:
- detecta si entró un corte nuevo
- guarda snapshot bruto por corte
- guarda versión normalizada
- actualiza `data/latest/onpe_latest.json`
- regenera `data/predictions.json`
- deja traza en `data/latest/pipeline_state.json`
- permite que toda la pestaña `Predicciones` se repinte desde una única fuente persistida

### Modo manual equivalente

```bash
cd /home/garrieta/.openclaw/workspace/check_dashboard
python3 scripts/store_onpe_snapshot.py
python3 scripts/build_onpe_latest.py
python3 scripts/build_predictions.py
python3 scripts/embed_latest_into_index.py
```

### Automatización del repo
- Workflow: `.github/workflows/onpe-pipeline.yml`
- Trigger: push a `main` cuando cambian `data/tracking.json` o `data/onpe_live.json`
- Efecto: ejecuta el pipeline, regenera snapshots/latest/predictions, resincroniza `index.html` y hace commit automático si hubo cambios reales

## Metodología actual de predicción

La capa predictiva actual usa:
- tracking histórico de cortes
- pendiente reciente por candidato
- priors estructurales manuales
- escenarios probables ponderados
- salida auditada con probabilidad histórica

### Idea central
La predicción no debe depender de un único escenario agresivo. La UI muestra una **media ponderada de escenarios probables**.

## Cambios ya hechos sobre el dashboard base

- rebranding a **Gustavo Arrieta**
- base visual clara / fondo blanco
- eliminación de créditos del autor original en UI
- eliminación de las visuales de proyección de la pestaña `ONPE en Vivo`
- migración de esas visuales a la pestaña `Predicciones`
- nueva gráfica histórica de probabilidad
- recálculo automático de predicciones tras refresh ONPE

## Cosas importantes a recordar

1. **No mezclar extracción y predicción en el mismo bloque lógico**
   - la extracción sigue desacoplada
   - la predicción vive como capa separada y persistida

2. **La visual mostrada en Predicciones no es un forecast único**
   - es una media ponderada de escenarios

3. **Frontend no debe ser source of truth**
   - no recalcular un modelo alterno en cliente como default
   - renderizar `data/predictions.json`

4. **Si cambian los cortes ONPE o el Worker**
   - persistir snapshot
   - regenerar latest
   - regenerar predicciones
   - la pestaña `Predicciones` debe releer únicamente `data/predictions.json`
   - recién después validar UI

## Próximas mejoras recomendadas

### Alta prioridad
- persistir automáticamente nueva histórica de probabilidad corte a corte
- unificar fórmula JS y fórmula Python para evitar drift
- mover parte del recálculo live a una capa más mantenible

### Media prioridad
- crear `data/model_input.json` como capa intermedia normalizada
- mostrar “último recalculo predictivo” explícitamente en UI
- añadir auditoría visual de cambios entre cortes

### Baja prioridad
- integrar más adelante nuestro análisis regional profundo dentro del dashboard
- añadir explicación larga tipo memo ejecutivo

## Checklist de verificación cuando retomemos

Antes de tocar el modelo:
- [ ] revisar `data/tracking.json`
- [ ] revisar `data/predictions.json`
- [ ] correr `python3 scripts/build_predictions.py`
- [ ] validar que probabilidades sumen 100
- [ ] validar que Belmont no salga artificialmente inflado
- [ ] validar que insights cualitativos sigan coherentes con la nueva data
- [ ] validar que la pestaña `ONPE en Vivo` no vuelva a mostrar visuales de predicción

## Comandos útiles

```bash
cd /home/garrieta/.openclaw/workspace/check_dashboard
python3 scripts/build_predictions.py
git status
git add .
git commit -m "mensaje"
git push origin main
```

## Nota operativa

Si el objetivo es retomar mejoras futuras, este repo ya no debe depender de memoria conversacional. La fuente de continuidad es:
- este `README.md`
- `scripts/build_predictions.py`
- `data/predictions.json`
- el historial git del repo
