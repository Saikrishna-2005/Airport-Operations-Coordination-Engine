"""Offline aircraft metadata candidates; never proof of current flight identity."""
from __future__ import annotations

import argparse
import csv
import sqlite3
import tempfile
from pathlib import Path

from .aircraft_identity import normalize_icao24, normalize_registration

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
CSV_PATH = DATA_DIR / 'aircraftDatabase.csv'
DB_PATH = DATA_DIR / 'aircraft_registry.db'
COLUMNS = {
    'icao24': 'icao24', 'registration': 'registration',
    'manufacturerName': 'manufacturer', 'model': 'model',
    'typecode': 'typecode', 'operator': 'operator',
    'operatorIata': 'operator_iata', 'operatorIcao': 'operator_icao',
    'country': 'country', 'timestamp': 'metadata_timestamp',
}


def build_registry(csv_path=CSV_PATH, db_path=DB_PATH):
    """Build atomically, preserving conflicting registration mappings."""
    csv_path, db_path = Path(csv_path), Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=db_path.parent, suffix='.db', delete=False) as tmp:
        temp_path = Path(tmp.name)
    accepted = skipped = 0
    try:
        with csv_path.open(encoding='utf-8-sig', newline='') as stream:
            header = stream.readline()
            stream.seek(0)
            quote = "'" if header.lstrip().startswith("'") else '"'
            reader = csv.DictReader(stream, quotechar=quote, strict=True)
            if not set(COLUMNS).issubset(reader.fieldnames or []):
                raise ValueError('Required CSV columns are missing.')
            with sqlite3.connect(temp_path) as conn:
                conn.execute('CREATE TABLE aircraft (' + ', '.join(f'{c} TEXT' for c in COLUMNS.values()) + ')')
                def rows():
                    nonlocal accepted, skipped
                    for row in reader:
                        if None in row or any(v is None for v in row.values()):
                            raise ValueError(f'Malformed CSV row near line {reader.line_num}')
                        icao = normalize_icao24(row['icao24'])
                        reg = normalize_registration(row['registration'])
                        if not icao or not reg:
                            skipped += 1
                            continue
                        accepted += 1
                        yield (icao, reg, *((row[k].strip() or None) for k in list(COLUMNS)[2:]))
                conn.executemany('INSERT INTO aircraft VALUES (?,?,?,?,?,?,?,?,?,?)', rows())
                if not accepted:
                    raise ValueError('No valid aircraft mappings found.')
                conn.execute('CREATE INDEX idx_registration ON aircraft(registration)')
                conn.execute('CREATE INDEX idx_icao24 ON aircraft(icao24)')
            conn.close()
        temp_path.replace(db_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return {'accepted_rows': accepted, 'skipped_rows': skipped, 'database': str(db_path)}


def lookup_registration(registration, db_path=DB_PATH):
    """Return all distinct candidate addresses; empty and ambiguous are explicit."""
    reg = normalize_registration(registration)
    if not reg:
        return {'registration': reg, 'status': 'invalid', 'candidates': []}
    path = Path(db_path).resolve()
    if not path.is_file():
        return {'registration': reg, 'status': 'unavailable', 'candidates': []}
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as conn:
        addresses = [r[0] for r in conn.execute('SELECT DISTINCT icao24 FROM aircraft WHERE registration=? ORDER BY icao24', (reg,))]
    conn.close()
    return {'registration': reg, 'status': 'candidate' if len(addresses) == 1 else 'ambiguous' if addresses else 'not_found', 'candidates': addresses}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--registration')
    args = parser.parse_args()
    if not args.build and not args.registration:
        parser.error('Specify --build or --registration')
    if args.build:
        print(build_registry())
    if args.registration:
        print(lookup_registration(args.registration))
