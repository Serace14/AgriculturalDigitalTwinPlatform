#!/bin/bash
# Deja los 4 gemelos de alfalfa "limpios" antes de grabar: borra lecturas de sensores, comandos,
# notificaciones y simulaciones anteriores. NO toca clima, cortes reales (Activities), propiedades
# ni los gemelos de pistacho.
#
#   bash scripts/reset_demo.sh          # solo cuenta lo que borraría (no borra nada)
#   bash scripts/reset_demo.sh --yes    # borra
set -euo pipefail
MODE="${1:-}"
MONGO=$(grep -i mongo <<<"$(docker ps --format '{{.Names}}')" | head -1 || true)
[ -n "$MONGO" ] || { echo "No encuentro el contenedor de Mongo en marcha"; exit 1; }

docker exec -i -e DO_DELETE="$([ "$MODE" = "--yes" ] && echo 1 || echo 0)" "$MONGO" bash -c \
  'mongosh -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --quiet' <<'EOF'
const del = process.env.DO_DELETE === "1";
const twins = ["25-56-0-0-8-162-1", "25-153-0-0-30-3-1", "25-56-0-0-8-219-1", "25-56-0-0-13-40-1"];
const cols = ["Sensors", "Commands", "Notifications", "Simulations", "SimulationResults"];
print(del ? "== BORRANDO ==" : "== SIMULACRO (no se borra nada; usa --yes) ==");
twins.forEach(id => cols.forEach(c => {
  const col = db.getSiblingDB(id).getCollection(c);
  const n = col.countDocuments();
  if (n > 0) {
    if (del) col.deleteMany({});
    print((del ? "borrados " : "se borrarían ") + n + "  " + id + "." + c);
  }
}));
const common = db.getSiblingDB("common").getCollection("Notifications");
const nc = common.countDocuments();
if (nc > 0) { if (del) common.deleteMany({}); print((del ? "borrados " : "se borrarían ") + nc + "  common.Notifications"); }
print("hecho.");
EOF
if [ "$MODE" = "--yes" ]; then
  echo
  echo "Recuerda: si hay simulaciones en marcha, páralas en el panel o termínalas en Temporal UI antes de grabar."
fi
