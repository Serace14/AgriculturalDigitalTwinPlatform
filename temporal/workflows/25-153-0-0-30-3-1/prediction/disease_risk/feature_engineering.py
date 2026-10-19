"""
Funciones de feature engineering EXTRAÍDAS LITERALMENTE del notebook
02_01_Herbaceos_Proteinicos.ipynb (secciones 0 y 1). No reimplementadas:
copiadas tal cual para garantizar que el preprocesado en producción es
idéntico al usado en el entrenamiento de `modelo_cereales.joblib`.

Si el compañero actualiza el notebook (p. ej. al reentrenar con datos de
alfalfa/extensivos), este fichero debe volver a sincronizarse con la
sección 1 y la sección 0 (config) del notebook actualizado.
"""
import re
import unicodedata

import numpy as np
import pandas as pd

# --- Configuración (sección 0 del notebook, valores usados para entrenar
#     modelo_cereales.joblib - deben coincidir con metadata.json) ---
TARGET_COL = "Alerta_enfermedad"
DATE_COL = "date"
PLOT_ID_COL = "plot_id"

WINDOWS = [3, 7, 14, 21]
LAG_DAYS = [1, 3, 7, 14]
GDD_BASE_TEMP = 5.0

METEO_CANDIDATES = [
    "maximum_temp", "minimum_temp", "average_temp",
    "average_relative_humidity", "maximum_relative_humidity", "minimum_relative_humidity",
    "precipitations", "evapotranspiration_Penman_Monteith",
    "effective_precipitation_Penman_Monteith",
    "average_wind_speed", "maximum_wind_gust", "radiation", "chillingHours",
]
BIOCLIM_VARS = [
    "temp_range", "humidity_temp_index", "dew_point_approx",
    "water_balance", "gdd", "leaf_wetness_proxy",
]


def parse_date_safe(df, date_col):
    if date_col in df.columns:
        dt = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        df[date_col] = dt.dt.tz_localize(None)
    return df


def add_temporal_features(df, date_col):
    """Features de calendario + codificación cíclica (mes/día del año)."""
    if date_col in df.columns:
        dt = pd.to_datetime(df[date_col], errors="coerce")
        df["month"] = dt.dt.month.astype("float32")
        df["day_of_year"] = dt.dt.dayofyear.astype("float32")
        df["week_of_year"] = dt.dt.isocalendar().week.astype("float32")
        df["date_ts"] = (dt.view("int64") // 10**9).astype("float64")
        # Codificación cíclica: evita el salto artificial dic->ene y jun->jul.
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12).astype("float32")
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12).astype("float32")
        df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365).astype("float32")
        df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365).astype("float32")
        season_map = {
            12: "winter", 1: "winter", 2: "winter",
            3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer",
            9: "fall", 10: "fall", 11: "fall",
        }
        df["season"] = df["month"].map(season_map).astype("object")
    return df


def add_climate_derivatives(df, gdd_base=5.0):
    """Índices bioclimáticos instantáneos (del propio día)."""
    if {"maximum_temp", "minimum_temp"}.issubset(df.columns):
        df["temp_range"] = (df["maximum_temp"] - df["minimum_temp"]).astype("float32")
    if {"average_temp", "average_relative_humidity"}.issubset(df.columns):
        # Índice de favorabilidad fúngica (calor * humedad).
        df["humidity_temp_index"] = (df["average_temp"] * df["average_relative_humidity"]).astype("float32")
        df["dew_point_approx"] = (df["average_temp"] - ((100 - df["average_relative_humidity"]) / 5.0)).astype("float32")
        # Proxy de horas de hoja mojada: humedad muy alta favorece infección.
        df["leaf_wetness_proxy"] = (df["average_relative_humidity"] >= 85).astype("float32")
    if {"precipitations", "evapotranspiration_Penman_Monteith"}.issubset(df.columns):
        df["water_balance"] = (df["precipitations"] - df["evapotranspiration_Penman_Monteith"]).astype("float32")
    if {"maximum_temp", "minimum_temp"}.issubset(df.columns):
        # Grados-día de crecimiento (GDD) del día, base configurable.
        df["gdd"] = (((df["maximum_temp"] + df["minimum_temp"]) / 2.0) - gdd_base).clip(lower=0).astype("float32")
    return df


