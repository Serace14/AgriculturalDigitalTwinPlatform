"""
Integración del modelo de riesgo de enfermedad compartido por el compañero
(resultados_modelo_cereales/modelo_cereales.joblib) en el gemelo digital.

AVISO IMPORTANTE (verificado contra el propio notebook del compañero,
02_01_Herbaceos_Proteinicos.ipynb, sección 3): este modelo se entrenó
ÚNICAMENTE con datos de CEBADA y MAIZ (562 parcelas, 18.493 filas). En el
parquet usado para entrenar, "PROTEÍNICOS: 0 filas" - no hay ninguna fila de
alfalfa en el entrenamiento. Se usa aquí sobre alfalfa por decisión explícita
del equipo, como extrapolación no validada por el propio protocolo del
modelo. Conviene contrastar sus predicciones contra observaciones de campo
reales antes de tomar decisiones de tratamiento basadas en ellas, y avisar
al compañero si algo no cuadra.

Qué predice: NO es un modelo de rendimiento/cosecha. Es un clasificador
binario de riesgo de enfermedad (Alerta_enfermedad: bajo=0 / alto=1) a 3
días vista (HORIZON_DIAS=3 en el notebook original), a partir de variables
meteorológicas reales de estación (no del clima sintético de la simulación)
y su dinámica temporal por parcela (lags, medias/desviaciones móviles,
acumulados, grados-día).

Columna esperada de entrada (una fila por parcela y fecha), como mínimo:
    date, plot_id,
    average_temp, maximum_temp, minimum_temp,
    average_relative_humidity, maximum_relative_humidity, minimum_relative_humidity,
    average_wind_speed, maximum_wind_gust, precipitations, radiation,
    evapotranspiration_Penman_Monteith, effective_precipitation_Penman_Monteith,
    chillingHours
Si además se dispone del histórico real de Alerta_enfermedad para esa
parcela, inclúyelo también (columna 'Alerta_enfermedad', valores 'bajo'/'alto'):
mejora las features *_lag1/3/7/14 de la propia alerta. Si no se dispone de
él, se deja tal cual: el imputador interno del pipeline rellena los NaN.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .feature_engineering import (
    add_climate_derivatives,
    add_dynamic_features,
    add_temporal_features,
    BIOCLIM_VARS,
    DATE_COL,
    GDD_BASE_TEMP,
    LAG_DAYS,
    map_target_series,
    METEO_CANDIDATES,
    parse_date_safe,
    PLOT_ID_COL,
    TARGET_COL,
    WINDOWS,
)

MODEL_DIR = Path(__file__).parent / "model"

_modelo = None
_umbral = None
_cols_esperadas = None


def _load_model():
    global _modelo, _umbral, _cols_esperadas
    if _modelo is None:
        import joblib
        _modelo = joblib.load(MODEL_DIR / "modelo_cereales.joblib")
        meta = json.loads((MODEL_DIR / "metadata.json").read_text())
        _umbral = meta["umbral_recomendado"]
        _cols_esperadas = json.loads(
            (MODEL_DIR / "columnas_entrenamiento.json").read_text()
        )["input_columns"]
    return _modelo, _umbral, _cols_esperadas


def predict_disease_risk(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Recibe filas crudas (una por parcela y fecha) y devuelve, por fila,
    la probabilidad de riesgo alto y la etiqueta bajo/alto según el umbral
    recomendado por el compañero (no 0.5 - ver metadata.json)."""
    modelo, umbral, cols_esperadas = _load_model()

    df = df_raw.copy()
    if TARGET_COL in df.columns:
        df[TARGET_COL] = map_target_series(df[TARGET_COL])

    df = parse_date_safe(df, DATE_COL)
    df = add_temporal_features(df, DATE_COL)
    df = add_climate_derivatives(df, gdd_base=GDD_BASE_TEMP)
    df = add_dynamic_features(
        df, group_col=PLOT_ID_COL, date_ts_col="date_ts",
        windows=WINDOWS, lag_days=LAG_DAYS,
        meteo_cols=METEO_CANDIDATES, bioclim_cols=BIOCLIM_VARS, target_col=TARGET_COL,
    )

    X = df.copy()
    for c in cols_esperadas:
        if c not in X.columns:
            X[c] = np.nan
    X = X[cols_esperadas]

    proba = modelo.predict_proba(X)[:, 1]
    pred = (proba >= umbral).astype(int)

    result = df[[PLOT_ID_COL, DATE_COL]].copy()
    result["probAlto"] = np.round(proba, 4)
    result["riesgo"] = pd.Series(pred, index=result.index).map({0: "bajo", 1: "alto"})
    return result


