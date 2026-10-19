from typing import Any
def check_if_number(obj: Any) -> float:
    try:
        return float(str(obj).replace(",", "."))
    except:
        return 0.0
def check_if_number_or_none(obj: Any):
    """Como check_if_number, pero devuelve None (no 0.0) si el dato falta o no es
    numérico. Imprescindible para humedad y horas de sol: muchas estaciones AEMET no
    las miden y un 0 % de humedad falso sesgaría el modelo de riesgo de enfermedad."""
    if obj is None:
        return None
    try:
        return float(str(obj).replace(",", "."))
    except:
        return None
historical_weather_dto ={
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "altitud": {
        "type": "string"
      },
      "dir": {
        "type": "string"
      },
      "fecha": {
        "type": "string"
      },
      "horaHrMax": {
        "type": "string"
      },
      "horaHrMin": {
        "type": "string"
      },
      "horaPresMax": {
        "type": "string"
      },
      "horaPresMin": {
        "type": "string"
      },
      "horaracha": {
        "type": "string"
      },
      "horatmax": {
        "type": "string"
      },
      "horatmin": {
        "type": "string"
      },
      "hrMax": {
        "type": "string"
      },
      "hrMedia": {
        "type": "string"
      },
      "hrMin": {
        "type": "string"
      },
      "indicativo": {
        "type": "string"
      },
      "nombre": {
        "type": "string"
      },
      "prec": {
        "type": "string"
      },
      "presMax": {
        "type": "string"
      },
      "presMin": {
        "type": "string"
      },
      "provincia": {
        "type": "string"
      },
      "racha": {
        "type": "string"
      },
      "sol": {
        "type": "string"
      },
      "tmax": {
        "type": "string"
      },
      "tmed": {
        "type": "string"
      },
      "tmin": {
        "type": "string"
      },
      "velmedia": {
        "type": "string"
      }
    }
  }
}