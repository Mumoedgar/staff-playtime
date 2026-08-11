import streamlit as st
import re
import pandas as pd

st.set_page_config(page_title="Control Playtime Staff", page_icon="🎮", layout="wide")

st.title("🎮 Control de Actividad y Playtime Staff")
st.caption("Calculadora quincenal automática y detector de DEMOTES (<10h/semana)")

def parse_minecraft_time(text):
    if not text or not isinstance(text, str):
        return 0.0
    
    days = re.search(r'(\d+)\s*día', text)
    hours = re.search(r'(\d+)\s*hora', text)
    minutes = re.search(r'(\d+)\s*minuto', text)
    seconds = re.search(r'(\d+)\s*segundo', text)
    
    d = float(days.group(1)) if days else 0.0
    h = float(hours.group(1)) if hours else 0.0
    m = float(minutes.group(1)) if minutes else 0.0
    s = float(seconds.group(1)) if seconds else 0.0
    
    total_hours = (d * 24.0) + h + (m / 60.0) + (s / 3600.0)
    return round(total_hours, 2)

# Formulario para agregar / calcular datos
st.subheader("📥 Registro Quincenal de Usuarios")

# Datos por defecto para demostración
default_data = [
    {"Nick": "EdgarMunoz", "Q1_Text": "Tiempo total jugado: 59 día(s), 19 hora(s), 17 minuto(s), 45 segundo(s)", "Q2_Text": "Tiempo total jugado: 61 día(s), 21 hora(s), 40 minuto(s), 10 segundo(s)"},
    {"Nick": "CrafterPro", "Q1_Text": "Tiempo total jugado: 10 día(s), 00 hora(s), 00 minuto(s), 00 segundo(s)", "Q2_Text": "Tiempo total jugado: 10 día(s), 12 hora(s), 00 minuto(s), 00 segundo(s)"}
]

if 'staff_data' not in st.session_state:
    st.session_state.staff_data = default_data

with st.form("add_user_form"):
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        nick = st.text_input("Nick del Usuario", placeholder="Ej: EdgarMunoz")
    with col2:
        q1_text = st.text_input("Texto Q1 (Inicio Quincena)", placeholder="Tiempo total jugado: 59 día(s)...")
    with col3:
        q2_text = st.text_input("Texto Q2 (Fin Quincena)", placeholder="Tiempo total jugado: 61 día(s)...")
    
    submitted = st.form_submit_button("➕ Añadir / Actualizar Usuario")
    if submitted and nick:
        st.session_state.staff_data.append({"Nick": nick, "Q1_Text": q1_text, "Q2_Text": q2_text})
        st.success(f"¡Usuario **{nick}** procesado correctamente!")

# Procesar Tabla
processed_rows = []
for entry in st.session_state.staff_data:
    h_q1 = parse_minecraft_time(entry["Q1_Text"])
    h_q2 = parse_minecraft_time(entry["Q2_Text"])
    
    aumento = max(0.0, round(h_q2 - h_q1, 2)) if h_q2 >= h_q1 else 0.0
    horas_semana = round(aumento / 2.0, 2)
    
    pct_incremento = round((aumento / h_q1) * 100, 1) if h_q1 > 0 else 0.0
    
    status = "⚠️ DEMOTE" if horas_semana < 10.0 else "✅ ACTIVO"
    
    processed_rows.append({
        "Nick": entry["Nick"],
        "Horas Q1": h_q1,
        "Horas Q2": h_q2,
        "Horas Jugadas (Quincena)": aumento,
        "Media Horas / Semana": horas_semana,
        "% Crecimiento": f"+{pct_incremento}%",
        "Estado": status
    })

if processed_rows:
    df = pd.DataFrame(processed_rows)
    df = df.sort_values(by="Horas Jugadas (Quincena)", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "Rank"

    st.markdown("---")
    
    # KPIs Rápidos
    top_user = df.iloc[0]["Nick"] if not df.empty else "N/A"
    demotes_count = len(df[df["Estado"] == "⚠️ DEMOTE"])
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("👑 Top Más Activo", top_user)
    kpi2.metric("⚠️ En riesgo de DEMOTE (<10h/sem)", f"{demotes_count} usuarios")
    kpi3.metric("📊 Promedio Horas/Semana", f"{round(df['Media Horas / Semana'].mean(), 1)} hrs")

    st.subheader("🏆 Ranking y Evaluación de Staff")
    
    # Aplicar estilos
    def highlight_demote(val):
        color = '#ffcdd2' if 'DEMOTE' in str(val) else '#c8e6c9'
        return f'background-color: {color}; font-weight: bold;'

    st.dataframe(df.style.applymap(highlight_demote, subset=['Estado']), use_container_width=True)