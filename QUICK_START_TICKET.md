# 🚀 Quick Start: Ticket System

## Untuk Buyer (Pembeli)

### Method 1: Auto-Ticket (Recommended) 🔥

#### 1️⃣ Masuk Channel #open-ticket
- Cari channel bernama `#open-ticket`
- Baca instruksi di pinned message

#### 2️⃣ Ketik Username Game
```
PlayerXYZ123
```
- Ketik **hanya username game** Anda
- Minimal 3 karakter, maksimal 50 karakter
- Bot akan **otomatis** create ticket private channel
- Pesan Anda akan dihapus otomatis dalam 10 detik

#### 3️⃣ Masuk ke Ticket Channel
- Bot akan mention channel baru: `#ticket-0001`
- Klik channel tersebut
- Private channel (hanya Anda + admin + bot)

### Method 2: Command /ticket (Alternative)

#### 1️⃣ Buka Ticket
```
/ticket game_username:PlayerXYZ123
```
- Gunakan di channel manapun
- Bot akan create private channel

---

### 2️⃣ Tambah Items
```
/add item:A quantity:2
/add item:C quantity:1
```
- **Bisa order banyak item** dalam 1 ticket
- Quantity max: 100 per item
- Bot akan tampilkan grand total otomatis

### 3️⃣ Transfer Uang
```
Bank: BCA
Nomor Rekening: 6241530865
Atas Nama: Aryansyah Saputra
Jumlah: Sesuai Grand Total di ticket
```
- Transfer **PERSIS** sesuai grand total
- Screenshot bukti transfer

### 4️⃣ Submit Bukti
```
/submit proof:https://i.imgur.com/abc123.png
```
- Upload link gambar bukti transfer
- Bot akan notify admin otomatis

### 5️⃣ Tunggu Approval
- Admin review dalam <30 menit
- Jika approved: Achievement unlock + channel dihapus
- Jika rejected: Cek alasan, close ticket, buat ticket baru

### ❌ Close Ticket (Opsional)
```
/close
```
- Jika mau cancel order
- Atau sudah selesai transaksi
- Channel akan dihapus otomatis

---

## Untuk Admin

### 1️⃣ Masuk ke Ticket Channel
- Cek category **TICKETS**
- Masuk ke ticket yang ada notifikasi

### 2️⃣ Review Order
```
Ticket akan tampilkan:
- Username game buyer
- List items dengan quantity
- Grand total
- Link bukti transfer
```

### 3️⃣ Klik Link Bukti Transfer
- Validasi apakah transfer valid
- Cek nama rekening + jumlah

### 4️⃣ Approve atau Reject

**Jika VALID:**
```
/approve-ticket
```
Bot otomatis:
- ✅ Update user stats
- ✅ Add transactions ke database
- ✅ Unlock achievements (jika ada)
- ✅ Delete channel dalam 10 detik

**Jika TIDAK VALID:**
```
/reject-ticket reason:Jumlah transfer tidak sesuai
```
Bot otomatis:
- ❌ Close ticket dengan alasan
- ❌ Delete channel dalam 30 detik
- ❌ Buyer bisa buat ticket baru

---

## 💡 Tips & Tricks

### Untuk Buyer:
- **Order banyak item sekaligus** untuk hemat waktu
- **Screenshot bukti jelas** (nama rekening + jumlah visible)
- **Jangan lupa username game** saat buka ticket
- **1 buyer = 1 ticket aktif** (harus close dulu untuk buka ticket baru)

### Untuk Admin:
- **Cek category TICKETS** secara berkala
- **Validasi bukti sebelum approve** (jangan asal approve!)
- **Reject dengan alasan jelas** agar buyer tahu apa yang salah
- **Admin bisa add item juga** jika buyer request via chat

---

## 📋 Command Summary

| Role | Command | Deskripsi |
|------|---------|-----------|
| Buyer | `/ticket` | Buka ticket baru |
| Buyer | `/add` | Tambah item ke order |
| Buyer | `/submit` | Upload bukti transfer |
| Buyer | `/close` | Tutup ticket |
| Admin | `/approve-ticket` | Approve dan complete transaksi |
| Admin | `/reject-ticket` | Reject dengan alasan |
| Admin | `/close` | Close ticket manual |

---

## 🎯 Example Order Flow

### Single Item Order
```
Buyer:
/ticket game_username:Player123
/add item:A quantity:1
[Transfer Rp74.000]
/submit proof:link

Admin:
[Review proof]
/approve-ticket

Result: ✅ Done!
```

### Bulk Order
```
Buyer:
/ticket game_username:WhaleGamer
/add item:A quantity:5
/add item:B quantity:3
/add item:E quantity:2
[Grand Total: Rp1.554.000]
[Transfer Rp1.554.000]
/submit proof:link

Admin:
[Review proof - Valid ✓]
/approve-ticket

Result: ✅ Done + Achievement Unlocked!
```

### Rejected Order
```
Buyer:
/ticket game_username:Newbie001
/add item:D quantity:1
[Transfer Rp200.000] ❌ Salah jumlah!
/submit proof:link

Admin:
[Review proof - Jumlah salah!]
/reject-ticket reason:Transfer Rp200.000, seharusnya Rp296.000

Buyer:
[Terima DM reject]
/close
/ticket game_username:Newbie001
/add item:D quantity:1
[Transfer Rp296.000] ✅ Benar!
/submit proof:new_link

Admin:
[Review - Valid ✓]
/approve-ticket

Result: ✅ Done!
```

---

## ❓ FAQ

### Q: Sudah add item, bisa hapus/edit?
**A:** Tidak bisa. Jika salah, gunakan `/close` dan buat ticket baru.

### Q: Sudah punya ticket aktif, mau buka lagi?
**A:** Harus close ticket lama dulu dengan `/close`.

### Q: Lupa username game pas buka ticket?
**A:** Username tidak bisa diubah. Close ticket dan buat ticket baru dengan username yang benar.

### Q: Buyer bisa lihat ticket orang lain?
**A:** Tidak. Setiap ticket private (hanya buyer + admin + bot).

### Q: Channel ticket bisa dihapus manual?
**A:** Bisa, tapi lebih baik gunakan `/close` agar database ter-update dengan benar.

### Q: Admin bisa add item untuk buyer?
**A:** Ya, admin bisa gunakan `/add` di ticket manapun.

### Q: Bot tidak create channel?
**A:** Pastikan bot punya permission:
- Manage Channels
- Manage Roles
- Read/Send Messages

---

## 🔐 Security

- ✅ Private channels (auto permission management)
- ✅ 1 user = 1 open ticket (UNIQUE constraint)
- ✅ Admin-only approve/reject
- ✅ Validation di setiap command
- ✅ Auto-delete channel setelah selesai
- ✅ Transaction history tersimpan di database

---

**Need help?** Tag admin di server atau DM admin untuk bantuan manual.
