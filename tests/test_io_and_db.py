import glob
import pandas as pd
from typing import List, Dict, Any, Hashable, cast
from core import guardar_datos, cargar_datos
import core as core_mod
import core_db


def make_players(n: int = 4) -> List[Dict[Hashable, Any]]:
    return [
        {"Gamertag": f"P{i}", "Nivel": i * 10, "K/D": 1.0 + i * 0.5, "Score": float(100 + i)}
        for i in range(n)
    ]


def test_csv_save_and_load(tmp_path):
    # usar archivo temporal
    csv_path = tmp_path / "jugadores_test.csv"
    # parchear DB_FILE
    core_mod.DB_FILE = str(csv_path)

    players = make_players(3)
    guardar_datos(cast(Any, players))

    loaded = cargar_datos()
    assert isinstance(loaded, list)
    assert len(loaded) == len(players)
    assert {p['Gamertag'] for p in loaded} == {p['Gamertag'] for p in players}


def test_csv_backup_rotation(tmp_path):
    csv_path = tmp_path / "jugadores_test2.csv"
    core_mod.DB_FILE = str(csv_path)

    players = make_players(1)
    # create initial file
    guardar_datos(cast(Any, players))
    # run multiple saves to produce backups
    for i in range(7):
        players[0]['Score'] += i
        guardar_datos(cast(Any, players))

    pattern = f"{core_mod.DB_FILE}.bak.*"
    backups = glob.glob(pattern)
    # Should keep at most 5 backups
    assert len(backups) <= 5


def test_csv_corrupt_returns_empty(tmp_path):
    csv_path = tmp_path / "jugadores_bad.csv"
    core_mod.DB_FILE = str(csv_path)
    # write corrupt content
    csv_path.write_text("this,is,not,valid\n1,2")
    loaded = cargar_datos()
    assert isinstance(loaded, list)


def test_sqlite_save_and_load(tmp_path):
    db_path = tmp_path / "jugadores_test.db"
    records = make_players(4)
    core_db.guardar_datos_db(records, db_path=str(db_path))
    loaded = core_db.cargar_datos_db(db_path=str(db_path))
    assert len(loaded) == len(records)
    assert {r['Gamertag'] for r in loaded} == {r['Gamertag'] for r in records}


def test_migration_script(tmp_path):
    csv_path = tmp_path / "migrar.csv"
    db_path = tmp_path / "migrado.db"
    df = pd.DataFrame(make_players(5))
    df.to_csv(csv_path, index=False)

    n = core_db.migrate_csv_to_sqlite(str(csv_path), str(db_path), backup=True)
    assert n == 5
    # verify DB contains rows
    loaded = core_db.cargar_datos_db(db_path=str(db_path))
    assert len(loaded) == 5
