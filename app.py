import os
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, cast, Sequence, Hashable
import streamlit.components.v1 as components
import statistics

# Importar funciones y utilidades desde el módulo core (lógica separada)
from core import (
    _sanitizar_nombre,
    _jugador_existe,
    cargar_datos,
    guardar_datos,
    balancear_equipos_greedy_swaps,
)
from core_db import init_db, cargar_datos_db, guardar_datos_db


# Backend por defecto: usar SQLite si existe el archivo, sino CSV
default_backend = 'sqlite' if os.path.exists('jugadores.db') else 'csv'
if 'backend' not in st.session_state:
    st.session_state.backend = default_backend


def load_players_from_backend() -> List[Dict[str, Any]]:
    if st.session_state.get('backend') == 'sqlite':
        init_db()
        return cast(List[Dict[str, Any]], cargar_datos_db())
    return cast(List[Dict[str, Any]], cargar_datos())


def save_players_to_backend(lista: Sequence[Dict[str, Any]]) -> None:
    # Aceptar una Sequence (covariante) para evitar errores de tipo y
    # convertir a list antes de pasar a las funciones que esperan listas concretas.
    if st.session_state.get('backend') == 'sqlite':
        guardar_datos_db(cast(Sequence[Dict[Hashable, Any]], list(lista)))
    else:
        guardar_datos(list(lista))


# Inicializar la lista de jugadores en session state si no existe o si backend cambió
if 'jugadores' not in st.session_state or st.session_state.get('backend_loaded') != st.session_state.get('backend'):
    st.session_state.jugadores = load_players_from_backend()
    st.session_state.backend_loaded = st.session_state.get('backend')



# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Team Balancer",
    page_icon="🎯",
    layout="centered"
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("Generador de Equipos")
st.caption(f"Persistencia: {'SQLite (jugadores.db)' if st.session_state.get('backend')=='sqlite' else 'CSV (jugadores_db.csv)'}")
st.markdown("""
Esta herramienta crea equipos balanceados usando el algoritmo **"Snake Draft Ponderado"**.
Toma en cuenta el **K/D Ratio** (habilidad) y el **Nivel** (experiencia).
""")

# --- BARRA LATERAL (ENTRADA DE DATOS) ---
with st.sidebar:
    backend_choice = st.radio("Persistencia:", ["CSV","SQLite (jugadores.db)"], index=0 if st.session_state.get('backend','csv')=='csv' else 1)
    selected_backend = 'sqlite' if backend_choice.startswith('SQLite') else 'csv'
    if selected_backend != st.session_state.get('backend'):
        st.session_state.backend = selected_backend
        st.session_state.jugadores = load_players_from_backend()
        st.session_state.backend_loaded = selected_backend

    st.markdown(f"**Persistencia actual:** { 'SQLite (jugadores.db)' if st.session_state.get('backend')=='sqlite' else 'CSV (jugadores_db.csv)'}")

    nombre = st.text_input("Gamertag (Nombre)")
    col1, col2 = st.columns(2)
    with col1:
        nivel = st.number_input("Nivel", min_value=0, max_value=350, value=150, step=10)
    with col2:
        ratio = st.number_input("K/D Ratio", min_value=0.0, max_value=10.0, value=1.0, step=0.1)

    if st.button("➕ Agregar Jugador", use_container_width=True):
        nombre_limpio = _sanitizar_nombre(nombre or "")

        # Validaciones básicas
        if not nombre_limpio:
            st.error("⚠️ El gamertag está vacío o no es válido.")
        elif _jugador_existe(cast(Sequence[Dict[str, Any]], st.session_state.jugadores), nombre_limpio):
            st.error("⚠️ Ya existe un jugador con ese gamertag.")
        elif not (0 <= nivel <= 350):
            st.error("⚠️ El nivel debe estar entre 0 y 350.")
        elif not (0.0 <= ratio <= 10.0):
            st.error("⚠️ El K/D debe estar entre 0.0 y 10.0.")
        else:
            # Fórmula de Amenaza
            score = (ratio * 100) + (nivel * 0.2)

            nuevo_jugador: Dict[str, Any] = {
                "Gamertag": nombre_limpio,
                "Nivel": int(nivel),
                "K/D": float(ratio),
                "Score": round(score, 1)
            }
            st.session_state.jugadores.append(cast(Any, nuevo_jugador))
            # Persistir al backend seleccionado
            save_players_to_backend(cast(Sequence[Dict[str, Any]], st.session_state.jugadores))
            st.success(f"✅ {nombre_limpio} agregado")

    st.markdown("---")
