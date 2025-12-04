# Discord Bot - Riwayat Perubahan & Setup

**Tanggal:** 5 Desember 2025 (Updated)
**Bot Name:** ASBLOX  
**Platform:** Render.com (Free Tier)  
**Repository:** https://github.com/A-XZ01/AbuyyXZ777
**Database:** SQLite (Fresh Schema - Dec 5, 2025)

---

## 🆕 UPDATE TERBARU (5 Desember 2025)

### **Database Migration - Fresh Start:**
- ✅ **Hapus database lama** yang corrupt dengan schema outdated
- ✅ **Database baru** dengan schema lengkap (semua tabel)
- ✅ **Fresh start** - data kosong, siap production
- ✅ **PostgreSQL ready** - auto-detect via DATABASE_URL

### **Bug Fixes:**
1. ✅ Fix `/reset_stats` - Interaction already responded error
2. ✅ Fix `/reset_stats reset_all:True` - sekarang hapus transactions juga
3. ✅ Fix `/add-item` - hapus parameter `code`, auto-generate dari name
4. ✅ Fix database schema - semua tabel dibuat dengan benar
5. ✅ Fix PostgreSQL support - indentasi SQLite schema, type hints

### **Permission Changes:**
- ✅ `/reset_stats reset_all:True` - **OWNER ONLY** (instant, no confirmation)
- ✅ Admin tidak bisa reset all - hanya owner

### **Code Cleanup:**
- ✅ Hapus unused confirmation buttons di `/reset_stats`
- ✅ Hapus parameter `code` dari `/add-item`
- ✅ Fix corrupted type hints di `db.py`
- ✅ Add psycopg2 type ignore untuk Pylance

---

## 🔧 KONFIGURASI BOT

### **Bot Token & Credentials:**
```
BOT_TOKEN: (Stored in Render environment variable - DISCORD_BOT_TOKEN)
CLIENT_ID: 1444283486121758891
GUILD_ID: 1445079009405833299 (ASBLOX Server)
```

### **Bot Invite Link:**
```
https://discord.com/api/oauth2/authorize?client_id=1444283486121758891&permissions=8&scope=bot%20applications.commands
```

### **Render Service:**
- **URL:** https://abuyxz777.onrender.com
- **Repository:** A-XZ01/AbuyyXZ777 (branch: main)
- **Auto-Deploy:** ON (deploy otomatis saat push ke GitHub)
- **Keep-Alive:** Sudah setup dengan Flask server + cron-job.org

---

## 📝 PERUBAHAN UTAMA YANG SUDAH DILAKUKAN

### **1. Leaderboard System - Daily & All-Time**

#### **Command yang Dihapus:**
- ❌ `/weekly-leaderboard` - Dihapus total (162 baris kode)
- ❌ `/setup-leaderboard` (nama lama) - Diganti

#### **Command Baru/Diubah:**
- ✅ `/daily-leaderboard` - Setup auto-update leaderboard harian di #lb-rich-daily
  - Auto-update setiap 1 jam (bukan 2 jam)
  - Menggunakan data transaksi hari ini (bukan mingguan)
  - Format embed modern dengan warna cyan
  
- ✅ `/allstats` - All-time leaderboard
  - Auto-post ke #lb-rich-weekly
  - Tidak kirim double (hanya post ke channel, bukan ke user)
  - Query langsung dari table `transactions`

#### **Format Leaderboard:**
```
Title: All-Time Leaderboard — Top Sultan
       Daily Leaderboard — Top Sultan Hari Ini

Ranking:
- Top 1: 👑 Crown
- Top 2: ⭐ Star  
- Top 3: 🔥 Fire
- Top 4-10: 💎 Diamond

Format: 
👑 Abuyy
1 deals • Rp71,910

Footer: Tanpa emoji, clean text saja
```

---

### **2. Deployment - Railway → Render**

#### **Masalah Railway:**
- ❌ Crash karena missing decorator `admin_or_owner()`
- ❌ Python version salah (3.14.0 tidak ada)
- ❌ User tidak punya credit card

#### **Solusi Render.com:**
- ✅ Free tier tanpa credit card
- ✅ Auto-deploy dari GitHub
- ✅ Python 3.12.0
- ✅ Keep-alive system dengan Flask

#### **File Deploy:**
```
runtime.txt: python-3.12.0
requirements.txt: discord.py, Flask, dll
keep_alive.py: Flask server port 8080 (anti-sleep)
Procfile: python bot.py
```

