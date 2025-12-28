import streamlit as st
import pandas as pd
import os
import tempfile
from typing import List, Dict, Any, cast, Optional, Sequence

# --- BLOQUE DE BASE DE DATOS ---
DB_FILE = "jugadores_db.csv"


def _sanitizar_nombre(nombre: Optional[str]) -> str:
    """Normaliza el gamertag: trim, colapsa espacios y limita longitud."""
    if not isinstance(nombre, str):
        return ""
    # Trim y colapsar espacios múltiples
    s = " ".join(nombre.strip().split())
    # Limitar longitud razonable
    return s[:48]


def _jugador_existe(lista: Sequence[Dict[str, Any]], gamertag: str) -> bool:
    """Comprueba existencia por gamertag (case-insensitive)."""
    if not gamertag:
        return False
    gt = gamertag.casefold()
    return any(str(j.get("Gamertag","") ).casefold() == gt for j in lista)

def cargar_datos():
    """Carga jugadores desde `DB_FILE` con manejo de errores y validación básica.

    Retorna una lista de diccionarios con las columnas esperadas.
    En caso de error devuelve lista vacía.
    """
    if not os.path.exists(DB_FILE):
        return []

    try:
        df = pd.read_csv(DB_FILE)
    except Exception as e:
        st.warning(f"No se pudo leer {DB_FILE}: {e}")
        return []

    # Validar columnas esperadas
    expected = {"Gamertag", "Nivel", "K/D", "Score"}
    if not expected.issubset(set(df.columns)):
        st.warning(f"Archivo {DB_FILE} no contiene las columnas esperadas: {expected}")
        return []

    # Forzar tipos simples (int/float) cuando sea posible
    try:
        df["Nivel"] = pd.to_numeric(df["Nivel"], errors="coerce").fillna(0).astype(int)
        df["K/D"] = pd.to_numeric(df["K/D"], errors="coerce").fillna(0.0).astype(float)
        df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0.0).astype(float)
    except Exception:
        # Si hay problemas de conversión, continuamos devolviendo lo leído
        pass

    return df.to_dict(orient="records")

def guardar_datos(lista_jugadores):
    """Guarda la lista de jugadores en `DB_FILE` de forma atómica.

    Escribe en un archivo temporal y reemplaza el archivo objetivo para evitar corrupciones parciales.
    """
    try:
        df = pd.DataFrame(lista_jugadores)
        # Asegurar directorio
        dirpath = os.path.dirname(DB_FILE) or "."
        os.makedirs(dirpath, exist_ok=True)

        # Escritura atómica: escribir en temporal y reemplazar
        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=dirpath, newline="", suffix=".csv") as tmp:
            tmp_path = tmp.name
            df.to_csv(tmp_path, index=False)

        os.replace(tmp_path, DB_FILE)
    except Exception as e:
        st.warning(f"No se pudo guardar {DB_FILE}: {e}")

# Reemplaza tu línea de "if 'jugadores' not in st.session_state..." por esta:
if 'jugadores' not in st.session_state:
    st.session_state.jugadores = cargar_datos()

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
# Los jugadores se cargan desde disco en la inicialización superior.

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
            # Persistir al disco
            guardar_datos(st.session_state.jugadores)
            st.success(f"✅ {nombre_limpio} agregado")

    st.markdown("---")
    if st.button("🗑️ Borrar Todos", type="primary"):
        st.session_state.jugadores = cast(List[Dict[str, Any]], [])
        # Persistir borrado
        guardar_datos(st.session_state.jugadores)
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
                    guardar_datos(st.session_state.jugadores)
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
                        guardar_datos(st.session_state.jugadores)
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
        # --- ALGORITMO SNAKE ---
        # A. Ordenar por Score
        lista_ordenada = sorted(st.session_state.jugadores, key=lambda x: x['Score'], reverse=True)
        
        # B. Crear contenedores
        num_equipos = total_jugadores // n_jugadores
        if num_equipos <= 0:
            st.error("No se pudo determinar el número de equipos. Revisa la configuración.")
            st.stop()

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