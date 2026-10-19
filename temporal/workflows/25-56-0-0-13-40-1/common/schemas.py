import pandera as pa

# Schemas
activities_schema = pa.DataFrameSchema({
    "FECHA": pa.Column(pa.String, nullable=True),
    "TAREA-PRODUCTO-DOSIS": pa.Column(pa.String, nullable=True),
    "PARCELA": pa.Column(pa.String, nullable=True),
    "RECINTO ID": pa.Column(pa.String, nullable=True),
}, coerce=True)

# Antes: recintos_almendros_parcelas_schema (pensado para frutal: Nº Arboles, Marcoplantacionh)
# Alfalfa es un cultivo herbáceo de siembra directa, no de plantación de pies individuales,
# así que se eliminan los campos que solo tienen sentido para árboles:
#   - "Nº Arboles": no hay un recuento de individuos en un cultivo sembrado a voleo/en líneas
#   - "Marcoplantacionh": el "marco de plantación" (separación entre árboles) no aplica aquí
# Se mantiene "Densidaddesiembra" (densidad de siembra, p.ej. kg semilla/ha), que de hecho es
# un dato más relevante para alfalfa que para un frutal. También se mantiene "AñoPlantacion"
# (año de siembra), útil para calcular la edad del alfalfar (ver stand_age_years en la simulación).
recintos_alfalfa_parcelas_schema = pa.DataFrameSchema({
    "ProductorNIF": pa.Column(pa.String, required=False),
    "Cosecha": pa.Column(pa.Int),
    "Provincia Id": pa.Column(pa.String),
    "Municipio Id": pa.Column(pa.String),
    "Poligono": pa.Column(pa.String),
    "Parcela": pa.Column(pa.String),
    "Recinto": pa.Column(pa.String),
    "Paraje": pa.Column(pa.String),
    "Agregado": pa.Column(pa.String),
    "Zona": pa.Column(pa.String),
    "OrdenPAC": pa.Column(pa.String),
    "SubOrdenPac": pa.Column(pa.String),
    "SuperficieSIGPAC": pa.Column(pa.Float),
    "SuperficieCultivo": pa.Column(pa.Float),
    "Cultivo Id": pa.Column(pa.String),
    "ParcelaVariedad Id": pa.Column(pa.String, nullable=True),
    "SistemaDeRiego": pa.Column(pa.String, nullable=True),
    "RegimenTenenciaId": pa.Column(pa.String, nullable=True),
    "AñoPlantacion": pa.Column(pa.Int, nullable=True),
    "Densidaddesiembra": pa.Column(pa.String, nullable=True),
    "ATRIA / ADV / ASV": pa.Column(pa.String, nullable=True),
    "ZonaVulnerable": pa.Column(pa.String, nullable=True),
    "ZonaEspecifica": pa.Column(pa.String, nullable=True),
    "UsoParcela": pa.Column(pa.String, nullable=True),
    "Asesoramiento": pa.Column(pa.String, nullable=True),
    "Pendiente %": pa.Column(pa.Float),
    "UHC": pa.Column(pa.String, nullable=True),
    "Descripción UHC": pa.Column(pa.String, nullable=True),
    "Zona Zepa": pa.Column(pa.String),
    "Zona SIE": pa.Column(pa.String),
}, coerce=True, unique_column_names=True)

recintos_alfalfa_tratamientos_schema = pa.DataFrameSchema({
    "MovimientoCosecha": pa.Column(pa.Int),
    "MovimientoFechaDeInicio": pa.Column(pa.DateTime),
    "Producto": pa.Column(pa.String, nullable=True),
    "ProductoNombre": pa.Column(pa.String),
    "Formulado": pa.Column(pa.String, nullable=True),
    "TratamientosPlagaEfectosEnPlagasId": pa.Column(pa.String, nullable=True),
    "EfectosEnPlagas": pa.Column(pa.String),
    "TratamientosPlagaMalasHierbasId": pa.Column(pa.String, nullable=True),
    "SecUserNombre": pa.Column(pa.String),
    "SecUserNIF": pa.Column(pa.String, nullable=True),
    "SecUserId": pa.Column(pa.String),
    "ParcelaProvinciaId": pa.Column(pa.String),
    "ParcelaMunicipioId": pa.Column(pa.String),
    "ParcelaPoligono": pa.Column(pa.String),
    "Parcela": pa.Column(pa.String),
    "ParcelaRecinto": pa.Column(pa.String),
    "ParcelaParaje": pa.Column(pa.String, nullable=True),
    "ParcelaAgregado": pa.Column(pa.String),
    "ParcelaZona": pa.Column(pa.String),
    "ParcelaCosechaCodigoPAC": pa.Column(pa.String),
    "ParcelaCosechaCultivoPAC": pa.Column(pa.String),
    "Caldo": pa.Column(pa.String, nullable=True),
    "TipoDeDosisId": pa.Column(pa.String, nullable=True),
    "TipoDeDosisDetalle": pa.Column(pa.String),
    "MovimientoParcelaSuperficieTratada": pa.Column(pa.Float32),
    "Cantidad": pa.Column(pa.Float32),
    "MovimientoPlazoDeSeguridad": pa.Column(pa.String, nullable=True),
    "MovimientoDosis": pa.Column(pa.Float32),
    "ParcelaSuperficieCultivo": pa.Column(pa.Float32),
    "ParcelaSuperficieSIGPAC": pa.Column(pa.Float32, nullable=True),
    "ParcelaZonaVulnerable": pa.Column(pa.String, nullable=True),
    "UsoDeParcelasId": pa.Column(pa.String, nullable=True),
}, coerce=True, unique_column_names=True)

# Genérico (id, fecha, valor de cosecha) - válido tal cual para alfalfa,
# "cosecha" puede interpretarse como t MS/ha por corte en vez de kg por árbol.
harvest_schema = pa.DataFrameSchema({
    "id": pa.Column(pa.String, nullable=True),
    "fecha": pa.Column(pa.String, nullable=True),
    "cosecha": pa.Column(pa.Float32, nullable=True),
}, coerce=True)