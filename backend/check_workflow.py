import sqlite3

conn = sqlite3.connect("data/airport_operations.db")
conn.row_factory = sqlite3.Row

print("WORKFLOWS TABLE STRUCTURE:")
columns = conn.execute("PRAGMA table_info(workflows)").fetchall()

for column in columns:
    print(dict(column))

print("\nSEARCHING FOR WORKFLOW:")

rows = conn.execute(
    "SELECT * FROM workflows WHERE workflow_id = ?",
    ("6c1a2317-5910-46cc-9444-cd6091979f81",)
).fetchall()

for row in rows:
    print(dict(row))

if not rows:
    print("Workflow not found in database.")

conn.close()