---

### **3. Code Improvements**

#### **Decorator Fix:**
```python
@admin_or_owner()  # Decorator baru untuk command yang butuh admin/owner access
```

#### **Server Whitelist:**
```python
ALLOWED_GUILDS = [1445079009405833299]  # Hanya ASBLOX server
```

#### **Database Functions:**
```python
get_daily_leaderboard()  # Query transaksi hari ini
get_leaderboard()        # Query all-time stats
```

---

### **4. Middleman Service Embed - Simplified**

#### **Perubahan:**
- ❌ Embed panjang 6 fields dengan ~30 baris
- ✅ Embed singkat 3 fields dengan ~15 baris
- ✅ Fokus pada: Cara Pakai, Fee, Keuntungan
- ✅ Hapus info redundant (metode bayar, penting, dll)

---

### **5. File Cleanup**

#### **File yang Dihapus:**
```
❌ check_db.py
❌ check_stats.py  
❌ check_weekly.py
❌ test_weekly_lb.py
❌ start_bot.bat
❌ start_bot_auto_restart.ps1
❌ PANDUAN_RAILWAY_DEPLOYMENT.md
❌ BOT_PERMISSIONS_SETUP.md
```

---

## 🚀 WORKFLOW DEPLOYMENT

### **Alur Kerja Sekarang:**
1. Edit code di local (VS Code)
2. Git commit & push ke GitHub
3. **Render auto-deploy** (tunggu 2-3 menit)
4. Bot restart otomatis
5. Test command di Discord

### **Cara Cek Bot Online:**
- Buka: https://abuyxz777.onrender.com
- Jika muncul "Bot is alive!" = Bot online ✅
- Atau lihat status bot di Discord member list

### **Keep-Alive Setup:**
- URL: https://abuyxz777.onrender.com
- Cron: cron-job.org (ping setiap 10 menit)
- Mencegah Render sleep setelah 15 menit idle

---

## 📊 DATABASE STRUCTURE

### **Tables:**
```sql
user_stats       - All-time user statistics
weekly_stats     - Weekly statistics (not used anymore)
transactions     - All transaction records
tickets          - Ticket system data
guild_config     - Server configuration
leaderboard_msg  - Leaderboard message tracking
```

### **Query Examples:**
```sql
-- Daily leaderboard
SELECT user_id, SUM(amount), COUNT(*) 
FROM transactions 
WHERE guild_id = ? AND DATE(timestamp) = TODAY()
GROUP BY user_id

-- All-time leaderboard  
SELECT user_id, SUM(amount), COUNT(*)
FROM transactions
WHERE guild_id = ?
GROUP BY user_id
```

---

## 🎯 COMMAND LIST (Active)

### **Owner Commands:**
- `/daily-leaderboard` - Setup daily leaderboard
- `/setup-mm` - Setup middleman ticket system

### **Admin Commands:**
- `/allstats` - Show all-time stats
- `/approve-ticket` - Approve purchase ticket
- `/approve-mm` - Approve middleman transaction
- `/close` - Close ticket

### **User Commands:**
- `/add` - Add item to ticket
- `/submit-proof` - Submit payment proof

---

## 📦 DEPENDENCIES

```txt
discord.py>=2.3.0
python-dotenv>=1.0.0
pytesseract>=0.3.10
Pillow>=10.0.0
aiohttp>=3.8.0
imagehash>=4.3.1
Flask>=3.0.0
```

---

## 🔐 ENVIRONMENT VARIABLES (Render)

```
DISCORD_BOT_TOKEN = (Set in Render dashboard - Environment tab)
GUILD_ID = 1445079009405833299
```

---

## 🐛 TROUBLESHOOTING

### **Command Tidak Muncul:**
1. Tunggu 2-3 menit setelah deploy
2. Kick & re-invite bot
3. Restart Discord client

### **Bot Offline:**
1. Cek Render dashboard: https://dashboard.render.com
2. Cek logs untuk error
3. Verify keep-alive cron job aktif

### **Database Kosong di Render:**
- Database di Render mulai dari 0
- Buat transaksi baru untuk populate data
- Database lokal ≠ database Render

---

## 📌 IMPORTANT NOTES (Updated Dec 5)

