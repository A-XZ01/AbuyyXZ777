# Discord Bot - Transaction Tracker Pro

Bot Discord profesional untuk tracking transaksi dan statistik user dengan SQLite database, achievement system, analytics, dan banyak fitur lainnya.

## ✨ Fitur Utama

- **📊 Tracking Transaksi**: Catat deals completed dan total nilai IDR per user
- **🎫 Ticket System**: Private channel untuk buyer order multiple items
- **🛒 Semi-Automated Payments**: Sistem pembayaran otomatis dengan BCA bank transfer
- **🤖 Auto-Detection**: Deteksi otomatis transaksi dari pesan di channel
- **💾 Database SQLite**: Storage yang aman dan cepat dengan audit log lengkap
- **🏆 Achievement System**: Unlock badges berdasarkan milestone transaksi
- **📈 Analytics**: Statistik weekly/monthly dengan visualisasi progress bar
- **🎯 Leaderboard**: Ranking dengan emoji medals (🥇🥈🥉)
- **📜 Transaction History**: Riwayat lengkap setiap transaksi
- **💱 Multi-Currency Display**: Tampilkan IDR + estimasi USD
- **⚙️ Per-Guild Config**: Konfigurasi terpisah untuk setiap server
- **📦 Auto-Backup**: Backup otomatis setiap 24 jam
- **💾 Export CSV**: Export transaksi ke file CSV
- **🎨 Beautiful Embeds**: UI modern dengan embed cards
- **👥 Role-Based Access**: Kontrol akses administrator yang fleksibel

## 📋 Requirements

- Python 3.8 atau lebih baru
- Discord Bot Token
- Discord Server dengan permission Administrator untuk setup

## 🚀 Quick Start

### 1. Clone atau Download

```bash
cd Discord-BOT
```

### 2. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Setup Environment Variables

