import sqlite3
from datetime import datetime, timedelta

def get_current_week_start():
    """Get Monday of current week"""
    today = datetime.now()
    days_since_monday = today.weekday()  # 0 = Monday, 6 = Sunday
    monday = today - timedelta(days=days_since_monday)
    return monday.strftime('%Y-%m-%d')

conn = sqlite3.connect('data/bot_database.db')
cursor = conn.cursor()

# Get current week start
week_start = get_current_week_start()
print(f"Current week starts: {week_start}")
print('='*60)

# Check all weekly_stats
cursor.execute('SELECT * FROM weekly_stats ORDER BY weekly_spend DESC')
rows = cursor.fetchall()

if not rows:
    print("❌ Tidak ada data di weekly_stats")
else:
    print(f"Total records in weekly_stats: {len(rows)}")
    print("\nAll weekly_stats data:")
    for row in rows:
        print(f"  Guild: {row[0]}, User: {row[1]}, Week: {row[2]}, Spend: {row[3]}, Deals: {row[4]}")

print('\n' + '='*60)

# Check weekly_stats for current week
cursor.execute('SELECT * FROM weekly_stats WHERE week_start = ?', (week_start,))
rows = cursor.fetchall()

if not rows:
    print(f"❌ Tidak ada data untuk minggu ini ({week_start})")
else:
    print(f"Data untuk minggu ini ({week_start}):")
    for row in rows:
        print(f"  Guild: {row[0]}, User: {row[1]}, Spend: {row[3]}, Deals: {row[4]}")

print('\n' + '='*60)

# Check recent tickets
cursor.execute('SELECT id, user_id, guild_id, status FROM tickets ORDER BY id DESC LIMIT 10')
rows = cursor.fetchall()
print("\nRecent 10 tickets:")
for row in rows:
    print(f"  Ticket ID: {row[0]}, User: {row[1]}, Guild: {row[2]}, Status: {row[3]}")

conn.close()
