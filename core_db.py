import sqlite3
import os
import shutil
import datetime
import glob
from typing import List, Dict, Any, Sequence, Hashable
import pandas as pd
import logging

logger = logging.getLogger("team_balancer.core_db")
try:
    MAX_BACKUPS = max(1, int(os.getenv("MAX_BACKUPS", "5")))
except Exception:
    MAX_BACKUPS = 5

DB_SQLITE = "jugadores.db"


def init_db(db_path: str = DB_SQLITE) -> None:
    """Inicializa la base de datos SQLite y crea la tabla si no existe."""
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS jugadores (
            Gamertag TEXT PRIMARY KEY,
            Nivel INTEGER NOT NULL,
            KD REAL NOT NULL,
            Score REAL NOT NULL
        )
        """
    )
    # Mejorar concurrencia mediante WAL
    try:
        c.execute("PRAGMA journal_mode=WAL;")
    except Exception as e:
        logger.exception("Error al configurar WAL: %s", e)
    conn.commit()
    conn.close()


def cargar_datos_db(db_path: str = DB_SQLITE) -> List[Dict[str, Any]]:
    """Carga todos los jugadores desde la base de datos SQLite.

    Devuelve una lista de diccionarios con las claves: `Gamertag`, `Nivel`, `K/D`, `Score`.
    """
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT Gamertag, Nivel, KD as 'K/D', Score FROM jugadores")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    # Normalizar tipos
    for r in rows:
        r['Nivel'] = int(r.get('Nivel', 0))
        r['K/D'] = float(r.get('K/D', 0.0))
        r['Score'] = float(r.get('Score', 0.0))
    return rows


def guardar_datos_db(lista_jugadores: Sequence[Dict[Hashable, Any]], db_path: str = DB_SQLITE) -> None:
    """Guarda/Actualiza la lista de jugadores en SQLite.

    Usa `REPLACE INTO` para simplificar el upsert.
    """
    init_db(db_path)
    # Backup simple del DB antes de escribir
    try:
        if os.path.exists(db_path):
            ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            backup_name = f"{db_path}.bak.{ts}"
            shutil.copy2(db_path, backup_name)
            # Mantener solo los N backups más recientes
            try:
                pattern = f"{db_path}.bak.*"
                backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
                for old in backups[MAX_BACKUPS:]:
                    try:
                        os.remove(old)
                    except Exception as e:
                        logger.debug("No se pudo borrar backup antiguo %s: %s", old, e)
            except Exception as e:
                logger.exception("Error gestionando backups: %s", e)
    except Exception as e:
        logger.exception("Error creando backup del DB: %s", e)

    # Usar transacción explícita con timeout para evitar race conditions
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        c = conn.cursor()
        # BEGIN IMMEDIATE para adquirir lock de escritura
        c.execute('BEGIN IMMEDIATE')
        for p in lista_jugadores:
            gt = str(p.get('Gamertag', '')).strip()
            if not gt:
                continue
            c.execute(
                "REPLACE INTO jugadores (Gamertag, Nivel, KD, Score) VALUES (?, ?, ?, ?)",
                (gt, int(p.get('Nivel', 0)), float(p.get('K/D', 0.0)), float(p.get('Score', 0.0)))
            )
        conn.commit()
    except Exception as e:
        logger.exception("Error guardando datos en DB: %s", e)
        raise
    finally:
        conn.close()


def migrate_csv_to_sqlite(csv_path: str = 'jugadores_db.csv', db_path: str = DB_SQLITE, backup: bool = True) -> int:
    """Migra datos desde un CSV a SQLite.

    - Valida que el CSV tenga las columnas requeridas.
    - Opcionalmente guarda una copia de seguridad del DB existente.
    - Retorna el número de filas insertadas.
    """
    if not os.path.exists(csv_path):
        return 0
    df = pd.read_csv(csv_path)
    expected = {"Gamertag", "Nivel", "K/D", "Score"}
    if not expected.issubset(set(df.columns)):
        raise ValueError(f"CSV no contiene columnas requeridas: {expected}")

    if backup and os.path.exists(db_path):
        shutil.copy2(db_path, f"{db_path}.bak")

    records = df.to_dict(orient='records')
    guardar_datos_db(records, db_path)
    return len(records)