Buat file `.env` di folder `Discord-BOT`:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
GUILD_ID=your_primary_server_id_here
```

**Note:** Bot sekarang mendukung **multi-server**! Command akan tersedia di semua server tempat bot diundang. `GUILD_ID` hanya digunakan untuk legacy migration dari JSON ke SQLite.

**Cara mendapatkan token dan Guild ID:**
- Bot Token: https://discord.com/developers/applications
- Guild ID: Enable Developer Mode di Discord → Right-click server → Copy ID

### 4. Enable Discord Intents

Di Discord Developer Portal → Your App → Bot → Privileged Gateway Intents:
- ✅ Enable **Server Members Intent**
- ✅ Enable **Message Content Intent**

### 5. Invite Bot ke Server

Generate invite URL dengan scopes:
- `bot`
- `applications.commands`

Permissions yang dibutuhkan:
- Read Messages/View Channels
- Send Messages
- Embed Links
- Read Message History

**Bot dapat diundang ke multiple servers!** Setiap server akan memiliki data dan konfigurasi terpisah.

### 6. Run Bot

```powershell
python bot.py
```

Jika sukses, Anda akan melihat:
```
✅ Bot berhasil Login sebagai BotName (ID: 123456789)
📡 Bot aktif di 2 server
⏳ Mencoba sinkronisasi Slash Commands...
🎉 17 Slash Commands synced globally! Bot siap digunakan.
```

**Multi-Server Support:** Commands akan otomatis tersedia di semua server. Mungkin perlu 1-5 menit untuk sync global pertama kali.

### 7. Migration Otomatis

Jika Anda memiliki data JSON lama (`user_data.json`), bot akan otomatis migrasi ke SQLite pada run pertama.

## 📚 Command Reference

### 📊 Statistik & Leaderboard

#### `/stats [user]`
Tampilkan statistik lengkap user dengan ranking, progress bar, dan multi-currency display.
- `user` (opsional): Tag user lain (default: diri sendiri)
- **Alias**: `/s`

**Contoh:**
```
/stats
/s user:@JohnDoe
```

#### `/allstats [page] [per_page]`
Leaderboard dengan emoji ranking (🥇🥈🥉) dan pagination.
- `page` (opsional): Halaman leaderboard (default: 1)
- `per_page` (opsional): Jumlah per halaman (default: 10, max: 20)
- **Alias**: `/lb`

**Contoh:**
```
/allstats
/lb page:2 per_page:15
```

#### `/history [user] [limit]`
Lihat riwayat transaksi lengkap dengan timestamp dan kategori.
- `user` (opsional): User yang ingin dilihat (default: diri sendiri)
- `limit` (opsional): Jumlah transaksi (default: 10, max: 25)
- **Alias**: `/h`

**Contoh:**
```
/history
/h user:@JohnDoe limit:20
```

#### `/achievements [user]`
Lihat semua achievement/badge yang sudah unlocked.
- `user` (opsional): User yang ingin dilihat (default: diri sendiri)

**Achievements available:**
- 🎯 Starter - 10 Transaksi
- 🔥 Dedicated - 50 Transaksi
- ⭐ Expert - 100 Transaksi
- 💎 Master - 500 Transaksi
- 💰 Millionaire - Rp1 Juta
- 💸 Big Spender - Rp5 Juta
- 🏆 High Roller - Rp10 Juta
- 👑 Whale - Rp50 Juta

### 📈 Analytics

#### `/weekly [user]`
Statistik 7 hari terakhir dengan rata-rata per hari.
- `user` (opsional): User yang ingin dilihat (default: diri sendiri)

#### `/monthly [user]`
Statistik 30 hari terakhir dengan rata-rata per hari.
- `user` (opsional): User yang ingin dilihat (default: diri sendiri)

### 💼 Transaction Management

#### `/complete item [user]`
Catat transaksi selesai secara manual dengan dropdown item selection.
- `item`: Pilih item A-E (harga otomatis terisi)
- `user` (opsional): User yang melakukan transaksi (default: diri sendiri)

**Item Prices:**
- Item A: Rp74.000
- Item B: Rp148.000
- Item C: Rp222.000
- Item D: Rp296.000
- Item E: Rp370.000

**Contoh:**
```
/complete item:A
/complete item:B user:@JohnDoe
```

#### `/export [user]`
Export riwayat transaksi ke file CSV.
- `user` (opsional): User yang ingin di-export (default: diri sendiri)

### 🎫 Ticket System (Recommended)

#### `/ticket game_username`
Buka ticket private channel untuk order item.
- `game_username`: Username game Anda untuk pengiriman item (WAJIB)

**Workflow:**
1. Bot create private channel (contoh: `ticket-0001`)
2. Gunakan `/add` untuk order multiple items
3. Transfer total ke BCA → `/submit` upload bukti
4. Admin review dan `/approve-ticket` atau `/reject-ticket`
5. Channel auto-delete setelah selesai

**Contoh:**
```
/ticket game_username:PlayerXYZ123
/add item:A quantity:2
/add item:C quantity:1
/submit proof:https://i.imgur.com/abc.png
```

#### `/add item quantity`
Tambah item ke ticket Anda (gunakan di ticket channel).
- `item`: Pilih item A-E
- `quantity`: Jumlah item (default: 1)

**Contoh:**
```
/add item:A quantity:3
/add item:B quantity:1
```

#### `/submit proof`
Submit bukti transfer untuk order di ticket.
- `proof`: Link gambar bukti transfer

**Contoh:**
```
/submit proof:https://i.imgur.com/abc123.png
```

#### `/close`
Tutup ticket Anda (buyer atau admin).

**Contoh:**
```
/close
```

### 🛒 Legacy Payment System

#### `/buy item game_username`
Pesan item - Bot otomatis kirim instruksi pembayaran ke DM Anda.
- `item`: Pilih item A-E yang ingin dibeli
- `game_username`: Username game Anda untuk pengiriman item (WAJIB)

**Workflow:**
1. Pilih item yang ingin dibeli
2. Bot kirim Payment ID + instruksi transfer BCA ke DM
3. Transfer sesuai jumlah ke rekening BCA
4. Upload bukti dengan `/confirm`

**Contoh:**
```
/buy item:A game_username:PlayerXYZ123
/buy item:C game_username:GamerPro456
```

#### `/confirm payment_id proof`
Upload bukti transfer untuk order Anda.
- `payment_id`: Payment ID yang diterima saat `/buy`
- `proof`: Link gambar bukti transfer (imgur, discord attachment, etc.)

**Tips untuk upload proof:**
1. Screenshot bukti transfer
2. Upload ke Discord channel pribadi atau imgur
3. Right-click gambar → Copy Link
4. Paste link di parameter `proof`

**Contoh:**
```
/confirm payment_id:42 proof:https://i.imgur.com/abc123.png
/confirm payment_id:15 proof:https://cdn.discordapp.com/attachments/...
```

### 🛒 Payment System (Admin)

#### `/pending`
Lihat semua pembayaran yang menunggu approval dengan bukti transfer.

Output:
- Payment ID
- Buyer name
- Item ordered
- Amount
- Created timestamp
- Link bukti transfer
- Quick action commands

**Contoh:**
```
/pending
```

#### `/approve payment_id`
Approve pembayaran dan complete transaksi otomatis.
- `payment_id`: Payment ID yang akan di-approve

**Workflow:**
1. Cek pembayaran dengan `/pending`
2. Klik link bukti transfer untuk validasi
3. Approve dengan `/approve`
4. Bot otomatis:
   - Update user stats
   - Add transaction record
   - Check & unlock achievements
   - Notify buyer via DM

**Contoh:**
```
/approve payment_id:42
```

#### `/reject payment_id [reason]`
Tolak pembayaran dengan alasan.
- `payment_id`: Payment ID yang ditolak
- `reason` (opsional): Alasan penolakan (default: "Bukti transfer tidak valid")

Bot otomatis notify buyer via DM dengan alasan penolakan.

**Contoh:**
```
/reject payment_id:42
/reject payment_id:15 reason:Jumlah transfer tidak sesuai
```

### Admin Commands
Export riwayat transaksi ke file CSV.
- `user` (opsional): User yang ingin di-export (default: diri sendiri)

### 🎫 Ticket System (Admin)

#### `/setup-ticket`
Setup channel #open-ticket untuk buyer buka ticket otomatis.
- Bot create channel `#open-ticket`
- Kirim instruksi lengkap di channel
- Buyer ketik username game → auto-create ticket

