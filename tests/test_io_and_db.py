import pandas as pd
from typing import List, Dict, Any, Hashable
import core_db


def make_players(n: int = 4) -> List[Dict[Hashable, Any]]:
    return [
        {"Gamertag": f"P{i}", "Nivel": i * 10, "K/D": 1.0 + i * 0.5, "Score": float(100 + i)}
        for i in range(n)
    ]


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
