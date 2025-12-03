# 📋 Panduan Lengkap Railway Deployment & Troubleshooting

## 🎯 Tujuan
Panduan ini membantu Anda memastikan bot Discord sudah ter-deploy dengan benar di Railway setelah push code baru ke GitHub.

---

## ✅ Langkah 1: Cek Status Deployment di Railway

### 1. Buka Railway Dashboard
1. Buka browser (Chrome/Firefox/Edge)
2. Ketik URL: **https://railway.app**
3. Klik **"Login"** (pojok kanan atas)
4. Login dengan akun GitHub Anda

### 2. Masuk ke Project Bot Discord
1. Setelah login, Anda akan melihat **Dashboard** dengan list project
2. Cari project bot Discord Anda (contoh: "Discord-BOT" atau nama lain)
3. **Klik** project tersebut untuk masuk ke detail

### 3. Cek Status Deployment
Setelah masuk ke project, Anda akan melihat tampilan seperti ini:

```
┌─────────────────────────────────────┐
│  Discord-BOT                        │
│  ● Active  atau  ⏳ Deploying       │ ← CEK DI SINI!
└─────────────────────────────────────┘
```

**Keterangan Status:**
- ✅ **"● Active"** (hijau) → Bot sudah jalan dengan code terbaru
- ⏳ **"⏳ Deploying..."** (kuning) → Masih proses deploy (tunggu 1-2 menit)
- ❌ **"● Failed"** (merah) → Deploy gagal (perlu dicek error)
- ⏸️ **"○ Inactive"** (abu-abu) → Bot mati/tidak jalan

---

## 🔄 Langkah 2: Cek History Deployment (Opsional)

### 1. Buka Tab "Deployments"
Di halaman project, klik tab **"Deployments"** di bagian atas:

```
┌──────────────────────────────────────────┐
│  Service  Variables  Settings  Deployments │ ← KLIK TAB INI
└──────────────────────────────────────────┘
```

### 2. Lihat List Deployment Terbaru
Anda akan melihat list deployment dengan info:
- **Commit Message** (contoh: "Fix: Change leaderboard auto-update...")
- **Commit Hash** (contoh: `83dee5f`)
- **Status**: Success (✅) / Failed (❌) / Deploying (⏳)
- **Waktu**: Kapan deploy dimulai

**Yang harus dicari:**
```
✅ 83dee5f  Fix: Change leaderboard auto-update from 30min to 2hrs & fix stats...
   └─ Status: Success
   └─ 2 minutes ago
```

Jika commit terbaru Anda (83dee5f) ada di list dan status **Success**, berarti bot sudah pakai code terbaru! ✅

---

## 🔁 Langkah 3: Force Restart Bot (Jika Diperlukan)

### Kapan perlu restart?
- Status **"Deploying..."** stuck lebih dari 5 menit
- Bot sudah **"Active"** tapi masih pakai code lama
- Ada perubahan environment variable

### Cara Restart:

#### Metode 1: Restart Melalui Settings (Recommended)
1. Di halaman project, klik tab **"Settings"**
2. Scroll ke bagian bawah
3. Cari section **"Danger Zone"** atau **"Service"**
4. Klik tombol **"Restart Deployment"** atau **"Redeploy"**
5. Konfirmasi dengan klik **"Restart"**
6. Tunggu 30-60 detik
7. Cek kembali status → harus jadi **"● Active"** (hijau)

#### Metode 2: Redeploy dari Deployments Tab
1. Klik tab **"Deployments"**
2. Cari deployment yang **Success** (yang terbaru)
3. Klik icon **"⋮"** (3 titik) di samping deployment
4. Pilih **"Redeploy"**
5. Tunggu 30-60 detik

---

## 📊 Langkah 4: Cek Logs Bot (Troubleshooting)

### 1. Buka Tab Logs
Di halaman project, cari bagian **"Logs"** atau **"View Logs"**

### 2. Cari Pesan Penting
Scroll ke bawah dan cari pesan seperti:

**✅ Bot Berhasil Login:**
```
✅ Bot berhasil Login sebagai HALLO#1234 (ID: 123456789)
📡 Bot aktif di 2 server
   - BLOX (ID: 1445079009405833299)
⏳ Mencoba sinkronisasi Slash Commands...
🎉 25 Slash Commands synced globally!
```

**❌ Bot Error:**
```
❌ Gagal Login: Invalid Token
❌ Error: discord.errors.LoginFailure
```

### 3. Interpretasi Logs
- Jika ada pesan **"✅ Bot berhasil Login"** → Bot sudah online! ✅
- Jika ada **"❌ Error"** → Ada masalah (cek error message)
- Jika tidak ada log baru → Bot belum restart (coba restart manual)

