# 🤖 ASBLOX Discord Bot - Command Reference

**Bot Name:** ASBLOX  
**Status:** ✅ Production Ready (Deployed on DigitalOcean)  
**Server:** 152.42.228.254:8080  
**Total Commands:** 27 Slash Commands  

---

## 📊 STATISTIK & LEADERBOARD

### `/stats`
Menampilkan statistik Total Transaksi dan Total Spend user.
- **Usage:** `/stats` atau `/stats user:@username`
- **Permission:** Everyone
- **Info:** Tampilkan ranking, progress bar, multi-currency display

### `/allstats`
📊 All-Time Leaderboard - Statistik sepanjang waktu
- **Usage:** `/allstats` atau `/allstats page:2 per_page:10`
- **Permission:** ADMIN
- **Info:** Leaderboard dengan emoji ranking (🥇🥈🥉)

### `/daily-leaderboard`
Setup auto-update leaderboard harian di #lb-rich-daily (refresh setiap 1 jam)
- **Usage:** `/daily-leaderboard`
- **Permission:** OWNER ONLY
- **Info:** Auto-post daily leaderboard ke channel

---

## 🎫 TICKET SYSTEM

### `/add`
Tambahkan item ke ticket Anda (gunakan di ticket channel).
- **Usage:** `/add` (di dalam ticket channel)
- **Permission:** Everyone
- **Info:** Gunakan di ticket untuk add item ke keranjang

### `/approve-ticket`
[ADMIN] Approve transaksi di ticket ini dan close ticket.
- **Usage:** `/approve-ticket` (di dalam ticket channel)
- **Permission:** ADMIN
- **Info:** Approve & close ticket sekaligus

### `/reject-ticket`
[ADMIN] Reject transaksi di ticket ini.
- **Usage:** `/reject-ticket` (di dalam ticket channel)
- **Permission:** ADMIN
- **Info:** Reject transaksi & berikan alasan

### `/close`
Tutup ticket Anda (buyer atau admin).
- **Usage:** `/close`
- **Permission:** Everyone (Ticket Owner), ADMIN
- **Info:** Close ticket tanpa approve/reject

---

## 🤝 MIDDLEMAN SYSTEM

### `/approve-mm`
[ADMIN] Approve middleman transaction dan release dana ke seller.
- **Usage:** `/approve-mm` (di middleman ticket channel)
- **Permission:** ADMIN
- **Info:** Approve middleman & release dana ke seller

### `/reject-mm`
[ADMIN] Reject middleman transaction.
- **Usage:** `/reject-mm` (di middleman ticket channel)
- **Permission:** ADMIN
- **Info:** Reject middleman & kembalikan dana ke buyer

---

## ⚙️ SETUP & KONFIGURASI

### `/setup-ticket`
[OWNER] Setup channel open-ticket untuk buyer.
- **Usage:** `/setup-ticket channel:#channel-name`
- **Permission:** OWNER ONLY
- **Info:** Setup button "Create Ticket" di channel

### `/setup-mm`
[OWNER] Setup channel untuk middleman ticket system.
- **Usage:** `/setup-mm channel:#channel-name`
- **Permission:** OWNER ONLY
- **Info:** Setup button "Create Middleman Ticket" di channel

### `/set-rate`
[OWNER] Ubah rate Robux (harga per 1 Robux dalam Rupiah).
- **Usage:** `/set-rate rate:500`
- **Permission:** OWNER ONLY
- **Info:** Ubah conversion rate Robux ke IDR

### `/add-item`
[OWNER] Tambah item baru ke katalog
- **Usage:** `/add-item name:Diamond robux:1000 price_idr:250000`
- **Permission:** OWNER ONLY
- **Info:** Tambah item ke katalog bot

### `/remove-item`
[OWNER] Hapus item dari katalog
- **Usage:** `/remove-item code:DIAMOND`
- **Permission:** OWNER ONLY
- **Info:** Hapus item dari katalog

---

## 👥 ADMIN & PERMISSION

### `/set-admin`
[OWNER] Tambah role sebagai Admin untuk manage bot.
- **Usage:** `/set-admin role:@role-name`
- **Permission:** OWNER ONLY
- **Info:** Tambahkan role admin untuk bot management

### `/remove-admin`
[OWNER] Hapus role Admin dari bot.
- **Usage:** `/remove-admin role:@role-name`
- **Permission:** OWNER ONLY
- **Info:** Hapus role admin

