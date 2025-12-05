#!/usr/bin/env python3
"""Test script untuk simulate create ticket dan query"""

import sqlite3
from datetime import datetime

def main():
    db_path = "/workspaces/AbuyyXZ777/data/bot_database.db"
    
    # Simulate parameters
    guild_id = 1445079009405833299
    user_id = 730091485474717718  # Abuyy's ID
    channel_id = 999999999999999999  # Fake channel ID untuk test
    game_username = "TestUser"
    
    print(f"Testing query dengan:")
    print(f"  Guild ID: {guild_id}")
    print(f"  User ID: {user_id}")
    print(f"  Channel ID: {channel_id}")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Simulate save
    print("1️⃣  Simulating SAVE...")
    
    cursor.execute("""
        SELECT MAX(ticket_number) FROM tickets WHERE guild_id = ?
    """, (str(guild_id),))
    result = cursor.fetchone()
    next_number = (result[0] or 0) + 1
    
    print(f"   Next ticket number: {next_number}")
    
    cursor.execute("""
        INSERT INTO tickets (
            guild_id, user_id, channel_id, ticket_number, game_username, status,
            ticket_type
        )
        VALUES (?, ?, ?, ?, ?, 'open', 'purchase')
    """, (str(guild_id), str(user_id), str(channel_id), next_number, game_username))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    
    print(f"   Ticket saved with ID: {ticket_id}")
    print()
    
    # Simulate query
    print("2️⃣  Simulating QUERY with get_ticket_by_channel()...")
    print(f"   Looking for: channel_id = {channel_id}")
    print(f"   As string: channel_id = '{str(channel_id)}'")
    print()
    
    # Try with int
    cursor.execute("""
        SELECT id, guild_id, user_id, channel_id, ticket_number
        FROM tickets
        WHERE channel_id = ?
    """, (str(channel_id),))
    
    row = cursor.fetchone()
    
    if row:
        print("✅ FOUND!")
        print(f"   Ticket ID: {row[0]}")
        print(f"   Guild ID: {row[1]}")
        print(f"   User ID: {row[2]}")
        print(f"   Channel ID: {row[3]}")
        print(f"   Ticket Number: {row[4]}")
    else:
        print("❌ NOT FOUND!")
        print()
        print("Checking all tickets to see what's stored:")
        cursor.execute("SELECT id, channel_id FROM tickets WHERE status='open' ORDER BY id DESC LIMIT 5")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Channel ID: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    main()
