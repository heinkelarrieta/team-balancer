import random
import statistics
import logging
from typing import List, Dict, Any, Tuple, Sequence

logger = logging.getLogger("team_balancer.core")

# Tipo para un jugador
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


# Las funciones de I/O basadas en CSV fueron eliminadas: la persistencia ahora es SQLite.
# Mantener funciones utilitarias y el algoritmo de balanceo.


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
    # Si solo hay un equipo, no hay swaps posibles
    if num_equipos < 2:
        return equipos, reservas

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