if st.button("🗑️ Borrar Todos", type="primary"):
    st.session_state.jugadores = cast(List[Dict[str, Any]], [])
    # Persistir borrado
    save_players_to_backend(cast(Sequence[Dict[str, Any]], st.session_state.jugadores))
    st.rerun()

# Importar desde CSV
st.header("📝 Registro de Jugador")
st.markdown("### 📥 Importar jugadores")
uploaded = st.file_uploader("Subir CSV de jugadores", type=["csv"], help="CSV con columnas: Gamertag,Nivel,K/D,Score")
import_mode = st.radio("Modo de importación:", ["Reemplazar","Añadir"], index=0)
if uploaded is not None:
    try:
        df_up = pd.read_csv(uploaded)
        expected = {"Gamertag", "Nivel", "K/D", "Score"}
        if not expected.issubset(set(df_up.columns)):
            st.error(f"CSV no contiene columnas requeridas: {expected}")
        else:
            # Forzar tipos
            df_up["Nivel"] = pd.to_numeric(df_up["Nivel"], errors="coerce").fillna(0).astype(int)
            df_up["K/D"] = pd.to_numeric(df_up["K/D"], errors="coerce").fillna(0.0).astype(float)
            df_up["Score"] = pd.to_numeric(df_up["Score"], errors="coerce").fillna(0.0).astype(float)

            lista_nueva = df_up.to_dict(orient="records")
            if import_mode == "Reemplazar":
                st.session_state.jugadores = lista_nueva
            else:
                # Añadir evitando duplicados por Gamertag
                existing = {j.get('Gamertag','').casefold() for j in st.session_state.jugadores}
                for j in lista_nueva:
                    gt = str(j.get('Gamertag','')).casefold()
                    if gt and gt not in existing:
                        st.session_state.jugadores.append(cast(Dict[str, Any], j))
                        existing.add(gt)

            save_players_to_backend(cast(Sequence[Dict[str, Any]], st.session_state.jugadores))
            st.success(f"Importadas {len(lista_nueva)} filas ({import_mode}).")
    except Exception as e:
        st.error(f"Error al procesar CSV: {e}")

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
    st.markdown("---")# Lista con controles para editar/eliminar individualmente
    st.subheader("✏️ Editar / Eliminar Jugadores")
    for idx, jugador in enumerate(st.session_state.jugadores):
            titulo = f"{jugador.get('Gamertag','(sin nombre)')} — Nvl {jugador.get('Nivel',0)} | KD {jugador.get('K/D',0.0)}"
            with st.expander(titulo, expanded=False):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    nuevo_nombre = st.text_input("Gamertag", value=jugador.get('Gamertag',''), key=f"name_{idx}")
                with c2:
                    nuevo_nivel = st.number_input("Nivel", min_value=0, max_value=350, value=int(jugador.get('Nivel',0)), step=10, key=f"nivel_{idx}")
                with c3:
                    nuevo_kd = st.number_input("K/D", min_value=0.0, max_value=10.0, value=float(jugador.get('K/D',0.0)), step=0.1, key=f"kd_{idx}")
                with c4:
                    btn_save = st.button("Guardar", key=f"save_{idx}")
                    btn_del = st.button("Eliminar", key=f"del_{idx}")

                if btn_del:
                    st.session_state.jugadores.pop(idx)
                    save_players_to_backend(cast(Sequence[Dict[str, Any]], st.session_state.jugadores))
                    st.success("Jugador eliminado")
                    getattr(st, "experimental_rerun", lambda: None)()

                if btn_save:
                    nombre_limpio = _sanitizar_nombre(nuevo_nombre or "")
                    # Validaciones similares a agregar
                    if not nombre_limpio:
                        st.error("⚠️ El gamertag está vacío o no es válido.")
                    elif any((j.get('Gamertag','').casefold() == nombre_limpio.casefold()) and i != idx for i, j in enumerate(st.session_state.jugadores)):
                        st.error("⚠️ Ya existe otro jugador con ese gamertag.")
                    elif not (0 <= nuevo_nivel <= 350):
                        st.error("⚠️ El nivel debe estar entre 0 y 350.")
                    elif not (0.0 <= nuevo_kd <= 10.0):
                        st.error("⚠️ El K/D debe estar entre 0.0 y 10.0.")
                    else:
                        score = (float(nuevo_kd) * 100) + (int(nuevo_nivel) * 0.2)
                        actualizado: Dict[str, Any] = {
                            'Gamertag': nombre_limpio,
                            'Nivel': int(nuevo_nivel),
                            'K/D': float(nuevo_kd),
                            'Score': round(score, 1)
                        }
                        st.session_state.jugadores[idx] = cast(Any, actualizado)
                        save_players_to_backend(cast(Sequence[Dict[str, Any]], st.session_state.jugadores))
                        st.success("Cambios guardados")
                        getattr(st, "experimental_rerun", lambda: None)()
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
        # --- ALGORITMO: greedy + swaps (mejora de balance) ---
        equipos, reservas = balancear_equipos_greedy_swaps(cast(Sequence[Dict[str, Any]], st.session_state.jugadores), n_jugadores, max_iters=2000)
        num_equipos = len(equipos)
        if num_equipos == 0:
            st.error("No se pudo determinar el número de equipos. Revisa la configuración.")
            st.stop()

        # D. Mostrar Resultados
        st.success("✅ Equipos generados exitosamente")

        cols = st.columns(num_equipos)
        # Métricas globales de balance
        team_sums = [sum(j.get('Score', 0.0) for j in eq) for eq in equipos]
        mean_sum = statistics.fmean(team_sums) if team_sums else 0.0
        stdev_sum = statistics.pstdev(team_sums) if len(team_sums) > 0 else 0.0
        diff_max_min = (max(team_sums) - min(team_sums)) if team_sums else 0.0
        st.markdown(f"**Balance — Media poder:** {mean_sum:.1f} · **Desv. poblacional:** {stdev_sum:.2f} · **Max-Min:** {diff_max_min:.1f}")

        for i, col in enumerate(cols):
            equipo = equipos[i]
            promedio_score = sum(j.get('Score', 0) for j in equipo)
            # Protege división por cero al calcular K/D promedio
            if len(equipo) > 0:
                avg_kd = sum(j.get('K/D', 0.0) for j in equipo) / len(equipo)
            else:
                avg_kd = 0.0

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

        # --- Exportar / Copiar ---
        # Construir CSV de equipos
        rows = []
        for t_idx, equipo in enumerate(equipos, start=1):
            for p in equipo:
                rows.append({
                    'Team': t_idx,
                    'Gamertag': p.get('Gamertag',''),
                    'Nivel': p.get('Nivel',0),
                    'K/D': p.get('K/D',0.0),
                    'Score': p.get('Score',0.0)
                })
        # Reservas al final
        for p in reservas:
            rows.append({'Team': 'Reserva', 'Gamertag': p.get('Gamertag',''), 'Nivel': p.get('Nivel',0), 'K/D': p.get('K/D',0.0), 'Score': p.get('Score',0.0)})

        if rows:
            df_export = pd.DataFrame(rows)
            csv_bytes = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar equipos (CSV)", data=csv_bytes, file_name="equipos.csv", mime="text/csv")

            # Texto legible para copiar
            txt = []
            for t_idx, equipo in enumerate(equipos, start=1):
                txt.append(f"Equipo {t_idx}:\n")
                for p in equipo:
                    txt.append(f" - {p.get('Gamertag','')} | Nvl {p.get('Nivel',0)} | KD {p.get('K/D',0.0)}\n")
                txt.append("\n")
            if reservas:
                txt.append("Reservas:\n")
                for p in reservas:
                    txt.append(f" - {p.get('Gamertag','')}\n")

            equipos_text = ''.join(txt)

            # Componente para copiar al portapapeles
            copy_html = f"""
            <button id='copy'>Copiar equipos</button>
            <textarea id='t' style='display:none'>{equipos_text}</textarea>
            <script>
            const btn = document.getElementById('copy');
            btn.onclick = () => {{ navigator.clipboard.writeText(document.getElementById('t').value).then(()=>{{alert('Copiado al portapapeles')}}).catch(()=>{{alert('Falló copiar')}}); }}
            </script>
            """
            components.html(copy_html)
