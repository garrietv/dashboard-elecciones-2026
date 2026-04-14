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
- frontend consulta ONPE vía `WORKER_URL`
- cuando entra nueva data, el tracking se actualiza en cliente

### Capa 2: predicción
- script: `scripts/build_predictions.py`
- salida persistida: `data/predictions.json`
- también existe recalculo live en frontend cuando entra nueva data ONPE

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
Se actualiza automáticamente desde el frontend cuando el Worker responde con nueva data.

### Predicciones
Se actualizan de 2 formas:

1. **Live en frontend**
   - cuando entra nueva data ONPE
   - recalcula numérico + insights

2. **Persistidas**
   - ejecutando:

```bash
cd /home/garrieta/.openclaw/workspace/check_dashboard
python3 scripts/build_predictions.py
```

Esto regenera `data/predictions.json`.

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
   - la extracción debe seguir desacoplada
   - la predicción debe vivir como capa separada

2. **La visual mostrada en Predicciones no es un forecast único**
   - es una media ponderada de escenarios

3. **No confiar solo en hardcodes del frontend**
   - si se cambia metodología, reflejar también en `scripts/build_predictions.py`

4. **Si cambian los cortes ONPE o el Worker**
   - verificar que `TRACKING.cuts` siga alimentándose bien
   - luego validar si la histórica de probabilidad sigue siendo lógica

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
