"""
Database module untuk Discord Bot - SQLite persistence
Mengelola user stats, guild config, dan backup/restore
"""
import sqlite3
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime


class BotDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Buat koneksi baru ke database dengan timeout"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode untuk better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def init_db(self):
        """Inisialisasi tabel database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabel user_stats: menyimpan statistik per user per guild
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                deals_completed INTEGER DEFAULT 0,
                total_idr_value INTEGER DEFAULT 0,
                stats_message_id TEXT,
                stats_channel_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        # Tabel guild_config: konfigurasi per server
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT PRIMARY KEY,
                auto_detect_channels TEXT,
                admin_roles TEXT,
                currency TEXT DEFAULT 'IDR',
                auto_detect_regex TEXT,
                leaderboard_message_id TEXT,
                leaderboard_channel_id TEXT,
                ticket_setup_message_id TEXT,
                ticket_setup_channel_id TEXT,
                price_hash TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabel audit_log: log aktivitas penting
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                user_id TEXT,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabel transactions: detail setiap transaksi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                category TEXT,
                notes TEXT,
                recorded_by TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabel achievements: milestone yang dicapai user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_value INTEGER,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, user_id, achievement_type, achievement_value)
            )
        """)
        
        # Tabel tickets: tracking ticket channels untuk buyer
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                ticket_number INTEGER NOT NULL,
                game_username TEXT,
                status TEXT DEFAULT 'open',
                proof_url TEXT,
                approved_by TEXT,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                closed_by TEXT,
                UNIQUE(guild_id, user_id, status)
            )
        """)
        
        # Tabel ticket_items: items yang dipesan dalam ticket
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id)
            )
        """)
        
        # Tabel weekly_stats: tracking spending per minggu untuk leaderboard
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_stats (
                guild_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                week_start TEXT NOT NULL,
                weekly_spend INTEGER DEFAULT 0,
                deals_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, week_start)
            )
        """)
        
        # Tabel item_prices: harga items yang bisa diubah dari Discord
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS item_prices (
                guild_id TEXT NOT NULL,
                item_code TEXT NOT NULL,
                item_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, item_code)
            )
        """)
        
        # ALTER TABLE untuk tambah kolom leaderboard (jika belum ada)
        try:
            cursor.execute("ALTER TABLE guild_config ADD COLUMN leaderboard_message_id TEXT")
            cursor.execute("ALTER TABLE guild_config ADD COLUMN leaderboard_channel_id TEXT")
            print("✅ Kolom leaderboard berhasil ditambahkan ke guild_config")
        except sqlite3.OperationalError as e:
            # Kolom sudah ada, skip
            if "duplicate column name" not in str(e).lower():
                print(f"⚠️ ALTER TABLE warning: {e}")
        
        # ALTER TABLE untuk tambah kolom personal stats message tracking
        try:
            cursor.execute("ALTER TABLE user_stats ADD COLUMN stats_message_id TEXT")
            cursor.execute("ALTER TABLE user_stats ADD COLUMN stats_channel_id TEXT")
            print("✅ Kolom stats message tracking berhasil ditambahkan ke user_stats")
        except sqlite3.OperationalError as e:
            # Kolom sudah ada, skip
            if "duplicate column name" not in str(e).lower():
                print(f"⚠️ ALTER TABLE warning: {e}")
        
        # ALTER TABLE untuk tambah kolom fraud prevention tracking
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN proof_url TEXT")
            cursor.execute("ALTER TABLE tickets ADD COLUMN approved_by TEXT")
            cursor.execute("ALTER TABLE tickets ADD COLUMN approved_at TIMESTAMP")
            print("✅ Kolom fraud prevention tracking berhasil ditambahkan ke tickets")
        except sqlite3.OperationalError as e:
            # Kolom sudah ada, skip
            if "duplicate column name" not in str(e).lower():
                print(f"⚠️ ALTER TABLE warning: {e}")
        
        # ALTER TABLE untuk tambah kolom duplicate image detection
        try:
            cursor.execute("ALTER TABLE tickets ADD COLUMN proof_hash TEXT")
            print("✅ Kolom proof_hash berhasil ditambahkan ke tickets")
        except sqlite3.OperationalError as e:
            # Kolom sudah ada, skip
            if "duplicate column name" not in str(e).lower():
                print(f"⚠️ ALTER TABLE warning: {e}")
        
        # ALTER TABLE untuk tambah kolom ticket setup tracking
        try:
            cursor.execute("ALTER TABLE guild_config ADD COLUMN ticket_setup_message_id TEXT")
            cursor.execute("ALTER TABLE guild_config ADD COLUMN ticket_setup_channel_id TEXT")
            cursor.execute("ALTER TABLE guild_config ADD COLUMN price_hash TEXT")
            print("✅ Kolom ticket setup tracking berhasil ditambahkan ke guild_config")
        except sqlite3.OperationalError as e:
            # Kolom sudah ada, skip
            if "duplicate column name" not in str(e).lower():
                print(f"⚠️ ALTER TABLE warning: {e}")
        
        conn.commit()
        conn.close()
    
    # === User Stats Methods ===
    
    def get_user_stats(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Ambil statistik user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_stats WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'deals_completed': row['deals_completed'],
                'total_idr_value': row['total_idr_value'],
                'updated_at': row['updated_at']
            }
        return None
    
    def update_user_stats(self, guild_id: int, user_id: int, amount: int) -> Dict[str, Any]:
        """Update stats user: +1 deal, +amount IDR"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Upsert
        cursor.execute("""
            INSERT INTO user_stats (guild_id, user_id, deals_completed, total_idr_value, updated_at)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                deals_completed = deals_completed + 1,
                total_idr_value = total_idr_value + ?,
                updated_at = CURRENT_TIMESTAMP
        """, (str(guild_id), str(user_id), amount, amount))
        
        conn.commit()
        conn.close()
        
        # Update weekly stats juga
        self.update_weekly_stats(guild_id, user_id, amount)
        
        # Ambil hasil terbaru
        stats = self.get_user_stats(guild_id, user_id)
        return stats
    
    def add_transaction(self, guild_id: int, user_id: int, amount: int, category: str = None, notes: str = None, recorded_by: int = None) -> int:
        """Tambahkan transaksi baru ke history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (guild_id, user_id, amount, category, notes, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(guild_id), str(user_id), amount, category, notes, str(recorded_by) if recorded_by else None))
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return transaction_id
    
    def get_user_transactions(self, guild_id: int, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Ambil history transaksi user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, amount, category, notes, recorded_by, timestamp
            FROM transactions
            WHERE guild_id = ? AND user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (str(guild_id), str(user_id), limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row['id'],
                'amount': row['amount'],
                'category': row['category'],
                'notes': row['notes'],
                'recorded_by': row['recorded_by'],
                'timestamp': row['timestamp']
            }
            for row in rows
        ]
    
    def check_and_unlock_achievement(self, guild_id: int, user_id: int) -> List[str]:
        """Cek dan unlock achievement baru berdasarkan stats. Return list achievement baru."""
        stats = self.get_user_stats(guild_id, user_id)
        if not stats:
            return []
        
        deals = stats['deals_completed']
        total_value = stats['total_idr_value']
        
        # Define milestones
        milestones = [
            ('deals_10', 10, deals >= 10),
            ('deals_50', 50, deals >= 50),
            ('deals_100', 100, deals >= 100),
            ('deals_500', 500, deals >= 500),
            ('value_1m', 1000000, total_value >= 1000000),
            ('value_5m', 5000000, total_value >= 5000000),
            ('value_10m', 10000000, total_value >= 10000000),
            ('value_50m', 50000000, total_value >= 50000000),
        ]
        
        conn = self.get_connection()
        cursor = conn.cursor()
        new_achievements = []
        
        for achievement_type, value, condition in milestones:
            if condition:
                try:
                    cursor.execute("""
                        INSERT INTO achievements (guild_id, user_id, achievement_type, achievement_value)
                        VALUES (?, ?, ?, ?)
                    """, (str(guild_id), str(user_id), achievement_type, value))
                    conn.commit()
                    new_achievements.append(achievement_type)
                except Exception:
                    # Already unlocked
                    pass
        
        conn.close()
        return new_achievements
    
    def get_user_achievements(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Dapatkan semua achievement yang sudah unlocked oleh user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT achievement_type, achievement_value, unlocked_at
            FROM achievements
            WHERE guild_id = ? AND user_id = ?
            ORDER BY unlocked_at DESC
        """, (str(guild_id), str(user_id)))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'achievement_type': row['achievement_type'],
                'achievement_value': row['achievement_value'],
                'unlocked_at': row['unlocked_at']
            }
            for row in rows
        ]
    
    def reset_user_stats(self, guild_id: int, user_id: int):
        """Reset stats user ke 0"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_stats 
            SET deals_completed = 0, total_idr_value = 0, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ?
        """, (str(guild_id), str(user_id)))
        conn.commit()
        conn.close()
    
    def reset_all_stats(self, guild_id: int):
        """Reset semua stats di guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_stats WHERE guild_id = ?", (str(guild_id),))
        conn.commit()
        conn.close()
    
    def get_all_user_stats(self, guild_id: int) -> List[Dict[str, Any]]:
        """Ambil semua user stats di guild, sorted by IDR value desc"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, deals_completed, total_idr_value 
            FROM user_stats 
            WHERE guild_id = ?
            ORDER BY total_idr_value DESC
        """, (str(guild_id),))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'user_id': row['user_id'],
                'deals_completed': row['deals_completed'],
                'total_idr_value': row['total_idr_value']
            }
            for row in rows
        ]
    
    # === Weekly Leaderboard Methods ===
    
    def get_current_week_start(self) -> str:
        """Get ISO week start date (Monday) untuk minggu ini"""
        from datetime import datetime, timedelta
        today = datetime.now()
        # Monday = 0, Sunday = 6
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        return monday.strftime('%Y-%m-%d')
    
    def update_weekly_stats(self, guild_id: int, user_id: int, amount: int):
        """Update weekly spending untuk user"""
        week_start = self.get_current_week_start()
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO weekly_stats (guild_id, user_id, week_start, weekly_spend, deals_count, updated_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, user_id, week_start) DO UPDATE SET
                weekly_spend = weekly_spend + ?,
                deals_count = deals_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (str(guild_id), str(user_id), week_start, amount, amount))
        
        conn.commit()
        conn.close()
    
    def get_weekly_leaderboard(self, guild_id: int, limit: int = None) -> List[Dict[str, Any]]:
        """Ambil leaderboard berdasarkan spending minggu ini"""
        week_start = self.get_current_week_start()
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Query dengan optional LIMIT
        query = """
            SELECT user_id, weekly_spend, deals_count
            FROM weekly_stats
            WHERE guild_id = ? AND week_start = ?
            ORDER BY weekly_spend DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (str(guild_id), week_start))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'user_id': row['user_id'],
                'weekly_spend': row['weekly_spend'],
                'deals_count': row['deals_count']
            }
            for row in rows
        ]
    
    def get_last_reset_date(self, guild_id: int) -> Optional[str]:
        """Get tanggal reset terakhir untuk guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(week_start) as last_week
            FROM weekly_stats
            WHERE guild_id = ?
        """, (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        
        return row['last_week'] if row and row['last_week'] else None
    
    # === Guild Config Methods ===
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Ambil konfigurasi guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM guild_config WHERE guild_id = ?", (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'auto_detect_channels': json.loads(row['auto_detect_channels']) if row['auto_detect_channels'] else [],
                'admin_roles': json.loads(row['admin_roles']) if row['admin_roles'] else [],
                'currency': row['currency'] or 'IDR',
                'auto_detect_regex': row['auto_detect_regex'] or r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)"
            }
        
        # Default config
        return {
            'auto_detect_channels': [],
            'admin_roles': [],
            'currency': 'IDR',
            'auto_detect_regex': r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)"
        }
    
    def set_guild_config(self, guild_id: int, config: Dict[str, Any]):
        """Set konfigurasi guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO guild_config (guild_id, auto_detect_channels, admin_roles, currency, auto_detect_regex, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id) DO UPDATE SET
                auto_detect_channels = ?,
                admin_roles = ?,
                currency = ?,
                auto_detect_regex = ?,
                updated_at = CURRENT_TIMESTAMP
        """, (
            str(guild_id),
            json.dumps(config.get('auto_detect_channels', [])),
            json.dumps(config.get('admin_roles', [])),
            config.get('currency', 'IDR'),
            config.get('auto_detect_regex', r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)"),
            json.dumps(config.get('auto_detect_channels', [])),
            json.dumps(config.get('admin_roles', [])),
            config.get('currency', 'IDR'),
            config.get('auto_detect_regex', r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)")
        ))
        
        conn.commit()
        conn.close()
    
    def set_guild_config(self, guild_id: int, key: str, value: Any):
        """Update satu field di guild config"""
        current_config = self.get_guild_config(guild_id)
        current_config[key] = value
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO guild_config (guild_id, auto_detect_channels, admin_roles, currency, auto_detect_regex, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id) DO UPDATE SET
                auto_detect_channels = ?,
                admin_roles = ?,
                currency = ?,
                auto_detect_regex = ?,
                updated_at = CURRENT_TIMESTAMP
        """, (
            str(guild_id),
            json.dumps(current_config.get('auto_detect_channels', [])),
            json.dumps(current_config.get('admin_roles', [])),
            current_config.get('currency', 'IDR'),
            current_config.get('auto_detect_regex', r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)"),
            json.dumps(current_config.get('auto_detect_channels', [])),
            json.dumps(current_config.get('admin_roles', [])),
            current_config.get('currency', 'IDR'),
            current_config.get('auto_detect_regex', r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)")
        ))
        
        conn.commit()
        conn.close()
    
    # === Audit Log ===
    
    def log_action(self, guild_id: int, user_id: int, action: str, details: str = ""):
        """Catat aksi penting ke audit log"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (guild_id, user_id, action, details)
            VALUES (?, ?, ?, ?)
        """, (str(guild_id), str(user_id), action, details))
        conn.commit()
        conn.close()
    
    # === Ticket Management ===
    
    def create_ticket(self, guild_id: int, user_id: int, channel_id: int, game_username: str = None) -> int:
        """Buat ticket baru, return ticket_id"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get next ticket number untuk guild ini
            cursor.execute("""
                SELECT MAX(ticket_number) FROM tickets WHERE guild_id = ?
            """, (str(guild_id),))
            result = cursor.fetchone()
            next_number = (result[0] or 0) + 1
            
            cursor.execute("""
                INSERT INTO tickets (guild_id, user_id, channel_id, ticket_number, game_username, status)
                VALUES (?, ?, ?, ?, ?, 'open')
            """, (str(guild_id), str(user_id), str(channel_id), next_number, game_username))
            
            ticket_id = cursor.lastrowid
            conn.commit()
            return ticket_id
        except Exception as e:
            print(f"❌ Database error in create_ticket: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def get_open_ticket(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Cek apakah user punya ticket yang masih open"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, channel_id, ticket_number, game_username, created_at
            FROM tickets
            WHERE guild_id = ? AND user_id = ? AND status = 'open'
        """, (str(guild_id), str(user_id)))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'channel_id': row[1],
            'ticket_number': row[2],
            'game_username': row[3],
            'created_at': row[4]
        }
    
    def get_ticket_by_channel(self, channel_id: int) -> Optional[Dict]:
        """Ambil ticket info by channel_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, guild_id, user_id, ticket_number, game_username, status, created_at
            FROM tickets
            WHERE channel_id = ?
        """, (str(channel_id),))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'guild_id': row[1],
            'user_id': row[2],
            'ticket_number': row[3],
            'game_username': row[4],
            'status': row[5],
            'created_at': row[6]
        }
    
    def add_item_to_ticket(self, ticket_id: int, item_name: str, amount: int):
        """Tambah item ke ticket"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticket_items (ticket_id, item_name, amount)
            VALUES (?, ?, ?)
        """, (ticket_id, item_name, amount))
        conn.commit()
        conn.close()
    
    def get_ticket_items(self, ticket_id: int) -> List[Dict]:
        """Ambil semua items dalam ticket"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, item_name, amount, added_at
            FROM ticket_items
            WHERE ticket_id = ?
            ORDER BY added_at ASC
        """, (ticket_id,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'item_name': row[1],
                'amount': row[2],
                'added_at': row[3]
            })
        
        conn.close()
        return items
    
    def close_ticket(self, ticket_id: int, closed_by: int, approved_by: int = None):
        """Close ticket with approval tracking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get ticket info first
            cursor.execute("SELECT guild_id, user_id FROM tickets WHERE id = ?", (ticket_id,))
            ticket_info = cursor.fetchone()
            
            if ticket_info:
                guild_id, user_id = ticket_info
                
                # Delete old closed tickets for this user (keep only the latest one we're closing)
                cursor.execute("""
                    DELETE FROM tickets
                    WHERE guild_id = ? AND user_id = ? AND status = 'closed'
                """, (guild_id, user_id))
            
            # Now close the current ticket with approval info
            cursor.execute("""
                UPDATE tickets
                SET status = 'closed', 
                    closed_at = CURRENT_TIMESTAMP, 
                    closed_by = ?,
                    approved_by = ?,
                    approved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (str(closed_by), str(approved_by) if approved_by else None, ticket_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ Error closing ticket: {e}")
            raise
        finally:
            conn.close()
    
    def update_ticket_proof(self, ticket_id: int, proof_url: str):
        """Save proof URL to ticket for audit trail"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE tickets
                SET proof_url = ?
                WHERE id = ?
            """, (proof_url, ticket_id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ Error updating proof: {e}")
            raise
        finally:
            conn.close()
    
    def get_all_open_tickets(self, guild_id: int) -> List[Dict]:
        """Ambil semua open tickets di guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, channel_id, ticket_number, game_username, created_at
            FROM tickets
            WHERE guild_id = ? AND status = 'open'
            ORDER BY created_at DESC
        """, (str(guild_id),))
        
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                'id': row[0],
                'user_id': row[1],
                'channel_id': row[2],
                'ticket_number': row[3],
                'game_username': row[4],
                'created_at': row[5]
            })
        
        conn.close()
        return tickets
    
    def get_all_tickets(self, guild_id: int) -> List[Dict]:
        """Ambil semua tickets (open + closed) di guild dengan total amount"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.user_id, t.channel_id, t.ticket_number, t.game_username, 
                   t.status, t.created_at, t.closed_at,
                   COALESCE(SUM(ti.amount), 0) as total_amount
            FROM tickets t
            LEFT JOIN ticket_items ti ON t.id = ti.ticket_id
            WHERE t.guild_id = ?
            GROUP BY t.id
            ORDER BY t.created_at DESC
        """, (str(guild_id),))
        
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                'id': row[0],
                'user_id': row[1],
                'channel_id': row[2],
                'ticket_number': row[3],
                'game_username': row[4],
                'status': row[5],
                'created_at': row[6],
                'closed_at': row[7],
                'total_amount': row[8]
            })
        
        conn.close()
        return tickets
    
    # === Leaderboard Message Tracking ===
    
    def set_leaderboard_message(self, guild_id: int, channel_id: int, message_id: int):
        """Simpan message ID dari leaderboard yang akan di-update"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO guild_config (guild_id, leaderboard_channel_id, leaderboard_message_id, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id) DO UPDATE SET
                leaderboard_channel_id = excluded.leaderboard_channel_id,
                leaderboard_message_id = excluded.leaderboard_message_id,
                updated_at = CURRENT_TIMESTAMP
        """, (str(guild_id), str(channel_id), str(message_id)))
        conn.commit()
        conn.close()
    
    def get_leaderboard_message(self, guild_id: int) -> Optional[Dict[str, int]]:
        """Ambil channel_id dan message_id dari leaderboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT leaderboard_channel_id, leaderboard_message_id
            FROM guild_config
            WHERE guild_id = ? AND leaderboard_message_id IS NOT NULL AND leaderboard_message_id != ''
        """, (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and row[1] and str(row[0]) != '0' and str(row[1]) != '0':
            try:
                return {
                    'channel_id': int(row[0]),
                    'message_id': int(row[1])
                }
            except (ValueError, TypeError):
                return None
        return None
    
    def set_user_stats_message(self, guild_id: int, user_id: int, channel_id: int, message_id: int):
        """Simpan message ID dari personal stats user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_stats
            SET stats_channel_id = ?, stats_message_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ?
        """, (str(channel_id), str(message_id), str(guild_id), str(user_id)))
        conn.commit()
        conn.close()
    
    def get_user_stats_message(self, guild_id: int, user_id: int) -> Optional[Dict[str, int]]:
        """Ambil channel_id dan message_id dari personal stats user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT stats_channel_id, stats_message_id
            FROM user_stats
            WHERE guild_id = ? AND user_id = ? AND stats_message_id IS NOT NULL AND stats_message_id != ''
        """, (str(guild_id), str(user_id)))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and row[1] and str(row[0]) != '0' and str(row[1]) != '0':
            try:
                return {
                    'channel_id': int(row[0]),
                    'message_id': int(row[1])
                }
            except (ValueError, TypeError):
                return None
        return None
    
    def set_ticket_setup_message(self, guild_id: int, channel_id: int, message_id: int, price_hash: str):
        """Simpan message ID dari ticket setup dan hash harga"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO guild_config (guild_id, ticket_setup_channel_id, ticket_setup_message_id, price_hash, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id) DO UPDATE SET
                ticket_setup_channel_id = excluded.ticket_setup_channel_id,
                ticket_setup_message_id = excluded.ticket_setup_message_id,
                price_hash = excluded.price_hash,
                updated_at = CURRENT_TIMESTAMP
        """, (str(guild_id), str(channel_id), str(message_id), price_hash))
        conn.commit()
        conn.close()
    
    def get_ticket_setup_message(self, guild_id: int) -> Optional[Dict[str, any]]:
        """Ambil channel_id, message_id, dan price_hash dari ticket setup"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticket_setup_channel_id, ticket_setup_message_id, price_hash
            FROM guild_config
            WHERE guild_id = ? AND ticket_setup_message_id IS NOT NULL
        """, (str(guild_id),))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and row[1]:
            try:
                return {
                    'channel_id': int(row[0]),
                    'message_id': int(row[1]),
                    'price_hash': row[2]
                }
            except (ValueError, TypeError):
                return None
        return None
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT stats_channel_id, stats_message_id
            FROM user_stats
            WHERE guild_id = ? AND user_id = ? AND stats_message_id IS NOT NULL AND stats_message_id != ''
        """, (str(guild_id), str(user_id)))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and row[1] and str(row[0]) != '0' and str(row[1]) != '0':
            try:
                return {
                    'channel_id': int(row[0]),
                    'message_id': int(row[1])
                }
            except (ValueError, TypeError):
                return None
        return None
    
    # === Item Prices Methods ===
    
    def init_default_prices(self, guild_id: int):
        """Initialize default item prices for a guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        default_prices = [
            ("A", "Item A", 74000),
            ("B", "Item B", 150000),
            ("C", "Item C", 222000),
            ("D", "Item D", 296000),
            ("E", "Item E", 370000)
        ]
        
        for code, name, price in default_prices:
            cursor.execute("""
                INSERT OR IGNORE INTO item_prices (guild_id, item_code, item_name, price, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (str(guild_id), code, name, price))
        
        conn.commit()
        conn.close()
    
    def get_item_prices(self, guild_id: int) -> Dict[str, int]:
        """Get all item prices for a guild"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Ensure default prices exist
        cursor.execute("SELECT COUNT(*) FROM item_prices WHERE guild_id = ?", (str(guild_id),))
        count = cursor.fetchone()[0]
        
        if count == 0:
            conn.close()
            self.init_default_prices(guild_id)
            conn = self.get_connection()
            cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_code, price
            FROM item_prices
            WHERE guild_id = ?
            ORDER BY item_code
        """, (str(guild_id),))
        
        prices = {}
        for row in cursor.fetchall():
            prices[row[0]] = row[1]
        
        conn.close()
        return prices
    
    def set_item_price(self, guild_id: int, item_code: str, price: int):
        """Update price for a specific item"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE item_prices
            SET price = ?, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND item_code = ?
        """, (price, str(guild_id), item_code))
        
        conn.commit()
        conn.close()
    
    def check_duplicate_proof(self, guild_id: int, proof_hash: str = None, transfer_signature: str = None):
        """Check if proof image hash OR transfer signature already exists in another ticket
        Returns: dict with ticket info if duplicate found, None otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check by transfer signature first (more accurate)
        if transfer_signature:
            cursor.execute("""
                SELECT t.ticket_number, t.user_id, t.game_username, t.created_at, t.status
                FROM tickets t
                WHERE t.guild_id = ? AND t.transfer_signature = ? AND t.transfer_signature IS NOT NULL
                ORDER BY t.created_at DESC
                LIMIT 1
            """, (str(guild_id), transfer_signature))
            
            row = cursor.fetchone()
            if row:
                conn.close()
                return {
                    'ticket_number': row[0],
                    'user_id': row[1],
                    'game_username': row[2],
                    'created_at': row[3],
                    'status': row[4],
                    'match_type': 'transfer_signature'
                }
        
        # Fallback: check by proof hash
        if proof_hash:
            cursor.execute("""
                SELECT t.ticket_number, t.user_id, t.game_username, t.created_at, t.status
                FROM tickets t
                WHERE t.guild_id = ? AND t.proof_hash = ? AND t.proof_hash IS NOT NULL
                ORDER BY t.created_at DESC
                LIMIT 1
            """, (str(guild_id), proof_hash))
            
            row = cursor.fetchone()
            if row:
                conn.close()
                return {
                    'ticket_number': row[0],
                    'user_id': row[1],
                    'game_username': row[2],
                    'created_at': row[3],
                    'status': row[4],
                    'match_type': 'proof_hash'
                }
        
        conn.close()
        return None
    
    def get_all_proof_hashes(self, guild_id: int):
        """Get all proof hashes from tickets for similarity comparison
        Returns: list of dicts with ticket info and proof_hash
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, ticket_number, user_id, game_username, created_at, status, proof_hash
            FROM tickets
            WHERE guild_id = ? AND proof_hash IS NOT NULL
            ORDER BY created_at DESC
        """, (str(guild_id),))
        
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                'ticket_id': row[0],
                'ticket_number': row[1],
                'user_id': row[2],
                'game_username': row[3],
                'created_at': row[4],
                'status': row[5],
                'proof_hash': row[6]
            })
        
        conn.close()
        return tickets
    
    def save_proof_hash(self, ticket_id: int, proof_hash: str, transfer_signature: str = None):
        """Save image hash and transfer signature to ticket for duplicate detection"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if transfer_signature column exists, add if not
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'transfer_signature' not in columns:
            cursor.execute("ALTER TABLE tickets ADD COLUMN transfer_signature TEXT")
            conn.commit()
        
        # Update both hash and signature
        if transfer_signature:
            cursor.execute("""
                UPDATE tickets
                SET proof_hash = ?, transfer_signature = ?
                WHERE id = ?
            """, (proof_hash, transfer_signature, ticket_id))
        else:
            cursor.execute("""
                UPDATE tickets
                SET proof_hash = ?
                WHERE id = ?
            """, (proof_hash, ticket_id))
        
        conn.commit()
        conn.close()
    
    # === Testimonial Methods ===
