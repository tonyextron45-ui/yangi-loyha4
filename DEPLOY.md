# 🚀 Render (bepul) + Turso ga joylash — to'liq qo'llanma

Bot **bepul** ishlaydi va ma'lumot **hech qachon yo'qolmaydi** (Turso doimiy saqlaydi).

```
┌─────────────┐   HTTP ping    ┌──────────────────┐   libsql   ┌─────────┐
│ UptimeRobot │ ─────10 daq──▶ │  Render (bepul)   │ ─────────▶ │  Turso  │
│  (uyg'oq    │                │  bot.py + health  │            │ (baza,  │
│   ushlaydi) │ ◀───200 OK──── │  polling          │            │ doimiy) │
└─────────────┘                └──────────────────┘            └─────────┘
```

Jami 4 qadam: **① Turso → ② GitHub → ③ Render → ④ UptimeRobot**

---

## ① Turso — bepul doimiy baza

1. https://turso.tech ga kiring → **Sign up** (GitHub bilan kirish eng oson).
2. **Databases** → **Create Database**:
   - Nom: `kinobot` (ixtiyoriy)
   - Region: **Frankfurt (fra)** yoki **Amsterdam** — O'zbekiston/MDH uchun eng yaqin.
3. Baza ochilgach ikkita narsa kerak:

   **a) Database URL:** baza sahifasida `libsql://kinobot-<username>.turso.io` ko'rinishida.

   **b) Auth token:** «Create Token» / «Generate Token» tugmasi → nusxa oling
   (`eyJhbGciOi...` bilan boshlanadi).

> 💡 CLI yoqtirsangiz: `turso db create kinobot --location fra` →
> `turso db show kinobot --url` va `turso db tokens create kinobot`.

Bu ikki qiymatni saqlab qo'ying — 3-qadamda kerak bo'ladi.

**Jadvallar avtomatik yaratiladi** — Turso'da hech narsa qo'lda qilish shart emas.

---

## ② Kodni GitHub'ga joylash

Loyiha papkasida (bir marta):

```bash
git init
git add .
git commit -m "Premium Kino Bot"
```

GitHub'da yangi (private) repo yarating, so'ng:

```bash
git remote add origin https://github.com/<username>/kinobot.git
git branch -M main
git push -u origin main
```

> ✅ `.gitignore` `.env` va `*.db` ni chetlab o'tadi — **token va parol GitHub'ga chiqmaydi.**

---

## ③ Render — bepul Web Service

1. https://render.com → **Sign up** (GitHub bilan).
2. **New +** → **Blueprint** → repongizni tanlang.
   `render.yaml` avtomatik o'qiladi (plan: free, region: frankfurt).
   > Blueprint chiqmasa: **New +** → **Web Service** → repo → qo'lda:
   > Runtime `Python 3`, Build `pip install -r requirements.txt`, Start `python bot.py`, Plan **Free**.
3. **Environment** bo'limida quyidagilarni kiriting (Add Environment Variable):

   | Key | Value |
   |-----|-------|
   | `BOT_TOKEN` | BotFather bergan token |
   | `MAIN_ADMIN_ID` | Sizning Telegram ID (masalan 7114973309) |
   | `ADMIN_PASSWORD` | `090704` |
   | `TURSO_DATABASE_URL` | `libsql://kinobot-...turso.io` (①dan) |
   | `TURSO_AUTH_TOKEN` | `eyJhbGciOi...` (①dan) |

4. **Create / Deploy** → loglarda quyidagini ko'rasiz:
   ```
   🌐 Health-server tayyor: 0.0.0.0:10000
   Baza tayyor: Turso (bulut)
   🎬 @TarjimaKinoman_bot ishga tushdi
   ```
5. Xizmat manzilini nusxa oling: `https://tarjima-kinoman-bot.onrender.com`

---

## ④ UptimeRobot — botni uyg'oq ushlash (MAJBURIY!)

⚠️ Render bepul xizmat **15 daqiqa jimlikdan keyin uxlab qoladi**. Polling
rejimida uni faqat HTTP so'rov uyg'otadi (Telegram xabarlari emas!). Shu sababli
tashqi «ping» **shart** — aks holda bot uxlab qoladi va xabarlarga javob bermaydi.

1. https://uptimerobot.com → bepul ro'yxatdan o'ting.
2. **Add New Monitor**:
   - Type: **HTTP(s)**
   - URL: `https://tarjima-kinoman-bot.onrender.com/health`
   - Monitoring Interval: **5 daqiqa** (yoki 10)
3. **Create** — tamom. Bot endi 24/7 uyg'oq.

> Muqobil: https://cron-job.org ham bepul va shu ishni bajaradi.

---

## ✅ Tekshirish

1. Telegramда botga `/start` yozing → salomlashish paneli.
2. `/admin` → `090704` → 📡 Kanal sozlamalari → baza kanal qo'shing.
3. Kino qo'shing, kodni sinang.
4. **Eng muhim sinov:** Render dashboard'da **Manual Deploy** → **Clear build cache & deploy**
   qiling (qayta ishga tushirish). Bot qaytgach — **kinolar, kodlar, adminlar
   joyida qoladi** ✅ (Turso saqlagani uchun).

---

## ℹ️ Muhim eslatmalar

- **Tezlik.** Turso remote bo'lsa ham bot tez ishlaydi: adminlar, kanallar,
  sozlamalar, kontent va obuna holati xotirada keshlanadi — foydalanuvchi
  harakatlarining ko'pi bazaga UMUMAN bormaydi. Ko'rishlar 30 sekundda bitta
  so'rovda yoziladi.
- **Bepul limitlar.** Render: 750 soat/oy (bitta xizmat 24/7 ≈ 730 soat — sig'adi).
  Turso: 9 GB, 1 mlrd o'qish/oy — kino boti uchun juda yetarli.
- **Yangilanish.** Kodni o'zgartirsangiz: `git push` → Render avtomatik qayta deploy qiladi.
- **Ma'lumot ko'chirish.** Lokaldagi `kinoBaza.db` ni Turso'ga yuklash:
  `turso db shell kinobot < dump.sql` (avval `sqlite3 kinoBaza.db .dump > dump.sql`).
- **Pullik disk shart emas** — Turso bepul va doimiy.
