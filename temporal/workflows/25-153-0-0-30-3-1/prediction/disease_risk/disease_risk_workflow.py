"""
Workflow que calcula el riesgo de enfermedad de un gemelo a partir de su
meteorología real (colección Weather, cargada desde AEMET) y guarda el
resultado en la colección DiseaseRisk.

Cómo se lanza (ejemplo, gemelo de alfalfa, riesgo de la última fecha disponible):
    docker exec temporal temporal workflow start \
      --namespace 25-153-0-0-30-3-1 --task-queue harvest-ai-prediction-task-queue \
      --type DiseaseRiskWorkflow --workflow-id disease-risk-test \
      --input '{"digital_twin_id": "25-153-0-0-30-3-1", "days_to_predict": 7}' \
      --address temporal:7233
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from .disease_risk_prediction import (
        InputPredictDiseaseRisk,
        predict_disease_risk_activity,
    )

# Correspondencia entre la colección Weather de la plataforma (AEMET, ver
# open-data/historical-weather) y las columnas que espera el modelo del compañero.
WEATHER_TO_MODEL = {
    "tmed": "average_temp",
    "tmax": "maximum_temp",
    "tmin": "minimum_temp",
    "humidityMean": "average_relative_humidity",
    "humidityMax": "maximum_relative_humidity",
    "humidityMin": "minimum_relative_humidity",
    "windSpeed": "average_wind_speed",
    "windGust": "maximum_wind_gust",
    "prec": "precipitations",
}
# Sin equivalente en AEMET diaria (no las tenemos): radiation,
# evapotranspiration_Penman_Monteith, effective_precipitation_Penman_Monteith y
# chillingHours. No se envían: el modelo las trata como datos ausentes y su
# imputador las rellena con la mediana del entrenamiento (chillingHours ya estaba
# ausente en el 70 % de las filas de entrenamiento).

MIN_ROWS = 8  # por debajo de esto los lags/ventanas no significan nada


@dataclass
class InputGetWeatherForRisk:
    digital_twin_id: str
    end_date: str = ""        # "YYYY-MM-DD"; vacío = última fecha disponible en Weather
    days_to_predict: int = 1
    history_days: int = 40    # días previos usados para lags y ventanas (máx. 21 + 14)


@activity.defn()
async def get_weather_for_disease_risk(input: InputGetWeatherForRisk) -> list:
    from datetime import datetime
    from pymongo import MongoClient
    import os
    db = MongoClient(os.getenv("MONGO_URI"))[input.digital_twin_id]

    if input.end_date:
        end = datetime.strptime(input.end_date, "%Y-%m-%d")  # nunca pd.to_datetime("d/m/Y")
    else:
        last = db["Weather"].find_one(sort=[("date", -1)])
        if not last:
            return []
        end = last["date"]
    start = end - timedelta(days=input.history_days + input.days_to_predict)

    by_date = {}
    for doc in db["Weather"].find({"date": {"$gte": start, "$lte": end}}).sort("date", 1):
        row = {"date": doc["date"].strftime("%Y-%m-%d"), "plot_id": input.digital_twin_id}
        for src, dst in WEATHER_TO_MODEL.items():
            v = doc.get(src)
            row[dst] = float(v) if v is not None else None
        # La carga histórica convierte los datos que faltan en 0.0. Si temperaturas o
        # viento salen todas a 0 el día no se midió: se marcan como ausentes en vez de
        # alimentar al modelo con 0 °C o 0 m/s falsos.
        if row["average_temp"] == 0 and row["maximum_temp"] == 0 and row["minimum_temp"] == 0:
            row["average_temp"] = row["maximum_temp"] = row["minimum_temp"] = None
        if row["average_wind_speed"] == 0 and row["maximum_wind_gust"] == 0:
            row["average_wind_speed"] = row["maximum_wind_gust"] = None
        by_date[row["date"]] = row   # si una fecha viene duplicada, gana la última
    rows = [by_date[d] for d in sorted(by_date)]
    if len(rows) < MIN_ROWS:
        activity.logger.warning(f"Solo {len(rows)} días de Weather en {input.digital_twin_id}; mínimo {MIN_ROWS}")
        return []
    return rows


@dataclass
class Input_DiseaseRisk:
    digital_twin_id: str = "25-153-0-0-30-3-1"
    end_date: str = ""
    days_to_predict: int = 1
    history_days: int = 40


@workflow.defn
class DiseaseRiskWorkflow:
    @workflow.run
    async def run(self, input: Input_DiseaseRisk) -> list:
        rows = await workflow.execute_activity(
            get_weather_for_disease_risk,
            InputGetWeatherForRisk(input.digital_twin_id, input.end_date, input.days_to_predict, input.history_days),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=2))
        if not rows:
            return []
        return await workflow.execute_activity(
            predict_disease_risk_activity,
            InputPredictDiseaseRisk(input.digital_twin_id, rows, input.days_to_predict),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=2))
