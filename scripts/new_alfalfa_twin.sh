#!/bin/bash
# Crea la carpeta de workflows de un gemelo de alfalfa nuevo copiando la del
# gemelo plantilla (25-56-0-0-8-162-1) y cambiando el id.
#
# Uso (desde la raíz del repo AgriculturalDigitalTwinPlatform):
#   bash scripts/new_alfalfa_twin.sh 25-153-0-0-30-3-1 25-56-0-0-8-219-1 25-56-0-0-13-40-1
#
# Qué hace por cada id:
#   1. Copia temporal/workflows/<plantilla> -> temporal/workflows/<id>
#      (sin ml-training, __pycache__ ni los *Zone.Identifier de Windows)
#   2. Sustituye el id de la plantilla por el nuevo en todos los .py
#   3. Añade sus 4 workers a temporal/entrypoint.sh (si no estaban ya)
#   4. Crea el namespace de Temporal (si no existe) y arranca esos workers YA dentro del contenedor temporal-worker, para que
#      el worker de static-info exista antes de crear el gemelo en la web
#      (el gateway espera a MeteoStationWorkflow al crear un gemelo).
#
# Es idempotente: si la carpeta ya existe no la toca (usa FORCE=1 para rehacerla).
set -euo pipefail

TEMPLATE="25-56-0-0-8-162-1"
WF_DIR="temporal/workflows"
ENTRY="temporal/entrypoint.sh"
CONTAINER="${CONTAINER:-temporal-worker}"

[ $# -ge 1 ] || { echo "Uso: $0 <id> [<id> ...]"; exit 1; }
[ -d "$WF_DIR/$TEMPLATE" ] || { echo "No encuentro $WF_DIR/$TEMPLATE (¿estás en la raíz del repo?)"; exit 1; }

for ID in "$@"; do
  [[ "$ID" =~ ^[0-9]+(-[0-9]+){6}$ ]] || { echo "Id no válido: $ID"; exit 1; }
  DEST="$WF_DIR/$ID"
  echo "== $ID"

  if [ -d "$DEST" ] && [ "${FORCE:-0}" != "1" ]; then
    echo "   $DEST ya existe, no se copia (FORCE=1 para rehacer)"
  else
    rm -rf "$DEST"
    mkdir -p "$DEST"
    # tar con exclusiones: copia el árbol sin lo que no hace falta
    tar -C "$WF_DIR/$TEMPLATE" \
        --exclude='ml-training' --exclude='__pycache__' --exclude='*Zone.Identifier' \
        -cf - . | tar -C "$DEST" -xf -
    find "$DEST" -name '*.py' -print0 | xargs -0 sed -i "s/$TEMPLATE/$ID/g"
    echo "   carpeta creada"
  fi

  if grep -q "workflows/$ID/" "$ENTRY"; then
    echo "   entrypoint.sh ya tiene $ID"
  else
    # el entrypoint termina en 'tail -f /dev/null': insertamos antes de él
    TMP=$(mktemp)
    awk -v id="$ID" '
      /^tail -f \/dev\/null/ && !done {
        print "# " id " (alfalfa)"
        print "python3 /etc/temporal/workflows/" id "/etl/static-info/init_workers.py &"
        print "python3 /etc/temporal/workflows/" id "/etl/activities/init_workers.py &"
        print "python3 /etc/temporal/workflows/" id "/prediction/init_workers.py &"
        print "python3 /etc/temporal/workflows/" id "/simulations/init_workers.py &"
        print ""
        done=1
      }
      { print }' "$ENTRY" > "$TMP"
    # si no había 'tail -f' al final, añadimos al final
    if ! grep -q "workflows/$ID/" "$TMP"; then
      { cat "$ENTRY"; echo; for w in etl/static-info etl/activities prediction simulations; do
          echo "python3 /etc/temporal/workflows/$ID/$w/init_workers.py &"; done; } > "$TMP"
    fi
    cat "$TMP" > "$ENTRY"; rm -f "$TMP"
    echo "   workers añadidos a entrypoint.sh"
  fi

  # El namespace de Temporal normalmente lo crea el gateway al dar de alta el gemelo,
  # pero los workers arrancan antes y necesitan que ya exista. El gateway tolera
  # "Namespace already exists", así que lo creamos aquí.
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx temporal; then
    if docker exec temporal temporal operator namespace create --namespace "$ID" --retention 24h \
         --address temporal:7233 >/dev/null 2>&1; then
      echo "   namespace Temporal creado"
    else
      echo "   namespace Temporal ya existía (o no se pudo crear; el gateway lo creará)"
    fi
  fi

  # Arrancar los workers ahora, sin reiniciar el contenedor entero
  RUNNING=$(docker ps --format '{{.Names}}' 2>/dev/null || true)
  if grep -qx "$CONTAINER" <<<"$RUNNING"; then
    for w in etl/static-info etl/activities prediction simulations; do
      # evitar duplicados si ya está corriendo
      if docker exec "$CONTAINER" pgrep -f "workflows/$ID/$w/init_workers.py" >/dev/null 2>&1; then
        echo "   ya corre: $w"
      else
        docker exec -d "$CONTAINER" python3 "/etc/temporal/workflows/$ID/$w/init_workers.py"
        echo "   arrancado: $w"
      fi
    done
  else
    echo "   contenedor $CONTAINER no está en marcha: se arrancarán con el entrypoint"
  fi
done

echo
echo "Hecho. Ahora crea cada gemelo en la web con su geojson y comprueba la estación (ver README_gemelos.md)."
