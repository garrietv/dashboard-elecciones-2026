# Handover técnico - capa de predicciones

## Objetivo
Montar una capa analítica encima del dashboard ONPE sin romper la extracción live.

## Decisión arquitectónica tomada
Se decidió **apalancarse de la extracción del dashboard base** porque es mejor para tiempo real, y poner encima nuestro modelo como capa separada.

### Separación vigente
- extracción live = dashboard/worker/tracking
- predicción = script + json + visual específica

## Qué no debemos romper
- `WORKER_URL`
- `TRACKING.cuts`
- pestaña `ONPE en Vivo`
- flujo de refresh live

## Qué sí se añadió
- pestaña `Predicciones`
- `data/predictions.json`
- `scripts/build_predictions.py`
- gráfica histórica de probabilidad
- escenarios con supuestos
- insights cualitativos

## Regla importante
La visual principal de predicción debe representar una **media ponderada de escenarios**, no el escenario más agresivo.

## Riesgos conocidos
1. Hay lógica duplicada entre Python y JS
2. La recalibración live en frontend puede divergir del script Python si se cambia uno y no el otro
3. Algunas partes del modelo aún usan heurísticas simplificadas, no toda la profundidad regional de nuestro análisis manual

## Próximo refactor deseable
Crear una única capa de cálculo compartida o, mínimo:
- `data/model_input.json`
- `data/predictions.json`
- frontend solo renderiza

## Señales de que algo salió mal
- Belmont sube artificialmente en probabilidad
- Sánchez aparece en escenario extremo como default visual
- la tabla de proyección contradice los escenarios
- la gráfica histórica no coincide con las probabilidades actuales
- ONPE en Vivo vuelve a mostrar elementos de predicción

## Cómo retomar trabajo
1. abrir `README.md`
2. abrir `scripts/build_predictions.py`
3. correr el script
4. verificar `data/predictions.json`
5. revisar UI de la pestaña Predicciones
6. hacer ajuste incremental y push a main