---

## 🧪 Langkah 5: Test Bot di Discord

### 1. Cek Status Bot Online
1. Buka Discord
2. Cek di **Member List** (pojok kanan)
3. Cari bot Anda (contoh: **HALLO**)
4. Status harus **"🟢 Online"** (hijau)
   - Jika **"⚪ Offline"** (abu-abu) → Bot mati di Railway

### 2. Test Command `/stats`
1. Di channel Discord (contoh: #cmd-bot)
2. Ketik: `/stats`
3. Pilih user yang **belum punya data** (contoh: @Abuyy)

**Hasil yang BENAR (setelah fix):**
```
👤 Abuyy
Statistik Transaksi

📊 Total Transaksi
0 deals

💰 Total Belanja
Rp0
(≈ $0.00 USD)
```

**Hasil yang SALAH (code lama):**
```
❌ Data statistik untuk Abuyy tidak ditemukan dalam database.
```

Jika hasil **BENAR** → Fix berhasil! ✅
Jika hasil **SALAH** → Railway belum deploy code baru (ulangi Langkah 3)

---

## ⚠️ Troubleshooting Common Issues

### Issue 1: Deployment Stuck di "Deploying..."
**Solusi:**
1. Tunggu 5 menit
2. Jika masih stuck, force restart (Langkah 3)
3. Jika masih stuck, cek **Logs** untuk error

### Issue 2: Deployment Failed (❌)
**Solusi:**
1. Klik deployment yang failed
2. Baca error message di logs
3. Common errors:
   - **"Module not found"** → Ada library yang belum di-install (cek `requirements.txt`)
   - **"Invalid Token"** → Token Discord salah (cek Environment Variables)
   - **"Port already in use"** → Restart deployment

### Issue 3: Bot Online tapi Command Lama
**Penyebab:** Railway belum deploy code terbaru dari GitHub

**Solusi:**
1. Cek apakah GitHub push berhasil (git status)
2. Cek apakah Railway terhubung ke GitHub repo yang benar
3. Force redeploy (Langkah 3, Metode 2)

### Issue 4: Bot Offline di Discord
**Solusi:**
1. Cek Railway status → harus **"● Active"**
2. Cek Logs → harus ada **"✅ Bot berhasil Login"**
3. Cek Environment Variables → pastikan `DISCORD_BOT_TOKEN` benar
4. Restart deployment

---

## 🔐 Langkah 6: Cek Environment Variables (Opsional)

### 1. Buka Tab "Variables"
Di halaman project, klik tab **"Variables"**

### 2. Pastikan Variables Ini Ada:
```
DISCORD_BOT_TOKEN = NzY4OTM2NTQ4MTIz... (token panjang)
GUILD_ID = 1445079009405833299
```

### 3. Jika Ada yang Salah/Kurang:
1. Klik **"+ New Variable"**
2. Masukkan:
   - **Variable Name:** `DISCORD_BOT_TOKEN`
   - **Value:** (paste token bot dari Discord Developer Portal)
3. Klik **"Add"**
4. **Restart deployment** (Langkah 3)

---

## 📝 Checklist Setelah Push Code Baru

Setiap kali Anda push code baru ke GitHub, lakukan checklist ini:

```
□ Push code ke GitHub berhasil (git push origin main)
□ Railway status: ● Active (hijau)
□ Deployment terbaru: Success ✅
□ Logs menunjukkan: "✅ Bot berhasil Login"
□ Bot online di Discord (🟢 Online)
□ Test command berfungsi dengan benar
□ Tidak ada error di Logs
```

Jika semua ✅, deployment berhasil! 🎉

---

## 🆘 Butuh Bantuan?

Jika masih ada masalah setelah ikuti semua langkah:

1. **Screenshot:**
   - Railway status page
   - Railway logs (bagian error)
   - Discord error message

2. **Info yang dibutuhkan:**
   - Commit hash terakhir (contoh: `83dee5f`)
   - Error message dari Logs
   - Behavior bot di Discord

3. **Contact:**
   - Tanyakan di chat ini dengan screenshot lengkap
   - Sertakan hasil checklist di atas

---

## 📚 Referensi

- **Railway Docs:** https://docs.railway.app
- **Discord Bot Docs:** https://discord.com/developers/docs
- **GitHub Repo:** https://github.com/A-XZ01/Discord-BOT

---

**Dibuat:** 3 Desember 2025  
**Versi:** 1.0  
**Untuk:** Discord BOT Project - Railway Deployment
