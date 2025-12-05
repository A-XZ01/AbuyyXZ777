#!/usr/bin/env python3
"""Debug script untuk check tickets di database"""

import sqlite3

def main():
    db_path = "/workspaces/AbuyyXZ777/data/bot_database.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check all tickets
    print("=" * 80)
    print("ALL TICKETS IN DATABASE:")
    print("=" * 80)
    
    cursor.execute("""
        SELECT id, guild_id, user_id, channel_id, ticket_number, game_username, status, ticket_type
        FROM tickets
        ORDER BY id DESC
        LIMIT 20
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ No tickets found!")
    else:
        for row in rows:
            ticket_id, guild_id, user_id, channel_id, ticket_number, game_username, status, ticket_type = row
            print(f"\n🎫 Ticket #{ticket_number:04d} (ID: {ticket_id})")
            print(f"   Guild ID: {guild_id} (type: {type(guild_id).__name__})")
            print(f"   User ID: {user_id} (type: {type(user_id).__name__})")
            print(f"   Channel ID: {channel_id} (type: {type(channel_id).__name__})")
            print(f"   Game Username: {game_username}")
            print(f"   Status: {status}")
            print(f"   Type: {ticket_type}")
    
    # Check table schema
    print("\n" + "=" * 80)
    print("TABLE SCHEMA:")
    print("=" * 80)
    
    cursor.execute("PRAGMA table_info(tickets)")
    schema = cursor.fetchall()
    
    for col in schema:
        col_id, name, col_type, notnull, default, pk = col
        print(f"{name:20} {col_type:15} PK:{pk} NOT NULL:{notnull}")
    
    conn.close()

if __name__ == "__main__":
    main()
