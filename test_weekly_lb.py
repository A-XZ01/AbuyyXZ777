import sys
sys.path.insert(0, '.')
from db import BotDatabase

# Initialize database
db = BotDatabase('data/bot_database.db')

# Test guild ID dari screenshot
guild_id = 1445079009405833299

print(f"Testing get_weekly_leaderboard for guild {guild_id}")
print("="*60)

# Get current week start
week_start = db.get_current_week_start()
print(f"Current week start: {week_start}")

# Get weekly leaderboard
result = db.get_weekly_leaderboard(guild_id, limit=10)

print(f"\nResult: {result}")
print(f"Number of records: {len(result)}")

if result:
    print("\nWeekly Leaderboard:")
    for idx, stat in enumerate(result, 1):
        print(f"{idx}. User {stat['user_id']}: {stat['deals_count']} deals, Rp{stat['weekly_spend']:,}")
else:
    print("\n❌ No data returned!")

# Debug: Check manually with same query
import sqlite3
conn = sqlite3.connect('data/bot_database.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT user_id, weekly_spend, deals_count, guild_id, week_start
    FROM weekly_stats
    WHERE guild_id = ? AND week_start = ?
    ORDER BY weekly_spend DESC
    LIMIT 10
""", (str(guild_id), week_start))
rows = cursor.fetchall()
print(f"\n\nDirect query result: {len(rows)} rows")
for row in rows:
    print(f"  {row}")
conn.close()
