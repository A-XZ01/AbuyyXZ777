#!/usr/bin/env python3
"""Test query untuk ticket #0004 yang sudah ada"""

import sqlite3

def main():
    db_path = "/workspaces/AbuyyXZ777/data/bot_database.db"
    
    # Dari database, ticket #0004 punya channel_id: 1446473844708872263
    channel_id = 1446473844708872263
    
    print(f"Testing query untuk channel_id: {channel_id}")
    print(f"As string: '{str(channel_id)}'")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query seperti yang dilakukan oleh get_ticket_by_channel()
    cursor.execute("""
        SELECT id, guild_id, user_id, ticket_number, game_username, status
        FROM tickets
        WHERE channel_id = ?
    """, (str(channel_id),))
    
    row = cursor.fetchone()
    
    if row:
        print("✅ FOUND!")
        print(f"   Ticket ID: {row[0]}")
        print(f"   Guild ID: {row[1]}")
        print(f"   User ID: {row[2]}")
        print(f"   Ticket #: {row[3]}")
        print(f"   Username: {row[4]}")
        print(f"   Status: {row[5]}")
    else:
        print("❌ NOT FOUND!")
        print()
        print("Checking with different approaches:")
        
        # Try as string without conversion
        cursor.execute("""
            SELECT id, channel_id FROM tickets
            WHERE channel_id = '1446473844708872263'
        """)
        print(f"  Direct string match: {cursor.fetchone()}")
        
        # Try as int
        cursor.execute("""
            SELECT id, channel_id FROM tickets
            WHERE CAST(channel_id AS INTEGER) = 1446473844708872263
        """)
        print(f"  Cast to INT match: {cursor.fetchone()}")
        
        # Show all channel_ids
        print("\n  All channel IDs in database:")
        cursor.execute("SELECT channel_id FROM tickets LIMIT 5")
        for row in cursor.fetchall():
            print(f"    {row[0]} (type: {type(row[0]).__name__})")
    
    conn.close()

if __name__ == "__main__":
    main()
