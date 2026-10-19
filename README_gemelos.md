# Generar las 4 parcelas de alfalfa

| Id | Parcela | Municipio | ha |
|---|---|---|---|
| 25-56-0-0-8-162-1 | BALAGUERÓ - LLARGA (ya existe) | Bellcaire d'Urgell | 1,81 |
| 25-153-0-0-30-3-1 | ROSA LLUCH - LINYOLA | Linyola | 2,98 |
| 25-56-0-0-8-219-1 | MAGATZEM LLUCH | Bellcaire d'Urgell | 1,63 |
| 25-56-0-0-13-40-1 | JORDI ESCOLA - CAMP | Bellcaire d'Urgell | 3,24 |

## 1. Copiar al proyecto (desde la raíz del repo)

Descomprime el zip en la raíz del repo. Sobrescribe solo
`temporal/workflows/25-56-0-0-8-162-1/etl/static-info/meteo_station.py`
(elige la estación 9771C Lleida y sube el timeout de 15 s a 60 s) y añade `scripts/` y `geojson/`.

## 2. Generar los gemelos nuevos

    bash scripts/new_alfalfa_twin.sh 25-153-0-0-30-3-1 25-56-0-0-8-219-1 25-56-0-0-13-40-1

Por cada id copia la carpeta del gemelo principal cambiando el id, añade sus 4 workers a
`temporal/entrypoint.sh`, crea el namespace en Temporal y arranca los workers en `temporal-worker`
(sin reiniciar nada). Es idempotente.

## 3. Crear cada gemelo en la web

Panel → añadir gemelo digital → subir `geojson/<id>.geojson`. El gateway espera a que
`MeteoStationWorkflow` termine; si se queda pensando, mira en Temporal UI (namespace del gemelo)
si el workflow `meteo-station` está en marcha.

## 4. Comprobar

    docker exec digital-twin-local-mongo mongosh --quiet common --eval 'db.DigitalTwins.find({}, {"properties.meteoStation":1, "meteoStation":1}).forEach(d => printjson(d))'

(o, más sencillo, en la vista del gemelo en la web / Temporal UI → namespace del gemelo → `meteo-station` → resultado.)

Debe salir la estación `9771C` en los cuatro. El gateway lanza luego la carga del histórico
meteorológico (workflow `historical-weather-workflow-9771C` en `open-data`): como la estación ya
tiene datos cargados no debería tardar; comprueba después `Weather` en cada base.

Si algún gemelo sale con otra estación (p. ej. 9720X), AGROSLAB no devolvió 9771C entre los
candidatos: dímelo y la fijamos a mano.

## Memoria

Cada gemelo con sus 4 workers añade ~380 MB al contenedor `temporal-worker` (activities ~180 MB,
prediction ~115 MB, simulations y static-info ~45 MB cada uno). Para 3 gemelos extra: ~1,1 GB.
Si vas justo de RAM, quita la línea de `prediction` de los gemelos extra en `entrypoint.sh`
(solo es necesaria para las predicciones de rendimiento de ese gemelo).