**Contoh:**
```
/setup-ticket
```

#### `/approve-ticket`
Approve transaksi di ticket dan close ticket otomatis.
- Auto-update user stats
- Auto-add transactions
- Auto-unlock achievements
- Channel deleted dalam 10 detik

**Contoh:**
```
/approve-ticket
```

#### `/reject-ticket [reason]`
Reject transaksi di ticket dengan alasan.
- `reason` (opsional): Alasan penolakan
- Channel deleted dalam 30 detik

**Contoh:**
```
/reject-ticket reason:Bukti transfer tidak valid
```

### Admin Commands

#### `/reset_stats [user] [reset_all]`
Reset statistik user atau semua user (dengan konfirmasi dan backup otomatis).
- `user` (opsional): User yang di-reset (default: diri sendiri)
- `reset_all`: true untuk reset semua (admin only, memerlukan konfirmasi)

**Contoh:**
```
/reset_stats
/reset_stats user:@JohnDoe
/reset_stats reset_all:true
```

#### `/config action [value]`
Kelola konfigurasi server.
- `action`: `view`, `set_channels`, `set_currency`, `set_admin_roles`
- `value`: Nilai untuk set action

**Contoh:**
```
/config action:view
/config action:set_channels value:123456789,987654321
/config action:set_channels value:all
/config action:set_currency value:IDR
/config action:set_admin_roles value:123456789
```

#### `/list_backups [limit]`
Tampilkan daftar file backup dengan pagination interaktif.
- `limit` (opsional): Jumlah item ditampilkan (default: 10, max: 50)

#### `/rollback_backup [filename]`
Restore data dari backup (dengan pre-restore backup untuk safety).
- `filename` (opsional): Nama file backup (default: backup terbaru)

**Contoh:**
```
/rollback_backup
/rollback_backup filename:user_data_backup_20251201T120000Z.json
```

## 🤖 Auto-Detection

Bot secara otomatis mendeteksi transaksi dari pesan di channel dengan format:
- `TRANSAKSI SELESAI: 1500000`
- `transaksi selesai 1500000`
- `transaksi: 1.500.000`

**Konfigurasi channel:**
- Secara default aktif di semua channel
- Admin dapat membatasi ke channel tertentu dengan `/config action:set_channels value:CHANNEL_IDS`

**Multi-Server:** Setiap server memiliki konfigurasi auto-detect terpisah. Setup di satu server tidak mempengaruhi server lain.

## 📂 Struktur File

```
Discord-BOT/
├── bot.py              # Main bot script
├── db.py               # Database module (SQLite)
├── .env                # Environment variables (buat sendiri)
├── requirements.txt    # Python dependencies
├── README.md          # Dokumentasi ini
└── data/
    ├── bot_database.db     # SQLite database (dibuat otomatis)
    └── backups/            # Folder backup (dibuat otomatis)
        ├── user_data_backup_*.json
        └── user_data_pre_restore_*.json
```

## 🔧 Database Schema

### `user_stats`
Statistik aggregat per user
- `guild_id`: ID server Discord
- `user_id`: ID user Discord
- `deals_completed`: Jumlah transaksi selesai
- `total_idr_value`: Total nilai IDR
- `updated_at`: Timestamp update terakhir

### `transactions`
Detail setiap transaksi individual
- `id`: Auto-increment ID
- `guild_id`: ID server
- `user_id`: ID user
- `amount`: Jumlah IDR
- `category`: Kategori (manual/auto_detect)
- `notes`: Catatan tambahan
- `recorded_by`: User ID yang mencatat
- `timestamp`: Waktu transaksi

### `achievements`
Achievement yang sudah unlocked per user
- `id`: Auto-increment ID
- `guild_id`: ID server
- `user_id`: ID user
- `achievement_type`: Tipe achievement (deals_10, value_1m, etc)
- `achievement_value`: Nilai threshold
- `unlocked_at`: Waktu unlock

