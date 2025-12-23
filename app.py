import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="CoD Team Balancer",
    page_icon="🎯",
    layout="centered"
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("🎯 Generador de Equipos CoD Mobile")
st.markdown("""
Esta herramienta crea equipos balanceados usando el algoritmo **"Snake Draft Ponderado"**.
Toma en cuenta el **K/D Ratio** (habilidad) y el **Nivel** (experiencia).
""")

# --- INICIALIZAR ESTADO (MEMORIA) ---
if 'jugadores' not in st.session_state:
    st.session_state.jugadores = []

# --- BARRA LATERAL (ENTRADA DE DATOS) ---
with st.sidebar:
    st.header("📝 Registro de Jugador")
    
    nombre = st.text_input("Gamertag (Nombre)")
    col1, col2 = st.columns(2)
    with col1:
        nivel = st.number_input("Nivel", min_value=0, max_value=350, value=150, step=10)
    with col2:
        ratio = st.number_input("K/D Ratio", min_value=0.0, max_value=10.0, value=1.0, step=0.1)

    if st.button("➕ Agregar Jugador", use_container_width=True):
        if nombre:
            # Fórmula de Amenaza
            score = (ratio * 100) + (nivel * 0.2)
            
            nuevo_jugador = {
                "Gamertag": nombre,
                "Nivel": nivel,
                "K/D": ratio,
                "Score": round(score, 1)
            }
            st.session_state.jugadores.append(nuevo_jugador)
            st.success(f"✅ {nombre} agregado")
        else:
            st.error("⚠️ Falta el nombre")

    st.markdown("---")
    if st.button("🗑️ Borrar Todos", type="primary"):
        st.session_state.jugadores = []
        st.rerun()

# --- ÁREA PRINCIPAL ---

# 1. Mostrar lista de jugadores actual
st.subheader(f"👥 Jugadores en Sala ({len(st.session_state.jugadores)})")

if len(st.session_state.jugadores) > 0:
    df = pd.DataFrame(st.session_state.jugadores)
    # Mostramos la tabla ordenada por Score para que vean quién es el "MVP" teórico
    st.dataframe(
        df.sort_values(by="Score", ascending=False), 
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("👈 Agrega jugadores desde el panel lateral para comenzar.")

st.markdown("---")

# 2. Configuración de Equipos
col_config1, col_config2 = st.columns([2, 1])
with col_config1:
    tamano = st.radio("Modo de Juego:", ["Duos (2)", "Trios (3)", "Squads (4)"], horizontal=True)
    n_jugadores = int(tamano.split("(")[1].replace(")", "")) # Extrae el número 2, 3 o 4

with col_config2:
    st.write("") # Espacio
    st.write("") 
    btn_generar = st.button("🎲 GENERAR EQUIPOS", type="primary", use_container_width=True)

# 3. Lógica y Resultados
if btn_generar:
    total_jugadores = len(st.session_state.jugadores)
    
    if total_jugadores < n_jugadores * 2:
        st.error(f"⚠️ Necesitas al menos {n_jugadores * 2} jugadores para armar 2 equipos.")
    else:
        # --- ALGORITMO SNAKE ---
        # A. Ordenar por Score
        lista_ordenada = sorted(st.session_state.jugadores, key=lambda x: x['Score'], reverse=True)
        
        # B. Crear contenedores
        num_equipos = total_jugadores // n_jugadores
        equipos = [[] for _ in range(num_equipos)]
        
        # C. Repartir
        reservas = []
        count = 0
        for i, jugador in enumerate(lista_ordenada):
            # Si excedemos la capacidad de equipos completos, van a reserva
            if i >= num_equipos * n_jugadores:
                reservas.append(jugador)
                continue
                
            indice_equipo = count % num_equipos
            vuelta = count // num_equipos
            
            # Invertir orden en vueltas impares (Snake)
            if vuelta % 2 == 1:
                indice_equipo = num_equipos - 1 - indice_equipo
            
            equipos[indice_equipo].append(jugador)
            count += 1

        # D. Mostrar Resultados
        st.success("✅ Equipos generados exitosamente")
        
        cols = st.columns(num_equipos)
        for i, col in enumerate(cols):
            equipo = equipos[i]
            promedio_score = sum(j['Score'] for j in equipo)
            avg_kd = sum(j['K/D'] for j in equipo) / len(equipo)
            
            with col:
                st.markdown(f"### 🛡️ Equipo {i+1}")
                st.caption(f"Poder Total: {promedio_score:.1f} | K/D Prom: {avg_kd:.2f}")
                
                txt_equipo = ""
                for jug in equipo:
                    txt_equipo += f"**{jug['Gamertag']}**\n\nNvl {jug['Nivel']} | KD {jug['K/D']}\n\n---\n\n"
                st.markdown(txt_equipo)

        # Mostrar Reservas si hay
        if reservas:
            st.warning("⚠️ Jugadores en Reserva (No completaron squad):")
            txt_reserva = ", ".join([j['Gamertag'] for j in reservas])
            st.write(txt_reserva)