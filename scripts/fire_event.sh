#!/bin/bash
# Lanza un evento de prueba en un gemelo, insertando lecturas en su colección Sensors
# (es lo mismo que haría Benthos al recibir el mensaje MQTT). Desde la raíz del repo:
#   bash scripts/fire_event.sh                     # gemelo principal, 75 mm
#   bash scripts/fire_event.sh 25-56-0-0-8-162-1 85
#
# Inserta una lectura de temperatura y otra de humedad (se ven en Monitorización)
# y una de agua en mm. Si el agua supera 60 mm marca threat=high y el watcher actúa:
# comando automático de parar el riego 12 h + aviso a las parcelas a menos de 10 km.
set -euo pipefail
ID="${1:-25-56-0-0-8-162-1}"
VAL="${2:-75}"
MONGO=$(grep -i mongo <<<"$(docker ps --format '{{.Names}}')" | head -1 || true)
[ -n "$MONGO" ] || { echo "No encuentro el contenedor de Mongo en marcha"; exit 1; }

docker exec -i -e TWIN="$ID" -e VAL="$VAL" "$MONGO" bash -c \
  'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet' <<'EOF'
const id = process.env.TWIN, val = Number(process.env.VAL);
const now = new Date();
const base = { timestamp: now, digitalTwinId: id, threat: "low" };
const docs = [
  { ...base, type: "temperature", unit: "C", value: 24.3, sensorId: "alfalfa-temp-1", sensorName: "Temperatura parcela" },
  { ...base, type: "humidity", unit: "%", value: 62, sensorId: "alfalfa-hum-1", sensorName: "Humedad parcela" },
  { ...base, type: "water", unit: "mm", value: val, sensorId: "alfalfa-water-1", sensorName: "Pluviómetro parcela",
    threat: val > 60 ? "high" : "low" },
];
db.getSiblingDB(id).Sensors.insertMany(docs);
print("insertado en " + id + ": temperatura 24.3 C, humedad 62 %, agua " + val + " mm (threat=" + docs[2].threat + ")");
EOF
