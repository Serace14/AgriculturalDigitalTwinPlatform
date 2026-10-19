"""
Reproduce la calibración de harvest_ai_simulation.py a partir de los cortes reales.

Uso:
    python calibracion_cortes_alfalfa.py "datos Javier Zaragoza proyecto IA.xlsx"

Entrada: Excel con las hojas "Kg y cortes" (albaranes de entrega) y "parcelario".
Salida: nº de cortes, ciclo entre cortes, 1er corte, y (mediana, sigma log) de t MS/ha
por nº de corte -> son los valores de CUT_YIELD_T_MS_HA, SEASON_* y la referencia para
GDD_PER_CUT en la simulación.

Criterios (importan, con otros salen cifras absurdas):
  * Un corte = suma de los albaranes de la misma plantación, año y código TA1..TA6
    (un corte llega en varias entregas; dividir cada entrega por la superficie
    daba hasta 35 t MS/ha en el percentil 95).
  * Solo plantaciones cuya superficie ("hatotales") es única en el parcelario: en 83
    de 161 plantaciones las filas se contradicen y la superficie es ambigua.
  * Materia seca = columna "KGS_SECS a 12grados humedad" (kg a 12 % de humedad).
"""
import sys
import warnings

import numpy as np
import pandas as pd

warnings.simplefilter("ignore")


def main(path: str):
    k = pd.read_excel(path, sheet_name="Kg y cortes", header=1)
    p = pd.read_excel(path, sheet_name="parcelario", header=2)

    k["fecha"] = pd.to_datetime(k["DATA_DOC"], errors="coerce")
    k["corte"] = k["TALL"].astype(str).str.strip()
    k = k[k["corte"].str.startswith("TA")].copy()
    k["año"] = k["fecha"].dt.year
    k["n"] = k["corte"].str[2:].astype(int)
    k["kg_ms"] = pd.to_numeric(k["KGS_SECS a 12grados humedad"], errors="coerce")

    sup = p.groupby("PLANTACIÓN").agg(u=("hatotales", "nunique"), ha=("hatotales", "first")).reset_index()
    sup = sup[sup["u"] <= 1]
    sup["ha"] = pd.to_numeric(sup["ha"], errors="coerce")

    cortes = (k.groupby(["PLANTACIÓN", "año", "n"]).kg_ms.sum().reset_index()
                .merge(sup[["PLANTACIÓN", "ha"]], on="PLANTACIÓN"))
    cortes = cortes[(cortes["ha"] > 0) & (cortes["kg_ms"] > 0)].copy()
    cortes["t_ms_ha"] = cortes["kg_ms"] / 1000 / cortes["ha"]

    print(f"Cortes con superficie fiable: {len(cortes)} de {cortes['PLANTACIÓN'].nunique()} plantaciones")
    por_año = cortes.groupby(["PLANTACIÓN", "año"]).n.nunique()
    print(f"Cortes por plantación y año: mediana {por_año.median():.0f}, máximo {por_año.max()}")

    inicio = k.groupby(["PLANTACIÓN", "año", "n"]).fecha.min().reset_index().sort_values(["PLANTACIÓN", "año", "n"])
    inicio["dias"] = inicio.groupby(["PLANTACIÓN", "año"]).fecha.diff().dt.days
    d = inicio["dias"].dropna()
    d = d[(d > 10) & (d < 90)]
    q = d.quantile([.25, .5, .75]).tolist()
    print(f"Días entre cortes consecutivos: p25 {q[0]:.0f}, mediana {q[1]:.0f}, p75 {q[2]:.0f} (n={len(d)})")
    print(f"Día del año del 1er corte (mediana): {int(inicio[inicio.n == 1].fecha.dt.dayofyear.median())}")
    print("Meses con entregas:", k["fecha"].dt.month.value_counts().sort_index().to_dict())

    print("\nCUT_YIELD_T_MS_HA = {")
    for n, s in cortes.groupby("n").t_ms_ha:
        ls = np.log(s)
        print(f"    {n}: ({np.exp(ls.mean()):.2f}, {ls.std():.2f}),   # n={len(s)}")
    print("}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "datos Javier Zaragoza proyecto IA.xlsx")
