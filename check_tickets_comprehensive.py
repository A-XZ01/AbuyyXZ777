#!/usr/bin/env python3
"""
Comprehensive ticket database check
"""

import sqlite3
import sys

def main():
    db_path = "/workspaces/AbuyyXZ777/data/bot_database.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 100)
    print("TICKET DATABASE COMPREHENSIVE CHECK")
    print("=" * 100)
    
    # Check 1: Total tickets
    cursor.execute("SELECT COUNT(*) FROM tickets")
    total = cursor.fetchone()[0]
    print(f"\n📊 Total tickets in database: {total}")
    
    # Check 2: Recent tickets
    print("\n🎫 Recent 10 tickets:")
    print("-" * 100)
    cursor.execute("""
        SELECT id, ticket_number, channel_id, user_id, game_username, status, created_at
        FROM tickets
        ORDER BY id DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    for row in rows:
        ticket_id, ticket_number, channel_id, user_id, game_username, status, created_at = row
        print(f"#{ticket_number:04d} | ID:{ticket_id} | CH:{channel_id} | User:{user_id} | {game_username:15} | {status:8} | {created_at}")
    
    # Check 3: Open tickets only
    cursor.execute("""
        SELECT id, ticket_number, channel_id, user_id, game_username, created_at
        FROM tickets
        WHERE status = 'open'
        ORDER BY id DESC
    """)
    
    open_tickets = cursor.fetchall()
    print(f"\n🟢 Open tickets ({len(open_tickets)}):")
    print("-" * 100)
    
    if open_tickets:
        for row in open_tickets:
            ticket_id, ticket_number, channel_id, user_id, game_username, created_at = row
            print(f"#{ticket_number:04d} | CH_ID:{channel_id} | {game_username:15} | Created: {created_at}")
    else:
        print("❌ NO OPEN TICKETS!")
    
    # Check 4: Try to find ticket 0006
    print(f"\n🔍 Looking for ticket #0006...")
    cursor.execute("""
        SELECT id, ticket_number, channel_id, user_id, game_username, status
        FROM tickets
        WHERE ticket_number = 6
    """)
    
    row = cursor.fetchone()
    if row:
        ticket_id, ticket_number, channel_id, user_id, game_username, status = row
        print(f"✅ Found!")
        print(f"   ID: {ticket_id}")
        print(f"   Number: {ticket_number}")
        print(f"   Channel ID: {channel_id}")
        print(f"   User ID: {user_id}")
        print(f"   Username: {game_username}")
        print(f"   Status: {status}")
        
        # Try query by channel_id
        print(f"\n   Testing query by channel_id: {channel_id}")
        cursor.execute("SELECT id FROM tickets WHERE channel_id = ?", (str(channel_id),))
        result = cursor.fetchone()
        if result:
            print(f"   ✅ Query works! Found ticket ID: {result[0]}")
        else:
            print(f"   ❌ Query FAILED! Channel ID not found!")
    else:
        print(f"❌ Ticket #0006 not found in database!")
    
    conn.close()

if __name__ == "__main__":
    main()
