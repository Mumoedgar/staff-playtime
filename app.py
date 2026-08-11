import streamlit as st
import re
import pandas as pd
import plotly.express as px
import json
import os
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="Control Playtime Staff", page_icon="🎮", layout="wide")

st.title("🎮 Control de Actividad y Playtime Staff")
st.caption("Panel quincenal de seguimiento, evaluación de Staff y promociones/demotes")

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
            "Q1_Text": "Tiempo total jugado: 50 día(s), 00 hora(s), 00 minuto(s), 00 segundo(s)",
            "Q2_Text": "Tiempo total jugado: 51 día(s), 12 hora(s), 00 minuto(s), 00 segundo(s)",
            "Estado_Manual": "ACTIVO"
        },
        "CrafterPro": {
            "Rango": "Helper",
            "Q1_Text": "Tiempo total jugado: 10 día(s), 00 hora(s), 00 minuto(s), 00 segundo(s)",
            "Q2_Text": "Tiempo total jugado: 10 día(s), 05 hora(s), 00 minuto(s), 00 segundo(s)",
            "Estado_Manual": "ACTIVO"
        }
    }

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'staff_db' not in st.session_state:
    st.session_state.staff_db = load_data()

# Función para convertir el texto de Minecraft a segundos exactos
def parse_minecraft_to_seconds(text):
    if not text or not isinstance(text, str):
        return 0
    
    days = re.search(r'(\d+)\s*día', text, re.IGNORECASE)
    hours = re.search(r'(\d+)\s*hora', text, re.IGNORECASE)
    minutes = re.search(r'(\d+)\s*minuto', text, re.IGNORECASE)
    seconds = re.search(r'(\d+)\s*segundo', text, re.IGNORECASE)
    
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
    json_data = json.dumps(st.session_state.staff_db, ensure_ascii=False, indent=4)
    st.download_button(
        label="📥 Descargar Backup (JSON)",
        data=json_data,
        file_name="backup_staff_playtime.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.markdown("---")
    
    # IMPORTAR / RESTAURAR BACKUP
    st.subheader("📤 Restaurar Backup")
    uploaded_backup = st.file_uploader("Subir archivo JSON de backup", type=["json"])
    
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
    gemini_key = st.text_input("Gemini API Key (Para escanear capturas)", type="password", help="Si vas a usar el escáner de capturas por IA, coloca aquí tu API Key de Google Gemini.")

# --- SECCIÓN 1: FORMULARIO DE REGISTRO / ACTUALIZACIÓN ---
st.subheader("📝 Registrar / Actualizar Tiempo de Staff")

tab_ai, tab1, tab2 = st.tabs(["📸 Escanear Captura (IA)", "➕ Entrada Manual (Q1)", "🔄 Actualizar Tiempo Q2"])

# --- TAB IA: SUBIR CAPTURA ---
with tab_ai:
    st.markdown("##### 📸 Escanear captura de pantalla de Minecraft")
    st.caption("Sube la captura de la pantalla o del chat donde aparece el tiempo jugado del usuario.")
    
    col_img1, col_img2 = st.columns([1, 1])
    
    with col_img1:
        uploaded_image = st.file_uploader("Sube una captura de pantalla (.png, .jpg, .jpeg)", type=["png", "jpg", "jpeg"], key="screenshot_uploader")
        periodo_target = st.radio("¿Para qué periodo es esta captura?", ["Q1 (Inicio de Quincena)", "Q2 (Fin de Quincena)"], horizontal=True)
        rango_ai = st.selectbox("Rango / Rol (para nuevos registros)", RANGOS_STAFF, key="ai_rango")

    with col_img2:
        if uploaded_image is not None:
            image = Image.open(uploaded_image)
            st.image(image, caption="Captura subida", use_container_width=True)

    if uploaded_image is not None:
        if st.button("🔍 Escanear Captura con IA", type="primary"):
            api_key = gemini_key or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                st.error("⚠️ Necesitas ingresar una API Key de Gemini en la barra lateral para usar el escáner automático.")
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
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
                        
                        # Limpiar el formato Markdown ```json ... ``` sin causar SyntaxError
                        clean_json_str = raw_text
                        if "```" in clean_json_str:
                            clean_json_str = re.sub(r"^```[a-z]*\n?", "", clean_json_str, flags=re.MULTILINE)
                            clean_json_str = re.sub(r"\n?```$", "", clean_json_str, flags=re.MULTILINE)
                        
                        parsed_res = json.loads(clean_json_str.strip())
                        
                        detected_nick = parsed_res.get("nick", "").strip()
                        detected_time = parsed_res.get("tiempo_texto", "").strip()
                        
                        if detected_nick and detected_time:
                            st.success(f"✅ ¡Datos detectados! **Usuario:** `{detected_nick}` | **Tiempo:** `{detected_time}`")
                            
                            # Guardar directamente
                            if "Q1" in periodo_target:
                                if detected_nick in st.session_state.staff_db:
                                    st.session_state.staff_db[detected_nick]["Rango"] = rango_ai
                                    st.session_state.staff_db[detected_nick]["Q1_Text"] = detected_time
                                else:
                                    st.session_state.staff_db[detected_nick] = {
                                        "Rango": rango_ai,
                                        "Q1_Text": detected_time,
                                        "Q2_Text": "",
                                        "Estado_Manual": "ACTIVO"
                                    }
                            else: # Q2
                                if detected_nick in st.session_state.staff_db:
                                    st.session_state.staff_db[detected_nick]["Q2_Text"] = detected_time
                                else:
                                    st.session_state.staff_db[detected_nick] = {
                                        "Rango": rango_ai,
                                        "Q1_Text": "",
                                        "Q2_Text": detected_time,
                                        "Estado_Manual": "ACTIVO"
                                    }
                            
                            save_data(st.session_state.staff_db)
                            st.success(f"¡Se han registrado automáticamente los datos de **{detected_nick}**!")
                            st.rerun()
                        else:
                            st.error("No se pudo detectar claramente el Nick o el Tiempo en la imagen. Inténtalo con una captura más nítida o agrégalo manualmente.")
                except Exception as e:
                    st.error(f"Error al procesar la imagen: {e}")

# --- TAB MANUAL Q1 ---
with tab1:
    with st.form("add_q1_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1.5, 1, 3])
        with col1:
            nick = st.text_input("Nick del Usuario", placeholder="Ej: EdgarMunoz", key="input_nick")
        with col2:
            rango = st.selectbox("Rango / Rol", RANGOS_STAFF, key="input_rango")
        with col3:
            q1_text = st.text_input("Tiempo Actual / Inicio Quincena (Q1)", placeholder="Tiempo total jugado: 59 día(s), 19 hora(s)...", key="input_q1")
        
        btn_add = st.form_submit_button("💾 Registrar Usuario en Quincena")
        if btn_add and nick:
            clean_nick = nick.strip()
            if clean_nick in st.session_state.staff_db:
                st.session_state.staff_db[clean_nick]["Rango"] = rango
                st.session_state.staff_db[clean_nick]["Q1_Text"] = q1_text
            else:
                st.session_state.staff_db[clean_nick] = {
                    "Rango": rango,
                    "Q1_Text": q1_text,
                    "Q2_Text": "",
                    "Estado_Manual": "ACTIVO"
                }
            save_data(st.session_state.staff_db)
            st.success(f"¡Usuario **{clean_nick}** guardado con éxito!")
            st.rerun()

# --- TAB MANUAL Q2 ---
with tab2:
    if st.session_state.staff_db:
        with st.form("add_q2_form", clear_on_submit=True):
            col_u, col_t = st.columns([1.5, 3])
            with col_u:
                selected_user = st.selectbox("Selecciona el Usuario", list(st.session_state.staff_db.keys()), key="input_select_user_q2")
            with col_t:
                q2_text = st.text_input("Tiempo al Finalizar Quincena (Q2)", placeholder="Tiempo total jugado: 61 día(s), 21 hora(s)...", key="input_q2")
            
            btn_update_q2 = st.form_submit_button("🏁 Guardar Fin de Quincena (Q2)")
            if btn_update_q2 and selected_user:
                st.session_state.staff_db[selected_user]["Q2_Text"] = q2_text
                save_data(st.session_state.staff_db)
                st.success(f"¡Tiempo final guardado para **{selected_user}**!")
                st.rerun()
    else:
        st.info("No hay usuarios registrados en la base de datos.")

st.markdown("---")

# --- SECCIÓN 2: TABLA Y PROCESAMIENTO ---
processed_rows = []
chart_data = []

for user_nick, data in st.session_state.staff_db.items():
    s_q1 = parse_minecraft_to_seconds(data["Q1_Text"])
    s_q2 = parse_minecraft_to_seconds(data["Q2_Text"])
    
    if s_q2 > 0 and s_q2 >= s_q1:
        s_gained = s_q2 - s_q1
    else:
        s_gained = 0
        
    s_weekly = s_gained // 2
    hours_gained = round(s_gained / 3600.0, 2)
    hours_weekly = round(s_weekly / 3600.0, 2)
    
    if s_q1 > 0 and s_gained > 0:
        pct_growth = round((s_gained / s_q1) * 100, 1)
        pct_str = f"+{pct_growth}%"
    else:
        pct_str = "0%"
        
    user_rank = data["Rango"]
    
    if data["Estado_Manual"] in ["RETIRADO", "EXPULSADO"]:
        eval_status = f"🔴 {data['Estado_Manual']}"
    elif s_q2 == 0:
        eval_status = "⏳ PENDIENTE Q2"
    else:
        if user_rank == "Soporte" and hours_gained >= 30.0:
            eval_status = "🟢 ACTIVO (POSIBLE PROMOTE)"
        elif user_rank == "Helper" and hours_weekly < 10.0:
            eval_status = "⚠️ INACTIVO (POSIBLE DEMOTE)"
        elif hours_weekly < 10.0:
            eval_status = "⚠️ DEMOTE"
        else:
            eval_status = "✅ ACTIVO"
            
    processed_rows.append({
        "Nick": user_nick,
        "Rango": user_rank,
        "Tiempo Q1 (Inicio)": format_seconds_to_exact_time(s
