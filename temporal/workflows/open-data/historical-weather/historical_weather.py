# This is for common functions to be accepted as module imports
import sys
from temporalio import activity, workflow
with workflow.unsafe.imports_passed_through():
    import pandas as pd
    import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.functions import DB_MongoClient
from historical_weather_dto import historical_weather_dto, check_if_number, check_if_number_or_none
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

logging.basicConfig(level=logging.ERROR)


@dataclass
class Input_Extract:
    meteo_station_id: str
    date_init: str
    date_end: str


@activity.defn()
async def extract(input: Input_Extract) -> list[dict]:
    from aiohttp_client_cache import CachedSession, SQLiteBackend
    AUTH_TOKEN = os.environ.get("AGROSLAB_AUTH_TOKEN")
    AGROSLAB_API_URL = os.environ.get("AGROSLAB_API_URL")
    body = {
        "operation": "aemetclimatologiadiaria",
        # Date format: DD-MM-YYYY
        "initdate": input.date_init,
        "enddate": input.date_end,
        "idema": input.meteo_station_id
    }
    headers = {
        'Authorization': AUTH_TOKEN,
    }
    async with CachedSession(cache=SQLiteBackend(expire_after=60*60*24)) as session: # Works if activity is local
    # async with aiohttp.ClientSession() as session:
        async with session.post(AGROSLAB_API_URL, json=body, headers=headers, ssl=False) as resp:
            if resp.status != 200:
                text = await resp.text()
                # AEMET responde 404 ("No hay datos que satisfagan esos criterios") cuando la
                # estación no tiene observaciones en ese tramo (estación parada, hueco...) y
                # AGROSLAB lo convierte en un 500. Eso NO es un fallo: es un tramo vacío.
                # Antes se reintentaba y abortaba toda la carga.
                if "No hay datos que satisfagan" in text:
                    return []
                raise Exception(f"Status code: {resp.status} - {input.meteo_station_id} -> Response: {text}")
            data = await resp.json(content_type="text/plain") # content_type is needed because the response is not a json (it's a text/plain)
            return data
        
@dataclass
class Input_Transform:
    weather_data: list[dict]

@activity.defn(name="historical-weather-transform")
async def transform(input: Input_Transform) -> list[dict]:
    # Convert "," to "."
    weather_data = input.weather_data
    weather_data = [dict((k, v.replace(",", ".")) for k, v in weather_data.items()) for weather_data in weather_data]
    # Validate the response
    from jsonschema import validate
    try:
        validate(instance=weather_data, schema=historical_weather_dto)
    except Exception as e:
        raise Exception(f"Error validating the response: {e.message}")
    # Transform the response
    weather_data_list = []
    for weather_data in weather_data:
        weather_data_list.append({
                "date": str(weather_data.get("fecha") or None),
                "idema": str(weather_data.get("indicativo") or None),
                "height": check_if_number(weather_data.get("altitud") or None),
                "tmed": check_if_number(weather_data.get("tmed") or None),
                "prec": check_if_number(weather_data.get("prec") or None),
                "tmin": check_if_number(weather_data.get("tmin") or None),
                "tminTime": str(weather_data.get("horatmin") or None),
                "tmax": check_if_number(weather_data.get("tmax") or None),
                "tmaxTime": str(weather_data.get("horatmax") or None),
                "windDir": check_if_number(weather_data.get("dir") or None),
                "windSpeed": check_if_number(weather_data.get("velmedia") or None),
                "windGust": check_if_number(weather_data.get("racha") or None),
                "windGustTime": str(weather_data.get("horaracha") or None),
                # Humedad relativa (%) y horas de sol: la API las devuelve pero antes se
                # descartaban. None si la estación no las mide (no se rellenan con 0).
                "humidityMean": check_if_number_or_none(weather_data.get("hrMedia")),
                "humidityMax": check_if_number_or_none(weather_data.get("hrMax")),
                "humidityMin": check_if_number_or_none(weather_data.get("hrMin")),
                "sunHours": check_if_number_or_none(weather_data.get("sol")),
        })
    return weather_data_list

@dataclass
class Input_Load:
    digital_twin_id: str
    weather_data_list: list[dict]

@activity.defn()
async def load(input: Input_Load):
    # Un tramo sin datos (hueco de la estación) no es un error: no hay nada que cargar.
    # Antes insert_many([]) lanzaba una excepción.
    if not input.weather_data_list:
        return
    # Connect to MongoDB
    db = DB_MongoClient().connect(input.digital_twin_id)
    # Convert input.weather_data_list.date to datetime
    for weather_data in input.weather_data_list:
        weather_data["date"] = pd.to_datetime(weather_data["date"], format="%Y-%m-%d")
    # Idempotente: la carga siguiente arranca en la última fecha ya cargada, así que ese
    # día llegaba duplicado. Borramos antes el rango que vamos a insertar.
    # Because update_one is really slow, we use delete_many + insert_many
    dates = [w["date"] for w in input.weather_data_list]
    db.Weather.delete_many({"date": {"$gte": min(dates), "$lte": max(dates)}})
    db.Weather.insert_many(input.weather_data_list)

