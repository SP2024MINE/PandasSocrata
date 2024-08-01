import streamlit as st
import pandas as pd
from sodapy import Socrata
import re
import datetime

st.title("Consulta de Datos de Contratación")

# Configuración de la API Socrata
client = Socrata("www.datos.gov.co", None)

consulta =  """SELECT 
proveedor_adjudicado,
tipo_de_contrato, 
modalidad_de_contratacion,
valor_del_contrato,
fecha_de_firma,
estado_contrato, 
duraci_n_del_contrato,
condiciones_de_entrega 	
WHERE nombre_entidad = "FABRICA DE LICORES DEL TOLIMA"
limit 2000"""
data_id = "jbjy-vk9h"

# Solicitud de datos
@st.cache_data
def load_data():
    results = client.get("jbjy-vk9h",query = consulta)
    return pd.DataFrame.from_records(results)

df = load_data()


# Función para convertir el tiempo a días
def convertir_a_dias(tiempo):
    match = re.match(r'(\d+)\s*(Dia\(s\)|Mes\(es\))', tiempo)
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        if unidad == 'Dia(s)':
            return cantidad
        elif unidad == 'Mes(es)':
            return cantidad * 30  # Asumiendo 30 días por mes
    return None
 
# Aplicar la función a la columna 'duracion'
df['duracion_en_dias'] = df['duraci_n_del_contrato'].apply(convertir_a_dias)
df = df.drop(columns=['duraci_n_del_contrato'])

#Corregir el tipo de variable a númerica
df['valor_del_contrato'] = df['valor_del_contrato'].astype(float)

# Nombre de proveedor en mayúsculas
df.proveedor_adjudicado = df.proveedor_adjudicado.str.upper()

# Fijar nuevo formato de fecha
df['fecha_de_firma'] = pd.to_datetime(df['fecha_de_firma'])
#df['fecha_de_firma'] = df['fecha_de_firma'].dt.date

# Mostrar datos

start_date = st.date_input('Fecha de inicio', df['fecha_de_firma'].min().date())
end_date = st.date_input('Fecha de finalización', df['fecha_de_firma'].max().date())

start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

df_filtrada0= df[(df['fecha_de_firma'] >= start_date) &
                 (df['fecha_de_firma'] <= end_date)]

list_tipo = df_filtrada0['tipo_de_contrato'].drop_duplicates()
 
tc= st.selectbox('Seleccione un tipo de contrato', list_tipo,
                        placeholder='Seleccione un tipo de contrato único')

df_filtrada1 = df_filtrada0[(df_filtrada0['tipo_de_contrato'] == tc)]

list_proveedor = df_filtrada1['proveedor_adjudicado'].drop_duplicates()

pa= st.selectbox('Seleccione un Proveedor Adjudicado', list_proveedor,
                        placeholder='Seleccione un proveedor')

df_filtrada2 = df_filtrada1[(df_filtrada1['proveedor_adjudicado'] == pa)]

cantidad_contratos = df_filtrada2['proveedor_adjudicado'].count()
st.metric(label=f'Cantidad de contratos', value=cantidad_contratos )

monto = df_filtrada2['valor_del_contrato'].sum()
st.metric(label=f'Monto total contratado', value=monto )

monto_mean = df_filtrada2['valor_del_contrato'].mean()
st.metric(label=f'Promedio de monto por contrato ', value=monto_mean )

st.write(df_filtrada2)
 