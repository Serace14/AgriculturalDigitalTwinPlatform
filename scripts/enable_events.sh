#!/bin/bash
# Activa los eventos (sensor -> watcher -> comando de riego + notificación a parcelas vecinas)
# para el gemelo de alfalfa principal. Desde la raíz del repo:
#   bash scripts/enable_events.sh
#
# 1. Añade el worker y el watcher del gemelo a temporal/entrypoint.sh (si no estaban)
# 2. Los arranca ya en el contenedor temporal-worker (sin duplicar el watcher)
# 3. Reinicia el contenedor de Benthos para que cargue benthos/entrypoint.sh (sensor + feedback)
set -euo pipefail

ID="${1:-25-56-0-0-8-162-1}"
CONTAINER="${CONTAINER:-temporal-worker}"
ENTRY="temporal/entrypoint.sh"
[ -d "temporal/workflows/$ID/watcher" ] || { echo "No existe temporal/workflows/$ID/watcher (¿raíz del repo?)"; exit 1; }

# 1. entrypoint de Temporal
if grep -q "workflows/$ID/watcher/" "$ENTRY"; then
  echo "entrypoint.sh ya tiene el watcher de $ID"
else
  TMP=$(mktemp)
  awk -v id="$ID" '
    /^tail -f \/dev\/null/ && !done {
      print "# " id " (alfalfa) - eventos"
      print "python3 /etc/temporal/workflows/" id "/watcher/init_workers.py &"
      print "python3 /etc/temporal/workflows/" id "/watcher/watcher.py &"
      print ""
      done=1
    }
    { print }' "$ENTRY" > "$TMP"
  if ! grep -q "workflows/$ID/watcher/" "$TMP"; then
    { cat "$ENTRY"; echo; echo "python3 /etc/temporal/workflows/$ID/watcher/init_workers.py &"; \
      echo "python3 /etc/temporal/workflows/$ID/watcher/watcher.py &"; } > "$TMP"
  fi
  cat "$TMP" > "$ENTRY"; rm -f "$TMP"
  echo "watcher añadido a entrypoint.sh"
fi

# 2. arrancar ahora, sin duplicar (dos watcher.py lanzarían cada evento dos veces)
RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null || true)
if grep -qx "$CONTAINER" <<<"$RUNNING"; then
  count() {  # cuántos procesos coinciden (el corchete evita que el grep se cuente a sí mismo)
    docker exec "$CONTAINER" bash -c "for p in /proc/[0-9]*; do tr '\0' ' ' < \$p/cmdline 2>/dev/null; echo; done | grep -c 'workflows/$ID/[w]atcher/$1'" 2>/dev/null || true
  }
  for f in init_workers.py watcher.py; do
    n=$(count "$f"); n=${n:-0}
    if [ "$n" -gt 0 ] 2>/dev/null; then
      echo "ya corre: watcher/$f"
    else
      docker exec -d "$CONTAINER" python3 "/etc/temporal/workflows/$ID/watcher/$f"
      echo "arrancado: watcher/$f"
    fi
  done
else
  echo "contenedor $CONTAINER no está en marcha: se arrancarán con el entrypoint"
fi

# 3. Benthos
BENTHOS=$(grep -i benthos <<<"$(docker ps --format '{{.Names}}' 2>/dev/null || true)" | head -1 || true)
if [ -n "$BENTHOS" ]; then
  docker restart "$BENTHOS" >/dev/null && echo "reiniciado: $BENTHOS"
else
  echo "no encuentro el contenedor de Benthos en marcha (docker compose up -d benthos)"
fi
echo "Listo. Prueba con: bash scripts/fire_event.sh $ID 75"
