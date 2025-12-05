"""
Script untuk cek data di database (SQLite lokal vs opsional PostgreSQL)
"""
import os
import sys

# Set environment variable untuk test PostgreSQL (opsional)
# os.environ['DATABASE_URL'] = 'postgres://...'  # Uncomment dan isi jika mau test PostgreSQL

from db import BotDatabase

def check_database():
    """Cek isi database dan tampilkan summary"""
    
    db = BotDatabase('data/bot_database.db')
    
    print("\n" + "="*60)
    print(f"DATABASE TYPE: {'PostgreSQL' if db.use_postgres else 'SQLite'}")
    if db.use_postgres:
        print(f"DATABASE URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
    else:
        print(f"DATABASE PATH: {db.db_path}")
    print("="*60)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Cek semua tabel
    tables = [
        'user_stats',
        'guild_config', 
        'transactions',
        'tickets',
        'weekly_stats',
        'leaderboard_msg',
        'audit_log',
        'achievements'
    ]
    
    print("\n📊 DATABASE SUMMARY:\n")
    
    for table in tables:
        try:
            if db.use_postgres:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            else:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            
            result = cursor.fetchone()
            count = dict(result)['count'] if db.use_postgres else result['count']
            
            print(f"  📌 {table:20s} : {count:5d} rows")
            
        except Exception as e:
            print(f"  ❌ {table:20s} : ERROR - {str(e)[:40]}")
    
    # Detail transactions (most important)
    print("\n" + "="*60)
    print("🔍 DETAIL TRANSACTIONS (Last 5):")
    print("="*60)
    
    try:
        query = """
            SELECT user_id, amount, timestamp 
            FROM transactions 
            ORDER BY timestamp DESC 
            LIMIT 5
        """
        if db.use_postgres:
            query = query.replace('?', '%s')
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                r = dict(row) if db.use_postgres else dict(row)
                print(f"  User: {r['user_id']:20s} | Amount: Rp{r['amount']:>10,} | Time: {r['timestamp']}")
        else:
            print("  ⚠️  No transactions found!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Detail tickets
    print("\n" + "="*60)
    print("🎫 DETAIL TICKETS:")
    print("="*60)
    
    try:
        query = """
            SELECT user_id, status, ticket_type, created_at 
            FROM tickets 
            ORDER BY created_at DESC 
            LIMIT 5
        """
        if db.use_postgres:
            query = query.replace('?', '%s')
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                r = dict(row) if db.use_postgres else dict(row)
                print(f"  User: {r['user_id']:20s} | Status: {r['status']:10s} | Type: {r['ticket_type']:10s}")
        else:
            print("  ⚠️  No tickets found!")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ Database check complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    check_database()
