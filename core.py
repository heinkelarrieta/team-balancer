import pandas as pd
import os
import tempfile
import random
import statistics
from typing import List, Dict, Any, Tuple, Sequence, cast
import streamlit as st

# --- CONSTANTES Y TIPOS ---
DB_FILE = "jugadores_db.csv"
Player = Dict[str, Any]


def _sanitizar_nombre(nombre: str | None) -> str:
    """Normaliza un gamertag recibido desde la UI.

    - Elimina espacios al inicio/fin
    - Colapsa múltiples espacios intermedios
    - Limita la longitud a 48 caracteres
    """
    if not isinstance(nombre, str):
        return ""
    s = " ".join(nombre.strip().split())
    return s[:48]


def _jugador_existe(lista: Sequence[Player], gamertag: str) -> bool:
    """Comprueba si un `gamertag` ya existe en la lista (case-insensitive)."""
    if not gamertag:
        return False
    gt = gamertag.casefold()
    return any(str(j.get("Gamertag", "")).casefold() == gt for j in lista)


def cargar_datos() -> List[Player]:
    """Carga la lista de jugadores desde `DB_FILE`.

    - Maneja errores de lectura y avisos mediante Streamlit.
    - Valida que el CSV contenga las columnas esperadas.
    - Normaliza tipos para `Nivel`, `K/D` y `Score` cuando sea posible.
    """
    if not os.path.exists(DB_FILE):
        return []

    try:
        df = pd.read_csv(DB_FILE)
    except Exception as e:
        st.warning(f"No se pudo leer {DB_FILE}: {e}")
        return []

    expected = {"Gamertag", "Nivel", "K/D", "Score"}
    if not expected.issubset(set(df.columns)):
        st.warning(f"Archivo {DB_FILE} no contiene las columnas esperadas: {expected}")
        return []

    try:
        df["Nivel"] = pd.to_numeric(df["Nivel"], errors="coerce").fillna(0).astype(int)
        df["K/D"] = pd.to_numeric(df["K/D"], errors="coerce").fillna(0.0).astype(float)
        df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0.0).astype(float)
    except Exception:
        pass

    return cast(List[Player], df.to_dict(orient="records"))


def guardar_datos(lista_jugadores: List[Player]) -> None:
    """Guarda la lista de jugadores en `DB_FILE` de forma atómica.

    - Escribe en un archivo temporal y lo reemplaza para evitar corrupciones.
    - Si ocurre un error, muestra un aviso en Streamlit.
    """
    try:
        df = pd.DataFrame(lista_jugadores)
        dirpath = os.path.dirname(DB_FILE) or "."
        os.makedirs(dirpath, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=dirpath, newline="", suffix=".csv") as tmp:
            tmp_path = tmp.name
            df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, DB_FILE)
    except Exception as e:
        st.warning(f"No se pudo guardar {DB_FILE}: {e}")


def balancear_equipos_greedy_swaps(lista_jugadores: Sequence[Player], n_jugadores: int, max_iters: int = 2000) -> Tuple[List[List[Player]], List[Player]]:
    """Genera equipos mediante:

    1) Greedy inicial: repartir jugadores por score intentando mantener sumas equilibradas.
    2) Refinamiento: swaps aleatorios entre equipos que reduzcan la varianza de las sumas.

    Devuelve `(equipos, reservas)`.
    """
    total_jugadores = len(lista_jugadores)
    num_equipos = total_jugadores // n_jugadores
    if num_equipos <= 0:
        return [], list(lista_jugadores)

    # Ordenar por Score descendente
    ordenados = sorted(lista_jugadores, key=lambda x: x.get("Score", 0.0), reverse=True)

    # Greedy: asignar cada jugador al equipo con menor suma actual
    equipos: List[List[Player]] = [[] for _ in range(num_equipos)]
    equipos_sums = [0.0] * num_equipos
    for p in ordenados[: num_equipos * n_jugadores]:
        candidatos = [i for i in range(num_equipos) if len(equipos[i]) < n_jugadores]
        idx = min(candidatos, key=lambda i: equipos_sums[i])
        equipos[idx].append(p)
        equipos_sums[idx] += float(p.get("Score", 0.0))

    reservas = ordenados[num_equipos * n_jugadores :]

    # Función de utilidad: varianza poblacional de las sumas
    def variance_of_sums(sums: List[float]) -> float:
        return statistics.pvariance(sums) if len(sums) > 0 else 0.0

    best_var = variance_of_sums(equipos_sums)

    # Intentar mejorar por swaps aleatorios
    for _ in range(max_iters):
        a, b = random.sample(range(num_equipos), 2)
        if not equipos[a] or not equipos[b]:
            continue
        ia = random.randrange(len(equipos[a]))
        ib = random.randrange(len(equipos[b]))
        pa = equipos[a][ia]
        pb = equipos[b][ib]

        sa = equipos_sums[a] - pa.get("Score", 0.0) + pb.get("Score", 0.0)
        sb = equipos_sums[b] - pb.get("Score", 0.0) + pa.get("Score", 0.0)
        new_sums = equipos_sums[:]
        new_sums[a] = sa
        new_sums[b] = sb
        new_var = variance_of_sums(new_sums)

        if new_var < best_var:
            equipos[a][ia], equipos[b][ib] = equipos[b][ib], equipos[a][ia]
            equipos_sums[a], equipos_sums[b] = sa, sb
            best_var = new_var

    return equipos, reservas