@dataclass
class Input_Create_Sequences:
    meteo_station_id: str
    date_init: str
    date_end: str

@activity.defn()
async def create_sequences(input: Input_Create_Sequences) -> list[list[str]]:
    # Extract every 3 years
    date_init = pd.to_datetime(input.date_init, format="%d-%m-%Y")
    date_end = pd.to_datetime(input.date_end, format="%d-%m-%Y")
    sequences = []
    while date_init < date_end:
        date_end_block = date_init + pd.DateOffset(months=1)
        if date_end_block > date_end:
            date_end_block = date_end
        sequences.append([date_init.strftime("%d-%m-%Y"), date_end_block.strftime("%d-%m-%Y")])
        date_init = date_end_block
    return sequences
        
@dataclass
class Input_Run:
    meteo_station_id: str
    digital_twin_ids: list[str]
    date_init: str
    date_end: str

@workflow.defn
class HistoricalWeatherWorkflow:
    @workflow.run
    async def run(self, input: Input_Run) -> None:
        sequences = await workflow.execute_local_activity(create_sequences, Input_Create_Sequences(input.meteo_station_id, input.date_init, input.date_end),
                                              start_to_close_timeout=timedelta(seconds=2),
                                              retry_policy=RetryPolicy(maximum_attempts=1, backoff_coefficient=1))
        tasks = []
        BATCH_SIZE = 1
        for i in range(0, len(sequences), BATCH_SIZE):
            tasks = []
            for sequence in sequences[i:i+BATCH_SIZE]:
                tasks.append(workflow.execute_activity(extract, Input_Extract(input.meteo_station_id, sequence[0], sequence[1]),
                                                        start_to_close_timeout=timedelta(seconds=60 * 5),
                                                        # La API (AGROSLAB -> AEMET) falla a ratos con 500: reintentos
                                                        # espaciados (15 s, 30 s, 60 s, 2 min, 3 min) en vez de 3 seguidos.
                                                        retry_policy=RetryPolicy(initial_interval=timedelta(seconds=15),
                                                                                 backoff_coefficient=2,
                                                                                 maximum_interval=timedelta(minutes=3),
                                                                                 maximum_attempts=6)))
            res = await asyncio.gather(*tasks, return_exceptions=True)
            # Sleep to avoid overloading the server
            await asyncio.sleep(3)
            for r in res:
                if isinstance(r, Exception):
                    logging.error(f"Error in meteo_station_id: {input.meteo_station_id} - {r}")
                    # PARAMOS en el primer tramo fallido. Antes se saltaba y se cargaban los
                    # meses siguientes: la próxima ejecución arranca en la ÚLTIMA fecha cargada,
                    # así que el hueco no se recuperaba nunca. Parando, la siguiente ejecución
                    # continúa exactamente donde se quedó.
                    raise ApplicationError(
                        f"Fallo al extraer la estación {input.meteo_station_id} "
                        f"({sequences[i][0]} a {sequences[i][1]}): {r}", non_retryable=True)
                if not r:
                    continue  # tramo sin datos: nada que transformar ni cargar
                data = await workflow.execute_activity(transform, Input_Transform(r),
                                                        start_to_close_timeout=timedelta(seconds=10),
                                                        retry_policy=RetryPolicy(maximum_attempts=1))
                for digital_twin_id in input.digital_twin_ids:
                    await workflow.execute_activity(load, Input_Load(digital_twin_id, data),
                                                start_to_close_timeout=timedelta(seconds=10),
                                                retry_policy=RetryPolicy(maximum_attempts=1, backoff_coefficient=2))
        


async def main(meteo_station_id: str, date_init: str, date_end: str):
    client = await Client.connect("localhost:7233")
    async with Worker(client,
                      task_queue="historical-weather-task-queue",
                      workflows=[HistoricalWeatherWorkflow],
                      activities=[extract, transform, load]):
        await client.execute_workflow(
                HistoricalWeatherWorkflow.run,
                Input_Run(meteo_station_id, date_init, date_end),
                id=f"historical-weather-workflow-{meteo_station_id}",
                task_queue="historical-weather-task-queue",
                retry_policy=RetryPolicy(maximum_attempts=1)
            )

if __name__ == "__main__":
    meteo_station_id = "2539"
    date_init = "01-01-2020"
    date_end = "31-12-2020"
    asyncio.run(main(meteo_station_id, date_init, date_end))
