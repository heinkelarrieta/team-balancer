import threading
import time
from pathlib import Path
import core_db


def worker_insert(db_path: str, gamertag: str, delay: float = 0.0):
    # Cada hilo crea su propio registro
    if delay:
        time.sleep(delay)
    core_db.guardar_datos_db([{"Gamertag": gamertag, "Nivel": 1, "K/D": 1.0, "Score": 100.0}], db_path=db_path)


def test_concurrent_inserts(tmp_path):
    db_file = str(Path(tmp_path) / "concurrent.db")
    # Inicializar la base
    core_db.init_db(db_file)

    threads = []
    n = 20
    for i in range(n):
        t = threading.Thread(target=worker_insert, args=(db_file, f"T{i}", i * 0.01))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Leer la base y verificar que todas las filas estén presentes
    rows = core_db.cargar_datos_db(db_path=db_file)
    gts = {r['Gamertag'] for r in rows}
    assert len(gts) == n
