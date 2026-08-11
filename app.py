import streamlit as st
import re
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Control Playtime Staff", page_icon="🎮", layout="wide")

st.title("🎮 Control de Actividad y Playtime Staff")
st.caption("Panel quincenal de seguimiento, evaluación de Staff y promociones/demotes")

# --- ARCHIVO DE PERSISTENCIA (GUARDADO EN DISCO) ---
DB_FILE = "staff_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Datos por defecto si no existe el archivo
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
    
    days = re.search(r'(\d+)\s*día', text)
    hours = re.search(r'(\d+)\s*hora', text)
    minutes = re.search(r'(\d+)\s*minuto', text)
    seconds = re.search(r'(\d+)\s*segundo', text)
    
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

# --- SECCIÓN 1: FORMULARIO DE REGISTRO / ACTUALIZACIÓN ---
st.subheader("📝 Registrar / Actualizar Tiempo de Staff")

tab1, tab2 = st.tabs(["➕ Añadir Nuevo / Tiempo Q1", "🔄 Actualizar Tiempo Q2 (Fin de Quincena)"])

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
            st.success(f"¡Usuario **{clean_nick}** guardado permanentemente!")
            st.rerun()

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
        "Tiempo Q1 (Inicio)": format_seconds_to_exact_time(s_q1),
        "Tiempo Q2 (Fin)": format_seconds_to_exact_time(s_q2) if s_q2 > 0 else "Sin registrar",
        "Tiempo Jugado (Quincena)": format_seconds_to_exact_time(s_gained),
        "Promedio Semanal": format_seconds_to_exact_time(s_weekly),
        "% Crecimiento": pct_str,
        "Estado / Evaluación": eval_status,
        "_raw_gained": s_gained
    })

    if s_q1 > 0:
        chart_data.append({"Staff": f"{user_nick} ({user_rank})", "Momento": "Inicio Quincena (Q1)", "Horas Totales": round(s_q1 / 3600.0, 1)})
        chart_data.append({"Staff": f"{user_nick} ({user_rank})", "Momento": "Fin Quincena (Q2)", "Horas Totales": round((s_q2 if s_q2 > 0 else s_q1) / 3600.0, 1)})

if processed_rows:
    df = pd.DataFrame(processed_rows)
    df = df.sort_values(by="_raw_gained", ascending=False).reset_index(drop=True)
    df.drop(columns=["_raw_gained"], inplace=True)
    df.index = df.index + 1
    df.index.name = "Rank"

    promotes_count = len(df[df["Estado / Evaluación"].str.contains("PROMOTE", na=False)])
    demotes_count = len(df[df["Estado / Evaluación"].str.contains("DEMOTE", na=False)])
    
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("🟢 Posibles Promociones", f"{promotes_count} miembros")
    col_k2.metric("⚠️ Posibles Demotes / Inactivos", f"{demotes_count} miembros")
    col_k3.metric("👥 Total Staff Registrado", f"{len(df)} miembros")

    st.subheader("🏆 Ranking y Evaluación de Staff")
    
    def style_status(val):
        if 'POSIBLE PROMOTE' in str(val):
            return 'background-color: #D1FAE5; color: #065F46; font-weight: bold;'
        elif 'POSIBLE DEMOTE' in str(val) or 'DEMOTE' in str(val):
            return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold;'
        elif 'ACTIVO' in str(val):
            return 'background-color: #E0E7FF; color: #3730A3; font-weight: bold;'
        elif 'RETIRADO' in str(val) or 'EXPULSADO' in str(val):
            return 'background-color: #F3F4F6; color: #6B7280; font-style: italic;'
        return ''

    try:
        styled_df = df.style.map(style_status, subset=['Estado / Evaluación'])
    except AttributeError:
        styled_df = df.style.applymap(style_status, subset=['Estado / Evaluación'])

    st.dataframe(styled_df, use_container_width=True)

    # --- SECCIÓN 3: GRÁFICO DE LÍNEAS DE EVOLUCIÓN ---
    st.markdown("---")
    st.subheader("📈 Evolución y Crecimiento de Playtime por Staff")
    
    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = px.line(
            df_chart, 
            x="Momento", 
            y="Horas Totales", 
            color="Staff", 
            markers=True,
            title="Progreso de Horas Acumuladas en Servidor (Q1 vs Q2)",
            labels={"Horas Totales": "Horas Acumuladas en Server", "Momento": "Período Evaluado"}
        )
        fig.update_traces(marker=dict(size=10))
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    # --- SECCIÓN 4: GESTIÓN DE EXPULSIONES, BORRADO Y REINICIO DE QUINCENA ---
    st.markdown("---")
    st.subheader("⚙️ Gestión y Acciones Globales")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.write("📌 **Cambiar Estado (Retirado / Expulsado)**")
        user_to_status = st.selectbox("Seleccionar Staff", list(st.session_state.staff_db.keys()), key="select_status")
        new_status = st.selectbox("Nuevo Estado", ["ACTIVO", "RETIRADO", "EXPULSADO"])
        if st.button("Aplicar Estado"):
            st.session_state.staff_db[user_to_status]["Estado_Manual"] = new_status
            save_data(st.session_state.staff_db)
            st.success(f"Estado de {user_to_status} cambiado a {new_status}")
            st.rerun()

    with col_m2:
        st.write("🗑️ **Eliminar Usuario de la Lista**")
        user_to_delete = st.selectbox("Seleccionar Staff a Borrar", list(st.session_state.staff_db.keys()), key="select_delete")
        if st.button("❌ Eliminar Permanentemente", type="primary"):
            del st.session_state.staff_db[user_to_delete]
            save_data(st.session_state.staff_db)
            st.success(f"Usuario {user_to_delete} eliminado.")
            st.rerun()

    with col_m3:
        st.write("🔄 **Iniciar Nueva Quincena**")
        st.caption("Pasa las horas Q2 a Q1 y deja Q2 libre para el siguiente periodo.")
        if st.button("🚀 Iniciar Nueva Quincena", type="secondary"):
            count_updated = 0
            for user, data in st.session_state.staff_db.items():
                if data["Q2_Text"]:
                    data["Q1_Text"] = data["Q2_Text"]
                    data["Q2_Text"] = ""
                    count_updated += 1
            save_data(st.session_state.staff_db)
            st.success(f"¡Quincena reiniciada! Se traspasaron los tiempos de {count_updated} usuarios.")
            st.rerun()
