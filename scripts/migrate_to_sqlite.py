#!/usr/bin/env python3
"""Script simple para migrar `jugadores_db.csv` a `jugadores.db` (SQLite).

Uso:
    python scripts/migrate_to_sqlite.py --csv path/to/jugadores_db.csv --db path/to/jugadores.db
"""
import argparse
from core_db import migrate_csv_to_sqlite


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', '-c', default='jugadores_db.csv', help='Ruta al CSV de origen')
    p.add_argument('--db', '-d', default='jugadores.db', help='Ruta al archivo SQLite destino')
    p.add_argument('--no-backup', dest='backup', action='store_false', help='No crear copia de seguridad del DB existente')
    args = p.parse_args()

    try:
        n = migrate_csv_to_sqlite(args.csv, args.db, backup=args.backup)
        print(f'Migradas {n} filas desde {args.csv} → {args.db}')
    except Exception as e:
        print(f'Error migrando: {e}')


if __name__ == '__main__':
    main()