### `guild_config`
Konfigurasi per server
- `guild_id`: ID server Discord
- `auto_detect_channels`: JSON array channel IDs
- `admin_roles`: JSON array role IDs
- `currency`: Mata uang (default: IDR)
- `auto_detect_regex`: Regex pattern untuk deteksi transaksi

### `audit_log`
Log semua aksi penting
- `id`: Auto-increment ID
- `guild_id`: ID server
- `user_id`: ID user yang melakukan aksi
- `action`: Jenis aksi
- `details`: Detail aksi
- `timestamp`: Waktu aksi

### `pending_payments`
Pembayaran yang menunggu approval (legacy system)
- `id`: Auto-increment ID (Payment ID)
- `guild_id`: ID server
- `user_id`: ID buyer
- `item_name`: Nama item yang dibeli
- `amount`: Jumlah pembayaran IDR
- `game_username`: Username game buyer untuk pengiriman item
- `payment_method`: Metode pembayaran (default: BCA)
- `proof_url`: Link bukti transfer
- `status`: Status pembayaran (pending/awaiting_approval/approved/rejected)
- `created_at`: Waktu order dibuat
- `approved_at`: Waktu di-approve/reject
- `approved_by`: User ID admin yang approve/reject

### `tickets`
Ticket private channels untuk buyer
- `id`: Auto-increment ID (Ticket ID)
- `guild_id`: ID server
- `user_id`: ID buyer (owner ticket)
- `channel_id`: ID channel Discord
- `ticket_number`: Nomor ticket (0001, 0002, etc.)
- `game_username`: Username game buyer
- `status`: Status ticket (open/closed)
- `created_at`: Waktu ticket dibuat
- `closed_at`: Waktu ticket ditutup
- `closed_by`: User ID yang close ticket
- **UNIQUE(guild_id, user_id, status)**: 1 user hanya bisa punya 1 open ticket

### `ticket_items`
Items yang dipesan dalam ticket
- `id`: Auto-increment ID
- `ticket_id`: ID ticket (foreign key)
- `item_name`: Nama item
- `quantity`: Jumlah item
- `amount`: Total harga (unit_price × quantity)
- `added_at`: Waktu item ditambahkan

## 🛠️ Troubleshooting

### Bot tidak login
- Periksa `DISCORD_BOT_TOKEN` di `.env` sudah benar
- Pastikan bot tidak dibanned di server

### Slash commands tidak muncul
- Pastikan `GUILD_ID` di `.env` benar
- Tunggu beberapa menit (Discord perlu sync)
- Restart bot dan periksa log sinkronisasi

### Auto-detect tidak berfungsi
- Pastikan **Message Content Intent** enabled di Developer Portal
- Cek channel sudah masuk dalam config dengan `/config action:view`
- Test dengan format: `TRANSAKSI SELESAI: 1500000`

### Database error
- Pastikan folder `data/` ada dan writable
- Cek permission file `bot_database.db`
- Jika corrupt, restore dari backup dengan `/rollback_backup`

## 🔐 Security Notes

- **Jangan share file `.env`** - ini berisi token rahasia
- **Backup berkala**: Bot otomatis backup saat reset_all, tapi backup manual juga disarankan
- **Admin permissions**: Hanya kasih role admin ke user terpercaya
- **Database file**: `bot_database.db` berisi semua data - backup secara teratur

## 📈 Implemented Features

✅ **Achievement System** - Unlock badges berdasarkan milestone  
✅ **Transaction History** - Riwayat lengkap setiap transaksi  
✅ **Analytics** - Weekly/monthly stats dengan progress bar  
✅ **Leaderboard** - Ranking dengan emoji medals  
✅ **Multi-Currency** - Display IDR + USD estimasi  
✅ **Command Aliases** - Shortcut /s, /lb, /deal, /h  
✅ **Export CSV** - Export transaksi ke file  
✅ **Auto-Backup** - Backup otomatis setiap 24 jam  
✅ **Progress Bars** - Visual progress ke milestone  
✅ **Goal Setting** - Set target pribadi  

## 🚧 Future Improvements

- Web dashboard untuk admin dengan grafik real-time
- Live exchange rate API untuk multi-currency
- Grafik statistik dengan matplotlib/chart.js
- Webhook integration untuk notifikasi eksternal
- Custom achievement creation oleh admin
- Transaction categories dengan tag/label
- Scheduled reports (weekly digest)
- Data retention policies
- Advanced analytics (trends, predictions)

## 📞 Support

Jika menemukan bug atau punya pertanyaan:
1. Cek log error di terminal
2. Periksa `data/bot_database.db` ada dan bisa dibaca
3. Cek audit log dengan query SQL jika perlu debug

## 📜 License

Bebas digunakan dan dimodifikasi sesuai kebutuhan.

---

**Made with ❤️ for Discord communities**