def add_dynamic_features(df, group_col, date_ts_col, windows, lag_days,
                          meteo_cols, bioclim_cols, target_col):
    """Dinámica temporal por parcela SIN fuga de información.

    Para cada parcela (ordenada por fecha) y cada variable meteo/bioclimática:
      - lags: valor de N observaciones atrás -> g[col].shift(N)
      - medias y desviaciones móviles a W observaciones, calculadas sobre
        shift(1) (solo pasado): nunca incluyen la fila actual.
      - acumulados de lluvia y de GDD a W observaciones (shift(1).rolling.sum).
      - rachas (streaks) de condiciones favorables: nº de observaciones
        consecutivas, hasta AYER, con humedad>=85% o balance hídrico positivo.
    """
    df = df.copy().sort_values([group_col, date_ts_col]).reset_index(drop=True)
    g = df.groupby(group_col, group_keys=False)
    feat_cols = [c for c in (meteo_cols + bioclim_cols) if c in df.columns]

    # --- Lags ---
    for col in feat_cols:
        for L in lag_days:
            df[f"{col}_lag{L}"] = g[col].shift(L)

    # --- Medias y desviaciones móviles (solo pasado) ---
    for col in feat_cols:
        s_shift = g[col].shift(1)
        grp = s_shift.groupby(df[group_col], group_keys=False)
        for W in windows:
            df[f"{col}_roll{W}_mean"] = grp.rolling(W, min_periods=1).mean().reset_index(level=0, drop=True)
            df[f"{col}_roll{W}_std"] = grp.rolling(W, min_periods=2).std().reset_index(level=0, drop=True)

    # --- Acumulados de lluvia y GDD (suma móvil del pasado) ---
    for col in [c for c in ["precipitations", "effective_precipitation_Penman_Monteith", "gdd"] if c in df.columns]:
        s_shift = g[col].shift(1)
        grp = s_shift.groupby(df[group_col], group_keys=False)
        for W in windows:
            df[f"{col}_acc{W}"] = grp.rolling(W, min_periods=1).sum().reset_index(level=0, drop=True)

    # --- Rachas de condiciones favorables (hasta ayer) ---
    def streak(mask_shift):
        out = np.zeros(len(mask_shift), dtype="float32")
        run = 0
        ids = df[group_col].values
        prev_id = None
        vals = mask_shift.values
        for i in range(len(vals)):
            if ids[i] != prev_id:
                run = 0
                prev_id = ids[i]
            out[i] = run
            run = run + 1 if (vals[i] == True) else 0
        return out

    if "leaf_wetness_proxy" in df.columns:
        df["streak_humedad_alta"] = streak(g["leaf_wetness_proxy"].shift(1).fillna(0) >= 1)
    if "water_balance" in df.columns:
        df["streak_balance_pos"] = streak(g["water_balance"].shift(1).fillna(-1) > 0)

    # --- Lag del propio target (riesgo reciente de la parcela) ---
    if target_col in df.columns:
        for L in lag_days:
            df[f"{target_col}_lag{L}"] = g[target_col].shift(L)

    return df


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def normalize_token(x) -> str:
    if pd.isna(x):
        return ""
    s = strip_accents(str(x).strip().lower())
    return re.sub(r"\s+", " ", s)


def map_target_series(series: pd.Series) -> pd.Series:
    """Solo necesario si se reentrena o se quiere usar Alerta_enfermedad_lagN
    con historial real. Para inferencia pura (sin histórico de alertas),
    esas columnas de lag se dejan como NaN y el imputador del pipeline las rellena."""
    norm = series.map(normalize_token)
    to_pos = {"alto", "alta", "alerta", "si", "1", "true", "t", "y", "yes",
              "positivo", "positiva", "high", "alert", "on"}
    to_neg = {"bajo", "baja", "0", "false", "f", "n", "no", "negativo", "negativa",
              "low", "no alerta", "off", "sin alerta", "normal", ""}
    mapped = pd.Series(index=norm.index, dtype="float64")
    mapped[norm.isin(to_pos)] = 1.0
    mapped[norm.isin(to_neg)] = 0.0
    mapped[mapped.isna()] = 0.0
    return mapped.astype(int)