### `/list-admins`
[ADMIN] Lihat daftar Admin bot di server ini.
- **Usage:** `/list-admins`
- **Permission:** ADMIN
- **Info:** Tampilkan semua admin roles

### `/addrole`
[ADMIN] Berikan role ke user.
- **Usage:** `/addrole user:@username role:@role-name`
- **Permission:** ADMIN
- **Info:** Add role ke user

### `/removerole`
[ADMIN] Hapus role dari user.
- **Usage:** `/removerole user:@username role:@role-name`
- **Permission:** ADMIN
- **Info:** Remove role dari user

### `/permissions`
[OWNER] Lihat permission level dan command yang tersedia.
- **Usage:** `/permissions`
- **Permission:** OWNER ONLY
- **Info:** Lihat command apa saja yang tersedia per permission level

---

## 📋 USER & INFO

### `/user-info`
[ADMIN] Lihat info detail user tertentu.
- **Usage:** `/user-info user:@username`
- **Permission:** ADMIN
- **Info:** Tampilkan detail statistik & transaksi user

---

## 🔧 MAINTENANCE & BACKUP

### `/reset_stats`
[OWNER] Reset Total Transaksi dan Total Spend untuk user atau semua user.
- **Usage:** `/reset_stats user:@username` atau `/reset_stats reset_all:true`
- **Permission:** OWNER ONLY
- **Info:** Reset stats instant (no confirmation)

### `/reset-tickets`
[ADMIN] Hapus tickets user tertentu.
- **Usage:** `/reset-tickets user:@username`
- **Permission:** ADMIN
- **Info:** Hapus semua open tickets user

### `/reset-all-tickets`
[OWNER] Hapus SEMUA tickets dari semua user di server ini.
- **Usage:** `/reset-all-tickets`
- **Permission:** OWNER ONLY
- **Info:** Nuclear option - hapus semua tickets

### `/rollback_backup`
[OWNER] Restore data dari backup terakhir atau dari file backup yang dipilih.
- **Usage:** `/rollback_backup` atau `/rollback_backup filename:backup_2025_12_05.db`
- **Permission:** OWNER ONLY
- **Info:** Restore database dari backup

### `/list_backups`
[OWNER] Tampilkan daftar file backup yang tersedia.
- **Usage:** `/list_backups` atau `/list_backups limit:20`
- **Permission:** OWNER ONLY
- **Info:** Lihat daftar backup files

---

## 🧹 UTILITY

### `/clear`
[OWNER] Hapus semua pesan di channel ini.
- **Usage:** `/clear`
- **Permission:** OWNER ONLY
- **Info:** Clear semua messages di current channel

---

## 📍 PERMISSION LEVELS

| Level | Role | Description |
|-------|------|-------------|
| **OWNER** | Server Owner | Full access, semua command |
| **ADMIN** | Custom Admin Role | Manage tickets, stats, user info |
| **Everyone** | All Members | Use tickets, stats, add items |

---

## 🔗 BOT FEATURES

### Ticket System
- 🎫 Private channels untuk buyer order
- 📦 Item selection dengan dropdown
- 💾 Automatic item tracking
- 📸 Transfer proof validation
- 🏆 Transaction history

### Middleman System
- 🤝 Secure middleman transactions
- 💰 Flexible fee structure (Buyer/Seller/Split)
- 📋 Middleman verification
- ✅ Approval workflow
- 💸 Auto-payout to seller

### Statistics & Analytics
- 📊 User ranking & leaderboard
- 📈 Daily/All-time stats
- 💱 Multi-currency display (IDR + USD)
- 🏅 Achievement tracking
- 📉 Progress visualization

### Database & Backup
- 🗄️ SQLite/PostgreSQL support
- 📅 Auto-backup every 24 hours
- 🔄 Rollback capability
- 📝 Audit logs
- 🛡️ Data integrity checks

---

## 🚀 DEPLOYMENT INFO

| Info | Value |
|------|-------|
| **Platform** | DigitalOcean (Ubuntu 24.04 LTS) |
| **IP Address** | 152.42.228.254 |
| **Port** | 8080 (Flask Server) |
| **Process Manager** | Supervisor |
| **Database** | SQLite / PostgreSQL |
| **Auto-Restart** | Yes (Supervisor) |
| **Uptime** | 24/7 |

---

## 📞 SUPPORT COMMANDS

For help with a specific command:
- `/permissions` - Lihat semua command & permission
- `/help command:name` - Get help untuk specific command (jika ada)

---

**Last Updated:** 5 December 2025  
**Bot Status:** ✅ Active & Running  
**Version:** Production v1.0
