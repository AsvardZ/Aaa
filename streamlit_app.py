
import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.set_page_config(page_title="Albion Online - Precios del Marketplace", layout="wide")
st.title("📊 Precios del Marketplace - Albion Online (v3.1 Estable)")
st.markdown("Consulta precios **actualizados** de monturas, herramientas y recursos procesados por ciudad. Descarga el Excel con nombres reales y analiza las mejores ganancias.")

cities = ["Bridgewatch", "Martlock", "Thetford", "Fort Sterling", "Lymhurst", "Caerleon"]

@st.cache_data(ttl=3600)
def cargar_nombres_items():
    url = "https://raw.githubusercontent.com/broderickhyman/ao-bin-dumps/master/formatted/items.json"
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as e:
        st.error("❌ No se pudo obtener los nombres desde la API.")
        return {}

    if not isinstance(data, list):
        st.error("❌ Formato de datos inesperado: no es una lista.")
        return {}

    nombres = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        index = item.get("Index")
        localized = item.get("LocalizedNames")
        if not index or not isinstance(localized, dict):
            continue
        nombre_es = localized.get("ES-ES") or localized.get("EN-US")
        if not nombre_es:
            continue
        if index.startswith("T") and "_" in index:
            tier = index[1]
            nombre_completo = f"{nombre_es} T{tier}"
        else:
            nombre_completo = nombre_es
        nombres[index] = nombre_completo
    return nombres

def obtener_items_filtrados():
    nombres = cargar_nombres_items()
    categorias = ["MOUNT_", "TOOL_", "ORE_", "WOOD_", "FIBER_", "HIDE_", "STONE_", "BAR_", "PLANK_", "CLOTH_", "LEATHER_", "BLOCK_"]
    filtrados = [k for k in nombres if any(cat in k for cat in categorias) and k.startswith("T")]
    return filtrados, nombres

if st.button("🔄 Generar precios actualizados"):
    st.info("Obteniendo precios y procesando información...")
    items_filtrados, nombres_dic = obtener_items_filtrados()
    base_url = "https://www.albion-online-data.com/api/v2/stats/prices/"
    resultados = []

    for i in range(0, len(items_filtrados), 50):
        grupo = items_filtrados[i:i+50]
        url = f"{base_url}{','.join(grupo)}?locations={','.join(cities)}"
        try:
            res = requests.get(url)
            if res.status_code == 200:
                for entry in res.json():
                    sell = entry.get("sell_price_min", 0)
                    buy = entry.get("buy_price_max", 0)
                    if sell > 0 and buy > 0:
                        item_id = entry["item_id"]
                        nombre_visible = nombres_dic.get(item_id, item_id)
                        resultados.append({
                            "Ciudad": entry["city"],
                            "Ítem": nombre_visible,
                            "Precio Venta (jugadores)": sell,
                            "Precio Compra (jugadores)": buy,
                            "Ganancia Potencial": sell - buy
                        })
        except Exception as e:
            st.warning(f"Error consultando ítems: {e}")

    if resultados:
        df = pd.DataFrame(resultados)
        st.success("✅ Datos cargados correctamente.")
        st.dataframe(df.sort_values("Ganancia Potencial", ascending=False), use_container_width=True)

        st.markdown("### 🏆 Top Ganancias por Ciudad")
        resumen = df.sort_values("Ganancia Potencial", ascending=False).groupby("Ciudad").first().reset_index()
        st.dataframe(resumen[["Ciudad", "Ítem", "Ganancia Potencial"]], use_container_width=True)

        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button(
            label="📥 Descargar Excel",
            data=output.getvalue(),
            file_name="precios_albion_actualizados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No se encontraron ítems con precios de compra y venta simultáneos.")