1. **Auto-Deploy ON** - Tidak perlu manual deploy lagi
2. **Git Push = Auto Deploy** - Tunggu 2-3 menit
3. **Keep-Alive Aktif** - Bot tidak sleep
4. **Database Fresh** - SQLite dengan schema lengkap (Dec 5, 2025)
5. **Server Whitelist** - Hanya ASBLOX server (ID: 1445079009405833299)
6. **PostgreSQL Ready** - Set DATABASE_URL untuk auto-switch
7. **No Database in Git** - Database file di-ignore, local only

---

## 🔗 USEFUL LINKS

- **GitHub Repo:** https://github.com/A-XZ01/AbuyyXZ777
- **Render Dashboard:** https://dashboard.render.com
- **Bot Service URL:** https://abuyxz777.onrender.com
- **Cron Job:** https://cron-job.org

---

## ✅ COMPLETION CHECKLIST (Updated Dec 5)

- [x] Hapus `/weekly-leaderboard`
- [x] Rename `/setup-leaderboard` → `/daily-leaderboard`
- [x] Ubah weekly → daily stats
- [x] Auto-update 2 jam → 1 jam
- [x] Fix Railway deployment issues
- [x] Migrate to Render.com
- [x] Setup keep-alive system
- [x] Fix `/allstats` double post
- [x] Remove emoji from title/footer
- [x] Keep ranking icons (top 1-3, 4-10)
- [x] Simplify middleman embed
- [x] Cleanup unused files
- [x] Test all commands in production
- [x] Add PostgreSQL support
- [x] Fix database schema issues
- [x] Fix `/reset_stats` interaction error
- [x] Make reset_all owner-only instant
- [x] Simplify `/add-item` command
- [x] Fresh database deployment

---

**Last Updated:** 5 Desember 2025, 13:45 WIB  
**Status:** ✅ Production Ready - Fresh Database  
**Database:** SQLite (semua tabel lengkap, ready untuk data baru)

**Next Steps:**
1. Test create ticket - pastikan tidak ada error
2. Test `/add-item` dengan parameter baru
3. Monitor bot di production
4. (Optional) Migrate ke PostgreSQL untuk data permanen
- [x] Ubah weekly → daily stats
- [x] Auto-update 2 jam → 1 jam
- [x] Fix Railway deployment issues
- [x] Migrate to Render.com
- [x] Setup keep-alive system
- [x] Fix `/allstats` double post
- [x] Remove emoji from title/footer
- [x] Keep ranking icons (top 1-3, 4-10)
- [x] Simplify middleman embed
- [x] Cleanup unused files
- [x] Test all commands in production
- [x] Add PostgreSQL support to db.py
- [x] Push database file to GitHub
- [x] Fix IndentationError for PostgreSQL compatibility

---

**Last Updated:** 5 Desember 2025, 12:30 WIB  
**Status:** ✅ Production Ready (SQLite + PostgreSQL Support)  
**Database:** SQLite (synced from GitHub) - 28 transaksi, 3 users

---

## 🔄 UPDATE TERBARU (5 Desember 2025)

### **PostgreSQL Support Added:**
- ✅ `db.py` sekarang support **PostgreSQL & SQLite**
- ✅ Auto-detect via `DATABASE_URL` environment variable  
- ✅ Database file (`bot_database.db`) di-push ke GitHub untuk persistence
- ✅ Ready untuk migrasi ke PostgreSQL kapan saja (Neon/Supabase)

### **Database Status:**
- **Local (Development):** SQLite - `data/bot_database.db`
- **Render (Production):** SQLite - synced dari GitHub setiap deploy
- **Data Tersimpan:** 28 transaksi, 3 users, 2 tiket, 91 audit logs, 4 achievements

### **Current Limitations:**
⚠️ **SQLite di Render akan reset saat:**
- Manual redeploy dari Render dashboard
- Major rebuild (dependency changes)
- **Solusi:** Data di-backup di GitHub, akan restored otomatis setelah deploy

### **Recommended Next Step (Optional):**
Migrasi ke **Neon PostgreSQL** untuk data 100% permanen:
1. Signup: https://neon.tech (gratis 3GB)
2. Create database → Copy connection string
3. Set `DATABASE_URL` di Render environment variable
4. Bot auto-switch ke PostgreSQL (no code change needed)
5. Run migration script untuk import data dari SQLite

---

**Next Steps:** Monitor bot performance, consider PostgreSQL migration untuk production stability
