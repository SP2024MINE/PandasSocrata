import streamlit as st
import pandas as pd
from sodapy import Socrata
import re
import datetime
import altair as alt
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# import os
# from dotenv import load_dotenv
# load_dotenv('.env')

# APP_TOKEN = os.getenv("TOKEN_SODAPY")
# DATASET_ID = os.getenv("DATASET_ID")

st.title("Consulta de Datos de Contratación")
st.subheader("FABRICA DE LICORES DEL TOLIMA")

# Configuración de la API Socrata
client = Socrata("www.datos.gov.co", 
                #  APP_TOKEN
                 None
                 )

consulta =  """SELECT 
proveedor_adjudicado,
tipo_de_contrato, 
valor_del_contrato,
fecha_de_firma,
estado_contrato, 
duraci_n_del_contrato
WHERE nombre_entidad = "FABRICA DE LICORES DEL TOLIMA"
limit 2000"""


results = client.get(
    # DATASET_ID
    "jbjy-vk9h"
    , query=consulta)
df = pd.DataFrame.from_records(results)

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
df.tipo_de_contrato = df.tipo_de_contrato.str.upper()

# Fijar nuevo formato de fecha
df['fecha_de_firma'] = pd.to_datetime(df['fecha_de_firma'])

# Creamos columnas para mostrar los filtros de fecha
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input('Fecha de inicio', df['fecha_de_firma'].min().date())
with col2:
    end_date = st.date_input('Fecha de finalización', df['fecha_de_firma'].max().date())

start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

df_filtrada0= df[(df['fecha_de_firma'] >= start_date) &
                 (df['fecha_de_firma'] <= end_date)]

list_tipo = df_filtrada0['tipo_de_contrato'].value_counts().index.tolist()

tc= st.selectbox('Seleccione un tipo de contrato', list_tipo,
                        placeholder='Seleccione un tipo de contrato único')

df_filtrada1 = df_filtrada0[(df_filtrada0['tipo_de_contrato']== tc)]

# Construcción de métricas
cantidad_contratos = df_filtrada1['proveedor_adjudicado'].count()
monto = df_filtrada1['valor_del_contrato'].sum()
monto_mean = df_filtrada1['valor_del_contrato'].mean()

# Presentación de metricas en la misma fila
col1, col2, col3 = st.columns(3)
with col1:
    st.metric('Cantidad de contratos', f"{cantidad_contratos}")
with col2:
    st.metric('Monto total contratado', f"${monto:,.0f}")
with col3:
    st.metric('Promedio de monto por contrato', f"${monto_mean:,.0f}")

# Realizar el groupby
tabla_resumen = df_filtrada1.groupby('proveedor_adjudicado').agg(
    Contratos = ('proveedor_adjudicado', 'count'),
    Monto = ('valor_del_contrato', 'sum'),
    Duracion = ('duracion_en_dias', 'mean'),
).reset_index()

tabla_resumen = tabla_resumen.sort_values(by='Contratos', ascending=False)
tabla_resumen = tabla_resumen.rename(columns={
    'proveedor_adjudicado': 'Contratista'
})

tabla_resumen['Monto'] = tabla_resumen['Monto'].apply(lambda x: f"${x:,.0f}")
tabla_resumen['Duracion'] = tabla_resumen['Duracion'].apply(lambda x: f"{x:,.0f} días")


# Configurar la tabla interactiva
gb = GridOptionsBuilder.from_dataframe(tabla_resumen)
gb.configure_selection('single', use_checkbox=True)
grid_options = gb.build()

# Mostrar la tabla interactiva
st.write(f"""Tabla de contratistas:  
         Cantidad de contratos, monto total adjudicado y duración promedio en por contrato""")
grid_response = AgGrid(
    tabla_resumen,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.SELECTION_CHANGED,
    height=300,
    width='100%'
)

# Filtrar la data por el proveedor seleccionado
if grid_response['selected_rows'] is not None:
    selected_row = grid_response['selected_rows']
    selected_contratista = selected_row.iloc[0, 0]
    df_filtrada2 = df_filtrada1[(df_filtrada1['proveedor_adjudicado'] == selected_contratista)]

# Mantener la tabla si no se ha seleccionado un proveedor
else:
    df_filtrada2 = df_filtrada1 

st.header('Análisis Gráfico')

# Gráfico de Barras
bar_chart = alt.Chart(df_filtrada2).mark_bar().encode(
    x=alt.X('estado_contrato', axis=alt.Axis(title='Estado del Contrato')),
    y=alt.Y('mean(valor_del_contrato)', axis=alt.Axis(title=None)),
    color=alt.Color('estado_contrato', legend=None)
).properties(
    title='Valor promedio de contrato por estado'
)

# Gráfico Circular
pie_chart = alt.Chart(df_filtrada2).mark_arc().encode(
    theta=alt.Theta(field='estado_contrato', type='nominal', aggregate='count'),
    color=alt.Color(field='estado_contrato', type='nominal')
).properties(
    title='Cantidad de contratos por estado'
)

# Presentación de gráfico de barras y circular en la misma línea
col1, col2 = st.columns(2)
with col1:
    st.altair_chart(bar_chart, use_container_width=True)
with col2:
    st.altair_chart(pie_chart, use_container_width=True)

df_filtrada2['fecha_de_firma'] = df_filtrada2['fecha_de_firma'].dt.to_period('M').dt.to_timestamp()

# Gráfico de Líneas 
line_chart = alt.Chart(df_filtrada2).mark_line().encode(
    x=alt.X('fecha_de_firma', axis=alt.Axis(title='Fecha de firma')),
    y=alt.Y('sum(valor_del_contrato)', axis=alt.Axis(title=None)),
    color=alt.value('blue')
).properties(
    title='Valor total de contratos histórico por mes'
)
st.altair_chart(line_chart, use_container_width=True)