# ---------------------------------------------------------------------------
# Envoltorio como actividad de Temporal, siguiendo el mismo patrón que
# harvest_ai_prediction.py del resto de la plataforma.
# ---------------------------------------------------------------------------
from dataclasses import dataclass
from datetime import datetime, timedelta
from temporalio import activity

# El notebook entrena con y_target = Alerta_enfermedad desplazada HORIZON_DIAS
# observaciones al futuro: la fila de la fecha D predice el riesgo en D + 3.
HORIZON_DIAS = 3


@dataclass
class InputPredictDiseaseRisk:
    digital_twin_id: str
    # Filas crudas (ver docstring del módulo), como lista de dicts para que
    # viajen por el data converter de Temporal. Cada dict es una fila:
    # {"date": "2026-05-01", "plot_id": "25-56-0-0-8-219-1",
    #  "average_temp": 18.2, "maximum_temp": 24.1, ...}
    raw_weather_rows: list
    # Se calcula sobre todas las filas (hacen falta ~3 semanas previas para los
    # lags y ventanas), pero solo se guardan las ÚLTIMAS persist_last_days fechas.
    persist_last_days: int = 1


@activity.defn()
async def predict_disease_risk_activity(input: "InputPredictDiseaseRisk") -> list:
    df_raw = pd.DataFrame(input.raw_weather_rows)
    result = predict_disease_risk(df_raw)
    _, umbral, _ = _load_model()

    result = result.sort_values(DATE_COL).tail(max(1, input.persist_last_days))
    now = datetime.utcnow()
    records = []
    for r in result.itertuples(index=False):
        date = pd.Timestamp(getattr(r, DATE_COL)).to_pydatetime()
        records.append({
            "plot_id": str(getattr(r, PLOT_ID_COL)),
            "date": date,                                   # fecha de las variables meteo
            "targetDate": date + timedelta(days=HORIZON_DIAS),  # fecha para la que se estima el riesgo
            "horizonDays": HORIZON_DIAS,
            "probAlto": float(r.probAlto),
            "riesgo": str(r.riesgo),
            "threshold": float(umbral),
            # Sin histórico de alertas el modelo pierde casi toda su capacidad
            # predictiva (ver README / análisis): se marca para que la interfaz
            # pueda avisar de que el resultado es orientativo.
            "usedAlertHistory": False,
            "model": "modelo_cereales (cebada/maíz) aplicado a alfalfa",
            "computedAt": now,
        })

    # Persistimos en Mongo con upsert por (plot_id, date): relanzar el cálculo
    # para la misma fecha sobrescribe en vez de duplicar.
    from pymongo import MongoClient
    import os
    client = MongoClient(os.getenv("MONGO_URI"))
    database = client[input.digital_twin_id]
    for x in records:   # pocas filas (days_to_predict): un update_one por fila es suficiente
        database["DiseaseRisk"].update_one({"plot_id": x["plot_id"], "date": x["date"]}, {"$set": x}, upsert=True)
    # Devolvemos fechas como texto: es lo que viaja bien por Temporal.
    return [{**x, "date": x["date"].strftime("%Y-%m-%d"),
             "targetDate": x["targetDate"].strftime("%Y-%m-%d"),
             "computedAt": x["computedAt"].isoformat()} for x in records]
