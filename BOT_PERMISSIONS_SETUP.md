# 🔐 Bot Permissions Setup Guide

## Required Permissions untuk Ticket System

Bot memerlukan permissions berikut untuk ticket system berfungsi dengan baik:

### ✅ Required Permissions:
- **Manage Channels** - Untuk create/delete ticket channels
- **Manage Roles** - Untuk set channel permissions
- **Read Messages/View Channels** - Untuk lihat channels
- **Send Messages** - Untuk kirim pesan di ticket
- **Embed Links** - Untuk kirim embed messages
- **Attach Files** - Untuk kirim attachments (optional)
- **Read Message History** - Untuk baca history chat
- **Add Reactions** - Untuk add reactions (optional)

## 📝 Step-by-Step Setup

### Method 1: Setup Bot Role (Recommended)

1. **Buka Server Settings**
   - Right-click server name → Server Settings

2. **Masuk ke Roles**
   - Sidebar kiri → Roles

3. **Pilih Bot Role**
   - Cari role bot Anda (biasanya nama sama dengan bot)
   - Atau create new role untuk bot

4. **Enable Permissions**
   - Scroll ke bagian "General Permissions"
   - Enable:
     - ✅ Manage Channels
     - ✅ Manage Roles
   - Scroll ke bagian "Text Permissions"
   - Enable:
     - ✅ Send Messages
     - ✅ Embed Links
     - ✅ Attach Files
     - ✅ Read Message History
     - ✅ Add Reactions

5. **Drag Role Position**
   - Drag bot role **di atas** role user biasa
   - Ini penting agar bot bisa manage permissions user

6. **Save Changes**
   - Klik "Save Changes" di bawah

### Method 2: Manual Category Setup (Alternative)

Jika tidak bisa kasih bot permission `Manage Channels`:

1. **Buat Category Manual**
   - Right-click di sidebar server
   - Create Category
   - Nama: `TICKETS`

2. **Set Category Permissions**
   - Right-click category TICKETS → Edit Category
   - Tab Permissions
   - Add bot role
   - Enable semua permissions untuk bot

3. **Test /ticket**
   - Bot sekarang bisa create channels di category TICKETS

## 🧪 Test Bot Permissions

Setelah setup, test dengan command:

```
/ticket game_username:TestUser123
```

### ✅ Jika Berhasil:
- Bot create category "TICKETS" (jika belum ada)
- Bot create channel #ticket-0001
- Channel private (hanya buyer + admin + bot)
- Welcome message muncul

### ❌ Jika Error:

**Error: "Bot tidak punya permission untuk membuat category"**
- Solution: Enable `Manage Channels` di bot role
- Atau buat category `TICKETS` manual

**Error: "Bot tidak punya permission untuk membuat channel"**
- Solution: Enable `Manage Channels` + `Manage Roles`
- Pastikan bot role di atas role user

**Error: "Missing Access"**
- Solution: Enable `Read Messages` di bot role

## 📋 Checklist Setup

- [ ] Bot role memiliki `Manage Channels` permission
- [ ] Bot role memiliki `Manage Roles` permission
- [ ] Bot role memiliki `Send Messages` permission
- [ ] Bot role memiliki `Embed Links` permission
- [ ] Bot role position di atas role user
- [ ] Category `TICKETS` sudah ada (atau bot bisa create)
- [ ] Test `/ticket` berhasil create channel

## 🎯 Invite Link dengan Permissions

Jika invite bot ke server baru, gunakan link dengan permissions:

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=268528720&scope=bot%20applications.commands
```

**Permissions value `268528720` includes:**
- Manage Channels
- Manage Roles
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions

Ganti `YOUR_BOT_ID` dengan bot client ID dari Discord Developer Portal.

## 🔧 Troubleshooting

### Bot create channel tapi permission salah?
**Solution:** Bot role harus di atas role user di hierarchy. Drag bot role ke atas.

### Category TICKETS tidak muncul?
**Solution:** Bot sudah create, tapi Anda mungkin perlu scroll atau refresh Discord.

### Channel ticket tidak private?
**Solution:** Bot perlu `Manage Roles` permission untuk set channel permissions.

### Bot tidak bisa delete channel?
**Solution:** Enable `Manage Channels` permission.

---

**Need more help?** Check bot logs atau hubungi developer.
