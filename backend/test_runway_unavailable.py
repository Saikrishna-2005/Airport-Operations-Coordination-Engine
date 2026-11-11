import sqlite3

conn = sqlite3.connect("data/airport_operations.db")
cursor = conn.cursor()

cursor.execute("""
    UPDATE runway_status
    SET status = 'AVAILABLE',
        reason = 'Development test - runway available',
        updated_at = strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')
    WHERE airport_code = 'HYD'
    AND runway_code = '09L'
""")

conn.commit()

print("Updated rows:", cursor.rowcount)

conn.close()