!(image.png)# Discord Bot - Riwayat Perubahan & Setup

**Tanggal:** 9 Desember 2025 (Updated)
**Bot Name:** ASBLOX  
**Platform:** DigitalOcean App Platform (primary) • Droplet (legacy scripts only)  
**Server IP (legacy droplet):** 159.223.71.87  
**Repository:** https://github.com/A-XZ01/AbuyyXZ777
**Database:** SQLite (fresh schema Dec 5, 2025; PostgreSQL-ready via `DATABASE_URL`)

---

## 🆕 UPDATE TERBARU (9 Desember 2025)

### **✅ Environment & Deploy:**
- ✅ `.python-version` ditambahkan → pin Python 3.12 di App Platform.
- ✅ `requirements.txt` disederhanakan (Flask/keep_alive dihapus; aiohttp 3.9).
- ✅ Deploy utama: DigitalOcean App Platform (`app.yaml`, `pip install -r requirements.txt`, `python bot.py`).
- ✅ Legacy droplet & PowerShell scripts tetap ada sebagai fallback manual.

### **✅ MIGRASI KE DIGITALOCEAN SELESAI:**
- ✅ **Droplet Created** - Ubuntu 24.04 LTS di Singapore region
- ✅ **IP Address:** 159.223.71.87
- ✅ **Python 3.12** installed dengan virtual environment
- ✅ **Bot deployed** - running 24/7 dengan Supervisor
- ✅ **Auto-restart** enabled - bot restart otomatis kalau crash
- ✅ **SSH Key** configured untuk secure access
- ✅ **Deploy scripts** - 4 PowerShell scripts untuk easy deployment

### **🚀 PowerShell Deploy Scripts (DigitalOcean):**
1. **deploy.ps1** - Deploy dengan custom commit message
2. **deploy-simple.ps1** - Deploy cepat dengan auto-message
3. **check-bot.ps1** - Cek status dan logs bot
4. **restart-bot.ps1** - Restart bot tanpa update code

### **Previous Updates:**

### **UI/UX Improvements:**
- ✅ **Middleman ticket embed** - minimized dari 8 fields ke 4 fields
- ✅ **Professional design** - elegant, modern, clean layout
- ✅ **Reduced clutter** - merge redundant fields (Buyer/Seller/Item)
- ✅ **Added timestamp** - footer dengan tanggal formatted

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
- ✅ Simplify middleman embed - 37 lines reduced

---

## 🔧 KONFIGURASI BOT

### **Bot Token & Credentials:**
```
DISCORD_BOT_TOKEN: simpan di .env di server (Supervisor env)
CLIENT_ID: 1444283486121758891
GUILD_ID: 1445079009405833299 (ASBLOX Server)
```

### **Bot Invite Link:**
```
https://discord.com/api/oauth2/authorize?client_id=1444283486121758891&permissions=8&scope=bot%20applications.commands
```

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

### **2. Deployment - DigitalOcean (Supervisor)**

- ✅ Bot dijalankan via Supervisor service `discordbot`
- ✅ Deploy via git pull + supervisorctl restart (lihat skrip PowerShell)
- ✅ Tidak pakai keep-alive Flask / Procfile / runtime.txt
- ✅ DATABASE_URL opsional untuk PostgreSQL; default SQLite di server

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

### **Alur Kerja Sekarang (DigitalOcean):**
1. Edit code di local (VS Code)
2. Git commit & push ke GitHub
3. Jalankan **deploy.ps1** atau **deploy-simple.ps1** (ssh ke droplet → git pull → supervisorctl restart)
4. Cek status dengan **check-bot.ps1** (lihat supervisor status + tail log)
5. Bot tetap 24/7 via Supervisor, tidak butuh keep-alive Flask

### **Cara Cek Bot Online:**
- `ssh root@159.223.71.87` kemudian `supervisorctl status discordbot`
- Lihat presence bot di Discord member list

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
aiohttp>=3.9.0
imagehash>=4.3.1
psycopg2-binary>=2.9.9
```

---

## 🔐 ENVIRONMENT VARIABLES (Server)

```
DISCORD_BOT_TOKEN = simpan di .env server atau Supervisor env
GUILD_ID = 1445079009405833299
DATABASE_URL = (opsional, PostgreSQL jika ingin)
```

---

## 🐛 TROUBLESHOOTING

### **Command Tidak Muncul:**
1. Tunggu 2-3 menit setelah deploy
2. Kick & re-invite bot
3. Restart Discord client

### **Bot Offline:**
1. SSH atau jalankan **check-bot.ps1**
2. `supervisorctl status discordbot`
3. `tail -n 200 /var/log/discordbot.out.log`

### **Database Kosong di Server:**
- Default SQLite di `/root/AbuyyXZ777/data/bot_database.db`
- Untuk PostgreSQL, set `DATABASE_URL` lalu restart bot

---

## 📌 IMPORTANT NOTES (Updated Dec 5)

1. Deploy via **deploy.ps1/deploy-simple.ps1** (ssh + supervisor restart)
2. Tidak pakai keep-alive Flask/Render; Supervisor jaga 24/7
3. Database default: SQLite on-server (Dec 5, 2025 schema)
4. Server whitelist: hanya ASBLOX (ID: 1445079009405833299)
5. PostgreSQL ready via `DATABASE_URL` (opsional)
6. Database file tidak di-commit

---

## 🔗 USEFUL LINKS

- **GitHub Repo:** https://github.com/A-XZ01/AbuyyXZ777
- **Droplet IP (SSH):** 159.223.71.87
- **Supervisor Service:** discordbot (log: /var/log/discordbot.out.log)

---

## ✅ COMPLETION CHECKLIST (Updated Dec 5)

- [x] Hapus `/weekly-leaderboard`
- [x] Rename `/setup-leaderboard` → `/daily-leaderboard`
- [x] Ubah weekly → daily stats
- [x] Auto-update 2 jam → 1 jam
- [x] Migrasi ke DigitalOcean + Supervisor
- [x] Hapus ketergantungan Render/Railway/keep_alive
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
- [x] Minimize middleman ticket embed

---

**Last Updated:** 5 Desember 2025, 14:00 WIB  
**Status:** ✅ Production Ready - Fresh Database  
**Database:** SQLite (semua tabel lengkap, ready untuk data baru)

**Recent Changes:**
1. ✅ Middleman ticket embed - reduced dari 8 ke 4 fields
2. ✅ Professional UI - elegant, modern, minimalist
3. ✅ Timestamp added to embed footer
4. ✅ Merged redundant fields (Buyer/Seller/Item)

**Next Steps:**
1. Test middleman ticket creation - verify new embed design
2. Test `/add-item` dengan parameter baru
3. Monitor bot di production
4. (Optional) Migrate ke PostgreSQL untuk data permanen
4. Bot auto-switch ke PostgreSQL (no code change needed)
5. Run migration script untuk import data dari SQLite

---

**Next Steps:** Monitor bot performance, consider PostgreSQL migration untuk production stability
