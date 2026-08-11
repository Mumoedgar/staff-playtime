import json
import os
import re
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Control Playtime Staff", page_icon="🎮", layout="wide"
)

st.title("🎮 Control de Actividad y Playtime Staff")
st.caption(
    "Panel quincenal de seguimiento, evaluación de Staff y promociones/demotes"
)

# --- ARCHIVO DE PERSISTENCIA (GUARDADO LOCAL) ---
DB_FILE = "staff_data.json"


def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "EdgarMunoz": {
            "Rango": "Soporte",
            "Q1_Text": (
                "Tiempo total jugado: 50 día(s), 00 hora(s), 00 minuto(s), 00"
                " segundo(s)"
            ),
            "Q2_Text": (
                "Tiempo total jugado: 51 día(s), 12 hora(s), 00 minuto(s), 00"
                " segundo(s)"
            ),
            "Estado_Manual": "ACTIVO",
        },
        "CrafterPro": {
            "Rango": "Helper",
            "Q1_Text": (
                "Tiempo total jugado: 10 día(s), 00 hora(s), 00 minuto(s), 00"
                " segundo(s)"
            ),
            "Q2_Text": (
                "Tiempo total jugado: 10 día(s), 05 hora(s), 00 minuto(s), 00"
                " segundo(s)"
            ),
            "Estado_Manual": "ACTIVO",
        },
    }


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if "staff_db" not in st.session_state:
    st.session_state.staff_db = load_data()


# Función para convertir el texto de Minecraft a segundos exactos
def parse_minecraft_to_seconds(text):
    if not text or not isinstance(text, str):
        return 0

    days = re.search(r"(\d+)\s*día", text, re.IGNORECASE)
    hours = re.search(r"(\d+)\s*hora", text, re.IGNORECASE)
    minutes = re.search(r"(\d+)\s*minuto", text, re.IGNORECASE)
    seconds = re.search(r"(\d+)\s*segundo", text, re.IGNORECASE)

    d = int(days.group(1)) if days else 0
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0

    total_seconds = (d * 86400) + (h * 3600) + (m * 60) + s
    return total_seconds


# Función para dar formato a segundos exactos -> Xh Ym Zs
def format_seconds_to_exact_time(total_seconds):
    if total_seconds <= 0:
        return "0h 0m 0s"

    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = remainder % 60

    return f"{hours}h {minutes}m {seconds}s"


# Lista oficial de rangos permitidos
RANGOS_STAFF = ["Soporte", "Helper", "Mod"]

# --- SECCIÓN: SISTEMA DE BACKUP (IMPORTAR Y EXPORTAR) ---
with st.sidebar:
    st.header("💾 Copias de Seguridad")

    # EXPORTAR / DESCARGAR BACKUP
    json_data = json.dumps(
        st.session_state.staff_db, ensure_ascii=False, indent=4
    )
    st.download_button(
        label="📥 Descargar Backup (JSON)",
        data=json_data,
        file_name="backup_staff_playtime.json",
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("---")

    # IMPORTAR / RESTAURAR BACKUP
    st.subheader("📤 Restaurar Backup")
    uploaded_backup = st.file_uploader(
        "Subir archivo JSON de backup", type=["json"]
    )

    if uploaded_backup is not None:
        if st.button("🔄 Cargar y Restaurar Datos", use_container_width=True):
            try:
                restored_data = json.load(uploaded_backup)
                if isinstance(restored_data, dict):
                    st.session_state.staff_db = restored_data
                    save_data(restored_data)
                    st.success("¡Base de datos restaurada con éxito!")
                    st.rerun()
                else:
                    st.error("El archivo JSON no tiene un formato válido.")
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

    st.markdown("---")
    st.header("🔑 Configuración IA (Opcional)")
    gemini_key = st.text_input(
        "Gemini API Key (Para escanear capturas)",
        type="password",
        help=(
            "Si vas a usar el escáner de capturas por IA, coloca aquí tu API Key"
            " de Google Gemini."
        ),
    )

# --- SECCIÓN 1: FORMULARIO DE REGISTRO / ACTUALIZACIÓN ---
st.subheader("📝 Registrar / Actualizar Tiempo de Staff")

tab_ai, tab1, tab2 = st.tabs(
    ["📸 Escanear Captura (IA)", "➕ Entrada Manual (Q1)", "🔄 Actualizar Tiempo Q2"]
)

# --- TAB IA: SUBIR CAPTURA ---
with tab_ai:
    st.markdown("##### 📸 Escanear captura de pantalla de Minecraft")
    st.caption(
        "Sube la captura de la pantalla o del chat donde aparece el tiempo"
        " jugado del usuario."
    )

    col_img1, col_img2 = st.columns([1, 1])

    with col_img1:
        uploaded_image = st.file_uploader(
            "Sube una captura de pantalla (.png, .jpg, .jpeg)",
            type=["png", "jpg", "jpeg"],
            key="screenshot_uploader",
        )
        periodo_target = st.radio(
            "¿Para qué periodo es esta captura?",
            ["Q1 (Inicio de Quincena)", "Q2 (Fin de Quincena)"],
            horizontal=True,
        )
        rango_ai = st.selectbox(
            "Rango / Rol (para nuevos registros)",
            RANGOS_STAFF,
            key="ai_rango",
        )

    with col_img2:
        if uploaded_image is not None:
            image = Image.open(uploaded_image)
            st.image(image, caption="Captura subida", use_column_width=True)

    if uploaded_image is not None:
        if st.button("🔍 Escanear Captura con IA", type="primary"):
            api_key = gemini_key or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                st.error(
                    "⚠️ Necesitas ingresar una API Key de Gemini en la barra"
                    " lateral para usar el escáner automático."
                )
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")

                    prompt = """
                    Analiza la imagen de Minecraft adjunta.
                    Extrae exactamente dos cosas en formato JSON estricto:
                    1. "nick": El nombre del jugador (Nick / Username) que aparece en la pantalla o chat.
                    2. "tiempo_texto": El texto exacto del tiempo jugado (por ejemplo: "Tiempo total jugado: 50 día(s), 12 hora(s), 30 minuto(s), 00 segundo(s)").

                    Responde ÚNICAMENTE un JSON válido con esta estructura exacta:
                    {
                        "nick": "NombreDelUsuario",
                        "tiempo_texto": "Tiempo total jugado: X día(s), X hora(s), X minuto(s), X segundo(s)"
                    }
                    """

                    with st.spinner("Analizando la imagen con IA..."):
                        response = model.generate_content([image, prompt])
                        raw_text = response.text.strip()
                        clean_json_str = re.sub(
                            r"```json\s*|\s*
