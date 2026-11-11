import sqlite3

conn = sqlite3.connect("data/airport_operations.db")
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT *
    FROM gate_assignments
    WHERE airport_code = 'HYD'
    ORDER BY gate_id, start_minute
""").fetchall()

for row in rows:
    print(dict(row))

conn.close()