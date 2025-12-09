# 🎫 Ticket System Documentation

## Overview

Sistem ticket untuk buyer order item dengan private channel. Setiap buyer hanya bisa punya 1 ticket aktif, dan bisa order multiple items dalam 1 ticket. Admin/Owner approve dalam ticket channel.

## 🔄 Workflow

### Buyer Workflow:

**Method 1: Auto-Ticket (Recommended)**
1. **Masuk #open-ticket** channel
2. **Ketik username game** Anda (contoh: `PlayerXYZ123`)
3. **Bot auto-create** private ticket channel
4. **Masuk ticket channel** dan gunakan `/add` untuk order
5. **Submit proof** dengan `/submit`
6. **Wait for approval**

**Method 2: Manual Command**
1. **Open Ticket** - `/ticket game_username:PlayerXYZ123`
   - Bot create private channel (contoh: `ticket-0001`)
   - Hanya buyer, admin, dan bot yang bisa lihat channel
   - Channel ada di category "TICKETS"

2. **Add Items** - `/add item:A quantity:2`
   - Buyer tambah item ke order
   - Bisa add multiple items berbeda
   - Bot tampilkan ringkasan order + grand total

3. **Submit Proof** - `/submit proof:https://imgur.com/abc.png`
   - Upload bukti transfer setelah order selesai
   - Bot notify admin dengan embed lengkap

4. **Wait for Review**
   - Admin review bukti transfer
   - Jika valid, transaksi diproses manual lalu ticket ditutup
   - Jika tidak valid, admin reject → buyer bisa close ticket dan buat ticket baru

5. **Close Ticket** - `/close`
   - Ticket ditutup dan channel dihapus otomatis
   - Atau admin yang close

### Admin Workflow:

1. **Review Ticket**
   - Masuk ke ticket channel
   - Lihat ringkasan order + bukti transfer

2. **Reject** - `/reject-ticket reason:Jumlah tidak sesuai`
   - Ticket ditutup dengan alasan
   - Channel dihapus dalam 30 detik

3. **Close** - `/close`
   - Tutup ticket setelah transaksi selesai

## 📋 Commands

### Buyer Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/ticket` | Buka ticket baru | `/ticket game_username:PlayerXYZ123` |
| `/add` | Tambah item ke ticket | `/add item:A quantity:2` |
| `/submit` | Submit bukti transfer | `/submit proof:https://i.imgur.com/abc.png` |
| `/close` | Tutup ticket | `/close` |

### Admin Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/reject-ticket` | Reject transaksi dengan alasan | `/reject-ticket reason:Invalid proof` |
| `/close` | Tutup ticket manual | `/close` |
| `/add` | Admin bisa add item juga (optional) | `/add item:B quantity:1` |

## 🎯 Features

### ✅ Automated
- Private channel creation per ticket
- Permission management (buyer + admin only)
- Order tracking dengan multiple items
- Grand total calculation
- Transaction auto-complete saat approve
- Achievement auto-unlock
- Channel auto-delete setelah close
- Ticket numbering otomatis (0001, 0002, etc.)

### ⚠️ Manual
- Bukti transfer validation by admin
- Approve/reject decision

## 🔒 Limitations

- **1 ticket per buyer**: User hanya bisa punya 1 ticket aktif
- **Open ticket only**: Tidak bisa edit ticket yang sudah closed
- **Admin permission required**: Hanya admin yang bisa approve/reject
- **No ticket history**: Setelah close, ticket terhapus (tapi transaksi tersimpan di database)

## 💡 Item Prices

| Item | Unit Price | Example Order |
|------|------------|---------------|
| Item A | Rp74.000 | `/add item:A quantity:2` = Rp148.000 |
| Item B | Rp148.000 | `/add item:B quantity:1` = Rp148.000 |
| Item C | Rp222.000 | `/add item:C quantity:3` = Rp666.000 |
| Item D | Rp296.000 | `/add item:D quantity:1` = Rp296.000 |
| Item E | Rp370.000 | `/add item:E quantity:5` = Rp1.850.000 |

## 💳 Payment Info

