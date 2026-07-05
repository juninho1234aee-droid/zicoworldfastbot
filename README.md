# ZicoWorldFast — eFootball Turnir Boti

Bu papkada botning to'liq kodi bor. Pastda **0 dan boshlab** hammasini qanday ishga
tushirish yozilgan. Ketma-ket, hech narsani tashlab ketmasdan bajaring.

---

## 0-QADAM: Muhim tushuntirish (HTML haqida)

Siz "html" ham so'ragan edingiz. Lekin sizga kerak bo'lgan narsa (bot ochilganda
rasm + tugmalar, admin panel, ro'yxatdan o'tish va h.k.) — bularning barchasi
oddiy Telegram bot xabarlari va tugmalari orqali ishlaydi, **alohida HTML sahifa
kerak emas**. "Ilovani ochish" nomi va rasm — bu botning profilida BotFather
orqali o'rnatiladigan nom/rasm, pastda shu haqida ham yozilgan.

Agar kelajakda haqiqiy "Mini App" (brauzer ichida ochiladigan maxsus dizaynli
sahifa) kerak bo'lsa — bu alohida, kattaroq loyiha bo'ladi, xohlasangiz keyin
alohida qilamiz.

---

## 1-QADAM: Kerakli dasturlarni o'rnatish

Kompyuteringizda (Windows/Mac/Linux) quyidagilar kerak:

1. **Python** (3.11 yoki undan yuqori) — https://www.python.org/downloads/
   O'rnatishda "Add Python to PATH" katagichini albatta belgilang.
2. **Git** — https://git-scm.com/downloads
3. **GitHub** akkaunti — https://github.com
4. **Supabase** akkaunti — https://supabase.com
5. **Railway** akkaunti — https://railway.app

---

## 2-QADAM: Supabase'ni sozlash (baza)

1. https://supabase.com ga kiring → **New Project**
2. Loyihaga nom bering (masalan `zicoworldfast`), parol o'rnating, region tanlang → **Create**
3. Loyiha tayyor bo'lgach, chap menyudan **SQL Editor** ga o'ting
4. **New query** tugmasini bosing
5. `schema.sql` faylidagi butun kodni nusxalab shu yerga joylashtiring va **Run** bosing
   — bu jadvallarni (users, tournaments, participants, matches, settings) yaratadi
6. Chap menyudan **Project Settings → API** ga o'ting:
   - **Project URL** — bu `SUPABASE_URL`
   - **service_role key** (yoki `anon` key) — bu `SUPABASE_KEY`
   - Ikkalasini alohida joyga saqlab qo'ying, keyin kerak bo'ladi

---

## 3-QADAM: BotFather'da botni sozlash

1. Telegramda **@BotFather** ga yozing
2. **Yangi token oling** (eski tokenni yuqorida aytganimdek revoke qilgan bo'lsangiz):
   `/mybots` → botingiz → **API Token**
3. Bot nomi va rasmini o'rnating:
   - `/setname` — botga "ZicoWorldFast" nomini bering
   - `/setuserpic` — sariq kubok rasmini yuklang
   - `/setdescription` — botingiz haqida qisqa tavsif yozing
4. O'zingizning Telegram ID raqamingizni bilib oling: Telegramda **@userinfobot** ga
   `/start` yozing, u sizga ID raqamingizni beradi (masalan `123456789`) — bu `ADMIN_ID`

---

## 4-QADAM: Kodni kompyuterga tayyorlash

1. Ushbu papkani (`zicoworldfast_bot`) kompyuteringizga yuklab oling
2. Papka ichiga o'zingizning sariq kubok rasmingizni qo'ying va nomini
   **trophy.jpg** deb o'zgartiring (agar rasm bo'lmasa ham bot ishlayveradi, faqat
   rasmsiz xabar yuboradi)
3. `.env.example` faylidan nusxa oling va nomini `.env` ga o'zgartiring, ichiga
   haqiqiy qiymatlarni yozing:

```
BOT_TOKEN=yangi_tokeningiz
ADMIN_ID=123456789
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=sizning_key
```

**MUHIM:** `.env` faylni hech qachon GitHub'ga yuklamang (u avtomatik
`.gitignore` orqali chetlab o'tiladi, tashvishlanmang).

---

## 5-QADAM: Terminalda botni lokal test qilish

Terminal (Windows'da **CMD** yoki **PowerShell**, Mac/Linux'da **Terminal**) oching
va quyidagilarni birma-bir yozing:

```bash
cd papka_yoli/zicoworldfast_bot
```
(`papka_yoli` o'rniga papkani qayerga joylashtirgan bo'lsangiz o'sha yo'lni yozing)

```bash
python -m venv venv
```

Virtual muhitni faollashtiring:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

Kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```

Botni ishga tushiring:
```bash
python bot.py
```

Agar hammasi to'g'ri bo'lsa, terminalda "Bot ishga tushdi..." yozuvi chiqadi.
Endi Telegram'da botingizga `/start` yozib sinab ko'ring. `Ctrl+C` bosib
terminaldagi botni to'xtatishingiz mumkin (lokal test tugagach).

---

## 6-QADAM: Kodni GitHub'ga yuklash

Terminalda (`zicoworldfast_bot` papkasida turib):

```bash
git init
git add .
git commit -m "ZicoWorldFast bot - birinchi versiya"
```

GitHub saytida yangi repository yarating (masalan nomi `zicoworldfast-bot`,
**Private** qilib qo'ying — chunki ichida token bo'lmasa ham baza ma'lumotlari
bilan bog'liq loyiha). Repository yaratilgach, GitHub sizga buyruqlar beradi,
odatda quyidagicha:

```bash
git remote add origin https://github.com/FOYDALANUVCHI_NOM/zicoworldfast-bot.git
git branch -M main
git push -u origin main
```

---

## 7-QADAM: Railway'ga ulash (24/7 ishlashi uchun)

1. https://railway.app ga kiring, GitHub akkauntingiz bilan kiring
2. **New Project → Deploy from GitHub repo** ni tanlang
3. GitHub'ga ruxsat bering, keyin `zicoworldfast-bot` repositoriyangizni tanlang
4. Railway avtomatik loyihani aniqlaydi. **Variables** bo'limiga o'ting va
   quyidagi 4 ta o'zgaruvchini qo'shing (xuddi `.env` dagidek):
   - `BOT_TOKEN`
   - `ADMIN_ID`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
5. **Settings** bo'limida **Start Command** ni tekshiring — `python bot.py`
   bo'lishi kerak (Procfile orqali avtomatik aniqlanadi, lekin tekshirib qo'ying)
6. **Deploy** tugmasini bosing — Railway loyihani qurib, ishga tushiradi
7. **Deployments → View Logs** orqali botingiz ishga tushganini tekshiring
   ("Bot ishga tushdi..." yozuvini ko'rishingiz kerak)

Shu bilan bot 24/7 ishlaydi — kompyuteringizni o'chirsangiz ham bot Railway
serverida ishlashda davom etadi.

---

## 8-QADAM: Botni sinab ko'rish

1. Telegramda botga `/start` yozing — sariq kubok rasmi + tugmalar chiqadi
2. Admin akkauntingiz bilan **⚙️ Admin panel** tugmasini bosing
3. **▶️ 32 talik turnir boshlash** ni bosing, muddatni soatlarda kiriting
   (masalan `2`)
4. Bot barcha foydalanuvchilarga ro'yxatdan o'tish tugmasi bilan xabar yuboradi
5. Foydalanuvchilar **✅ Ro'yxatdan o'tish** tugmasini bosishi bilan yuqorida
   yashil "✅ Ro'yxatdan o'tdingiz!" degan xabar chiqadi va tugma o'sha
   foydalanuvchi uchun o'chadi
6. Belgilangan muddat tugagach, bot **avtomatik** ravishda qura tashlab,
   har bir ishtirokchiga o'z raqibini @username bilan va "✉️ Raqibga yozish"
   tugmasi bilan yuboradi (bosilganda raqibning shaxsiy chatiga o'tadi)
7. **⏹ Turnirni to'xtatish** — istalgan vaqtda joriy turnirni bekor qiladi
8. **🟢/🔴 Texnik ishlar** tugmasi — yoqilganda, admin'dan boshqa hech kim
   turnir bo'limiga kira olmaydi, "texnik ishlar" xabarini ko'radi

---

## Botning imkoniyatlari (qisqacha)

- `/start` — sariq kubok rasmi bilan bosh menyu
- 🏆 Asosiy turnir — faol turnir holati, ro'yxatdan o'tish, raqib ma'lumoti
- 👤 Profil — o'z holatingiz va raqibingiz
- 📜 Qoidalar — Match Nastroyka 8 daqiqa ✅, Extra Time ✅, Penalti ✅,
  Kayfiyat: Excellent ✅
- ⚙️ Admin panel (faqat sizga ko'rinadi):
  - Umumiy foydalanuvchilar soni
  - Faol qatnashuvchilar soni
  - Texnik ishlar ON/OFF
  - 32 talik / 128 talik turnir boshlash (muddat bilan)
  - Turnirni to'xtatish
- Avtomatik qura tashlash — muddat tugagach bot o'zi raqiblarni tanlaydi
- Har ikki o'yinchi ham bir-birining @username'ini ko'radi va "Raqibga yozish"
  tugmasi orqali to'g'ridan-to'g'ri lichkaga o'tadi — hammasi xolis va tasodifiy

---

## Xavfsizlik bo'yicha eslatmalar

- `.env` faylni hech qachon hech kimga yubormang, GitHub'ga yuklamang
- Token oshkor bo'lib qolsa, darhol BotFather orqali "Revoke" qiling va yangisini oling
- Supabase'da **service_role key**ni faqat serverda (Railway Variables) ishlating,
  uni frontendga yoki ochiq joyga qo'ymang
- `ADMIN_ID` faqat sizning shaxsiy Telegram ID raqamingiz bo'lishi kerak — shu
  orqali admin panel faqat sizga ko'rinadi
