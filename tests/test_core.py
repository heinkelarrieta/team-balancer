import random
from core import balancear_equipos_greedy_swaps


def make_players(n):
    """Crear jugadores con scores crecientes para pruebas."""
    players = []
    for i in range(n):
        players.append({
            "Gamertag": f"P{i}",
            "Nivel": i % 100,
            "K/D": round(1.0 + (i * 0.1), 2),
            "Score": float(100 + i * 5),
        })
    return players


def test_empty_list():
    equipos, reservas = balancear_equipos_greedy_swaps([], 2)
    assert equipos == []
    assert reservas == []


def test_insufficient_players_creates_reserve():
    players = make_players(3)
    equipos, reservas = balancear_equipos_greedy_swaps(players, 2)
    # 3 jugadores, squads de 2 -> 1 equipo + 1 reserva
    assert len(equipos) == 1
    assert len(reservas) == 1
    # Conserva todos los jugadores
    total = sum(len(eq) for eq in equipos) + len(reservas)
    assert total == 3


def test_no_duplicates_and_team_sizes():
    players = make_players(8)
    # fijar seed para determinismo en swaps
    random.seed(0)
    equipos, reservas = balancear_equipos_greedy_swaps(players, 4, max_iters=1000)
    # Deben formarse 2 equipos completos
    assert len(equipos) == 2
    assert all(len(eq) == 4 for eq in equipos)
    # Sin duplicados entre equipos y reservas
    seen = set()
    for eq in equipos:
        for p in eq:
            gt = p['Gamertag']
            assert gt not in seen
            seen.add(gt)
    for r in reservas:
        assert r['Gamertag'] not in seen