**Pembayaran QRIS:**
```
Admin akan memberikan QRIS di ticket Anda
```

Buyer bayar **Grand Total** yang tertera di ticket.

## 📊 Database Schema

### `tickets` Table
```sql
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    ticket_number INTEGER NOT NULL,
    game_username TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    closed_by TEXT,
    UNIQUE(guild_id, user_id, status)
)
```

**UNIQUE constraint**: Satu user hanya bisa punya 1 ticket dengan status `open` per guild.

### `ticket_items` Table
```sql
CREATE TABLE ticket_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    amount INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
)
```

## 🎨 Example Scenario

### Buyer Side:
```
1. /ticket game_username:GamerPro456
   → Bot create #ticket-0001

2. /add item:A quantity:3
   → Item A x3 = Rp222.000

3. /add item:C quantity:1
   → Item C x1 = Rp222.000
   → Grand Total: Rp444.000

4. Transfer Rp444.000 to BCA

5. /submit proof:https://i.imgur.com/proof123.png
   → Bot notify admin

6. Wait...

7. Admin proses manual → Channel ditutup setelah selesai
```

### Admin Side:
```
1. Masuk #ticket-0001
2. Review order:
   - GamerPro456
   - Item A x3 = Rp222.000
   - Item C x1 = Rp222.000
   - Grand Total: Rp444.000
   - Proof: [Lihat Bukti]

3. Klik link proof → Valid ✓

4. Admin proses manual
   → Gunakan `/close` setelah transaksi selesai
```

## ❓ FAQ

### Q: Bisa order banyak item sekaligus?
**A:** Ya! Gunakan `/add` berkali-kali untuk order multiple items.

### Q: Bisa edit item yang sudah di-add?
**A:** Tidak bisa edit/remove. Jika salah, close ticket dan buat ticket baru.

### Q: Sudah ada ticket tapi mau order lagi?
**A:** Harus close ticket lama dulu dengan `/close`, baru bisa buat ticket baru.

### Q: Lupa close ticket?
**A:** Admin bisa close dengan `/close` atau buyer bisa close sendiri.

### Q: Channel ticket bisa dihapus manual?
**A:** Bisa, tapi lebih baik gunakan `/close` agar database ter-update dengan benar.

### Q: Buyer bisa lihat ticket orang lain?
**A:** Tidak. Setiap ticket adalah private channel (hanya buyer, admin, dan bot).

### Q: Admin bisa add item untuk buyer?
**A:** Ya, admin punya permission untuk add item di ticket manapun.

## 🔐 Security

- ✅ Private channels (hanya buyer + admin + bot)
- ✅ UNIQUE constraint: 1 user = 1 open ticket
- ✅ Permission validation di setiap command
- ✅ Admin-only approve/reject
- ✅ Audit log untuk create/close ticket
- ✅ Transaction history tersimpan di database

## 🚀 Benefits vs Old System

### Old System (/buy + /confirm):
- ❌ DM-based (bisa terlewat)
- ❌ 1 item per payment request
- ❌ Manual tracking di multiple DMs
- ❌ Admin harus cek `/pending` di channel

### New System (Ticket):
- ✅ Private channel (lebih organized)
- ✅ Multiple items per ticket
- ✅ Real-time chat dengan admin
- ✅ All-in-one: order + proof + approve dalam 1 channel
- ✅ Auto-delete setelah selesai (clean)

## 🎯 Use Cases

### Single Item Order:
```
/ticket game_username:Player123
/add item:A quantity:1
/submit proof:link
→ Admin approve → Done
```

### Bulk Order:
```
/ticket game_username:Whale999
/add item:A quantity:10
/add item:B quantity:5
/add item:E quantity:2
/submit proof:link
→ Grand Total: Rp1.480.000
→ Admin approve → Done
```

### Rejected Order:
```
/ticket game_username:Newbie001
/add item:D quantity:1
/submit proof:invalid_link
→ Admin reject: "Bukti tidak valid"
→ Channel deleted
→ Buyer buat ticket baru dengan proof yang benar
```

---

**Made with ❤️ for organized sales workflow**
