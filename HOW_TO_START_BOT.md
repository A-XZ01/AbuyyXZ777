# 🤖 ASBLOX Discord Bot - Cara Menjalankan (DigitalOcean + Local)

## 🛰️ Jalankan di Server (Production)
1. Push perubahan ke GitHub (`main`).
2. Jalankan **deploy.ps1** atau **deploy-simple.ps1** (otomatis git pull + `supervisorctl restart discordbot`).
3. Cek status: `ssh root@159.223.71.87` → `supervisorctl status discordbot`.
4. Logs: `tail -n 200 /var/log/discordbot.out.log`.

## 💻 Jalankan Lokal (Dev/Test)
1. Pastikan `.env` berisi `DISCORD_BOT_TOKEN` dan `GUILD_ID`.
2. Instal dependensi: `python -m pip install -r requirements.txt`.
3. Jalanan bot: `python bot.py`.
4. Stop dengan `Ctrl+C`.

## 🔧 Troubleshooting Singkat
- Token salah → bot gagal login (cek .env).
- Missing library → ulang `pip install -r requirements.txt`.
- Tidak respon di server → pastikan bot diundang dan intents aktif.

## 🔒 Catatan Penting
- Database SQLite production ada di `/root/AbuyyXZ777/data/bot_database.db` (tidak di-commit).
- Supervisor menjaga bot 24/7, tidak perlu keep-alive Flask/Procfile.
- Untuk PostgreSQL, set `DATABASE_URL` lalu restart bot.
