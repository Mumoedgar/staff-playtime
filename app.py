import streamlit as st
import re
import pandas as pd

st.set_page_config(page_title="Control Playtime Staff", page_icon="🎮", layout="wide")

st.title("🎮 Control de Actividad y Playtime Staff")
st.caption("Panel quincenal de seguimiento, rangos y evaluación de Staff de Minecraft")

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

# Inicializar Base de Datos en Session State
default_data = {
    "EdgarMunoz": {
        "Rango": "Mod",
        "Q1_Text": "Tiempo total jugado: 59 día(s), 19 hora(s), 17 minuto(s), 45 segundo(s)",
        "Q2_Text": "Tiempo total jugado: 61 día(s), 21 hora(s), 40 minuto(s), 10 segundo(s)",
        "Estado_Manual": "ACTIVO"
    },
    "CrafterPro": {
        "Rango": "Helper",
        "Q1_Text": "Tiempo total jugado: 10 día(s), 00 hora(s), 00 minuto(s), 00 segundo(s)",
        "Q2_Text": "Tiempo total jugado: 10 día(s), 12 hora(s), 00 minuto(s), 00 segundo(s)",
        "Estado_Manual": "ACTIVO"
    }
}

if 'staff_db' not in st.session_state:
    st.session_state.staff_db = default_data

# Lista oficial de rangos permitidos
RANGOS_STAFF = ["Soporte", "Helper", "Mod"]

# --- SECCIÓN 1: FORMULARIO DE REGISTRO / ACTUALIZACIÓN ---
st.subheader("📝 Registrar / Actualizar Tiempo de Staff")

tab1, tab2 = st.tabs(["➕ Añadir Nuevo / Tiempo Q1", "🔄 Actualizar Tiempo Q2 (Fin de Quincena)"])

with tab1:
    with st.form("add_q1_form"):
        col1, col2, col3 = st.columns([1.5, 1, 3])
        with col1:
            nick = st.text_input("Nick del Usuario", placeholder="Ej: EdgarMunoz")
        with col2:
            rango = st.selectbox("Rango / Rol", RANGOS_STAFF)
        with col3:
            q1_text = st.text_input("Tiempo Actual / Inicio Quincena (Q1)", placeholder="Tiempo total jugado: 59 día(s), 19 hora(s)...")
        
        btn_add = st.form_submit_button("💾 Registrar Usuario en Quincena")
        if btn_add and nick:
            clean_nick = nick.strip()
            if clean_nick in st.session_state.staff_db:
                st.session_state.staff_db[clean_nick]["Rango"] = rango
                st.session_state.staff_db[clean_nick]["Q1_Text"] = q1_text
                st.success(f"¡Se actualizó el rango a **{rango}** y el tiempo Q1 de **{clean_nick}**!")
            else:
                st.session_state.staff_db[clean_nick] = {
                    "Rango": rango,
                    "Q1_Text": q1_text,
                    "Q2_Text": "",
                    "Estado_Manual": "ACTIVO"
                }
                st.success(f"¡Usuario **{clean_nick}** ({rango}) registrado con éxito!")
            st.rerun()

with tab2:
    if st.session_state.staff_db:
        with st.form("add_q2_form"):
            col_u, col_t = st.columns([1.5, 3])
            with col_u:
                selected_user = st.selectbox("Selecciona el Usuario", list(st.session_state.staff_db.keys()))
            with col_t:
                q2_text = st.text_input("Tiempo al Finalizar Quincena (Q2)", placeholder="Tiempo total jugado: 61 día(s), 21 hora(s)...")
            
            btn_update_q2 = st.form_submit_button("🏁 Guardar Fin de Quincena (Q2)")
            if btn_update_q2 and selected_user:
                st.session_state.staff_db[selected_user]["Q2_Text"] = q2_text
                st.success(f"¡Tiempo final guardado para **{selected_user}**!")
                st.rerun()
    else:
        st.info("No hay usuarios registrados en la base de datos.")

st.markdown("---")

# --- SECCIÓN 2: TABLA Y PROCESAMIENTO ---
processed_rows = []

