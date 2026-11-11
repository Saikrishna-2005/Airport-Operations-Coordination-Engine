import sqlite3

conn = sqlite3.connect("data/airport_operations.db")
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT *
    FROM audit_logs
    WHERE resource_id = ?
    ORDER BY rowid DESC
""", ("250e1d4a-99c0-4e0b-8040-fbfdf9721eb0",)).fetchall()

for row in rows:
    print(dict(row))

if not rows:
    print("No audit records found.")

conn.close()