import sqlite3

conn = sqlite3.connect('data/bot_database.db')
cursor = conn.cursor()

guild_id = "1445079009405833299"

# Check user_stats
cursor.execute('SELECT COUNT(*) FROM user_stats WHERE guild_id = ?', (guild_id,))
user_stats_count = cursor.fetchone()[0]
print(f"user_stats count: {user_stats_count}")

# Check weekly_stats
cursor.execute('SELECT COUNT(*) FROM weekly_stats WHERE guild_id = ?', (guild_id,))
weekly_stats_count = cursor.fetchone()[0]
print(f"weekly_stats count: {weekly_stats_count}")

# Show user_stats data
print("\nuser_stats data:")
cursor.execute('SELECT user_id, deals_completed, total_idr_value FROM user_stats WHERE guild_id = ?', (guild_id,))
for row in cursor.fetchall():
    print(f"  User {row[0]}: {row[1]} deals, Rp{row[2]:,}")

# Show weekly_stats data
print("\nweekly_stats data:")
cursor.execute('SELECT user_id, deals_count, weekly_spend FROM weekly_stats WHERE guild_id = ?', (guild_id,))
for row in cursor.fetchall():
    print(f"  User {row[0]}: {row[1]} deals, Rp{row[2]:,}")

conn.close()