for user_nick, data in st.session_state.staff_db.items():
    s_q1 = parse_minecraft_to_seconds(data["Q1_Text"])
    s_q2 = parse_minecraft_to_seconds(data["Q2_Text"])
    
    # Cálculos exactos
    if s_q2 > 0 and s_q2 >= s_q1:
        s_gained = s_q2 - s_q1
    else:
        s_gained = 0
        
    s_weekly = s_gained // 2  # Media semanal
    
    # % Crecimiento
    if s_q1 > 0 and s_gained > 0:
        pct_growth = round((s_gained / s_q1) * 100, 1)
        pct_str = f"+{pct_growth}%"
    else:
        pct_str = "0%"
        
    # Evaluación de Demote (< 10 horas semanales = 36000 segundos)
    if data["Estado_Manual"] in ["RETIRADO", "EXPULSADO"]:
        eval_status = f"🔴 {data['Estado_Manual']}"
    else:
        if s_q2 == 0:
            eval_status = "⏳ PENDIENTE Q2"
        elif s_weekly < 36000:
            eval_status = "⚠️ DEMOTE"
        else:
            eval_status = "✅ ACTIVO"
            
    processed_rows.append({
        "Nick": user_nick,
        "Rango": data["Rango"],
        "Tiempo Q1 (Inicio)": format_seconds_to_exact_time(s_q1),
        "Tiempo Q2 (Fin)": format_seconds_to_exact_time(s_q2) if s_q2 > 0 else "Sin registrar",
        "Tiempo Jugado (Quincena)": format_seconds_to_exact_time(s_gained),
        "Promedio Semanal": format_seconds_to_exact_time(s_weekly),
        "% Crecimiento": pct_str,
        "Estado / Evaluación": eval_status,
        "_raw_gained": s_gained
    })

if processed_rows:
    df = pd.DataFrame(processed_rows)
    # Ordenar por tiempo jugado en la quincena
    df = df.sort_values(by="_raw_gained", ascending=False).reset_index(drop=True)
    df.drop(columns=["_raw_gained"], inplace=True)
    df.index = df.index + 1
    df.index.name = "Rank"

    # KPIs Rápidos
    active_users = df[~df["Estado / Evaluación"].str.contains("RETIRADO|EXPULSADO", na=False)]
    top_user = active_users.iloc[0]["Nick"] if not active_users.empty else "N/A"
    demotes_count = len(df[df["Estado / Evaluación"] == "⚠️ DEMOTE"])
    
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("👑 Top Más Activo", top_user)
    col_k2.metric("⚠️ En riesgo de DEMOTE (<10h/sem)", f"{demotes_count} usuarios")
    col_k3.metric("👥 Total Staff Registrado", f"{len(df)} miembros")

    st.subheader("🏆 Ranking y Evaluación de Staff")
    
    def style_status(val):
        if 'DEMOTE' in str(val):
            return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold;'
        elif 'ACTIVO' in str(val):
            return 'background-color: #DCFCE7; color: #166534; font-weight: bold;'
        elif 'RETIRADO' in str(val) or 'EXPULSADO' in str(val):
            return 'background-color: #F3F4F6; color: #6B7280; font-style: italic;'
        return ''

    try:
        styled_df = df.style.map(style_status, subset=['Estado / Evaluación'])
    except AttributeError:
        styled_df = df.style.applymap(style_status, subset=['Estado / Evaluación'])

    st.dataframe(styled_df, use_container_width=True)

    # --- SECCIÓN 3: GESTIÓN DE EXPULSIONES Y BORRADO ---
    st.markdown("---")
    st.subheader("⚙️ Gestión y Sanciones de Staff")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.write("📌 **Cambiar Estado (Retirado / Expulsado)**")
        user_to_status = st.selectbox("Seleccionar Staff", list(st.session_state.staff_db.keys()), key="select_status")
        new_status = st.selectbox("Nuevo Estado", ["ACTIVO", "RETIRADO", "EXPULSADO"])
        if st.button("Aplicar Estado"):
            st.session_state.staff_db[user_to_status]["Estado_Manual"] = new_status
            st.success(f"Estado de {user_to_status} cambiado a {new_status}")
            st.rerun()

    with col_m2:
        st.write("🗑️ **Eliminar Usuario de la Lista**")
        user_to_delete = st.selectbox("Seleccionar Staff a Borrar", list(st.session_state.staff_db.keys()), key="select_delete")
        if st.button("❌ Eliminar Permanentemente", type="primary"):
            del st.session_state.staff_db[user_to_delete]
            st.success(f"Usuario {user_to_delete} eliminado.")
            st.rerun()
