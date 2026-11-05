# TZ: AI montaj loyihasini GitHub'ga yuklash

Sana: 2026-11-05 · Loyiha: `Documents\Montajchi\ai-montaj`

## 1. Maqsad

Shu kungacha qilingan ishlarni (montaj tizimining kodi, uslublar, Remotion sahnalari, Claude skilli, o'rnatish
skripti) GitHub repozitoriyasiga yuklash. Natijada:

- loyiha zaxira nusxada saqlanadi (kompyuter buzilsa ham yo'qolmaydi);
- har bir o'zgarish tarixi qoladi, xohlagan versiyaga qaytish mumkin;
- boshqa kompyuterda `git clone` + `setup.ps1` bilan tizimni qayta tiklash mumkin.

## 2. Hozirgi holat (tekshirildi)

| Narsa | Holat |
|---|---|
| Papkaning umumiy hajmi | ~1.5 GB, shundan kod va sozlamalar ~0.3 MB |
| Git | **o'rnatilmagan** |
| GitHub CLI (`gh`) | **o'rnatilmagan** |
| Maxfiy kalitlar (API key, token, parol) | kodda **topilmadi** |
| 100 MB dan katta fayllar | 3 ta video: `input/reels.mp4` (533 MB), `input/video02.mp4` (176 MB), `input/video01.mp4` (109 MB) |

GitHub bitta faylni 100 MB dan ortiq qabul qilmaydi, shuning uchun videolar oddiy repoga sig'maydi.

## 3. Nima yuklanadi, nima yuklanmaydi

### Yuklanadi (~9 MB)

| Yo'l | Nima |
|---|---|
| `montaj/` | 15 ta Python skript (transkripsiya, kesish, render, storyboard, baholash, Remotion qatlami...) |
| `remotion/` | React sahnalari: `TitleCard`, `StepCard`, `Root`, `fonts.js` |
| `styles/` | subtitr uslublari, 12 ta uslub pasporti, o'rganilgan pasportlar |
| `.claude/skills/montaj/SKILL.md` | Claude uchun to'liq montaj ish tartibi |
| `CLAUDE.md`, `README.md`, `requirements.txt`, `setup.ps1` | hujjatlar va o'rnatish |
| `assets/fonts/` | Montserrat, Bebas Neue + litsenziya fayllari (OFL tarqatishga ruxsat beradi) |
| `assets/sfx/` | Kenney (CC0) + sintez SFX, `catalog.json` (~7 MB) |
| `assets/music/LITSENZIYA.txt` | musiqa manbalari ro'yxati (faylning o'zi emas) |

### Yuklanmaydi

| Yo'l | Sabab |
|---|---|
| `input/` (videolar, referenslar) | juda katta; shaxsiy kadrlar (yuzingiz, xonangiz) |
| `output/` (tayyor reels) | katta; tayyor videolar Instagram/Drive'da saqlanadi |
| `work/` (oraliq fayllar, kadrlar, transkriptlar) | ~500 MB, qayta yaratsa bo'ladi; shaxsiy matnlar bor |
| `assets/music/*.mp3` | Mixkit litsenziyasi musiqani videodan alohida qayta tarqatishga ruxsat bermaydi |
| `%USERPROFILE%\.ai-montaj\` | Whisper modeli, FFmpeg, Node - `setup.ps1` o'zi yuklab oladi |
| `1_Isxodniklar` va boshqa yorliqlar | ular `ai-montaj` dan tashqarida, repoga kirmaydi |

## 4. `.gitignore`

```gitignore
# Videolar va oraliq fayllar
input/
output/
work/

# Musiqa fayllari (litsenziya qayta tarqatishga ruxsat bermaydi)
assets/music/*.mp3
assets/music/*.wav
assets/music/*.beats.json

# Foydalanuvchining shaxsiy SFX'lari
assets/sfx/custom/

# Python / Node
__pycache__/
*.pyc
.venv/
node_modules/

# Tizim fayllari
Thumbs.db
desktop.ini
.DS_Store
```

Bo'sh papkalar (`input/`, `input/reference/`, `output/`, `work/`, `assets/music/`) klonlangandan keyin ham bo'lishi
uchun ichiga `.gitkeep` qo'yiladi va `.gitignore` da istisno qilinadi.

## 5. Ish bosqichlari

| # | Bosqich | Kim bajaradi |
|---|---|---|
| 1 | Git'ni o'rnatish (`winget install Git.Git`) | Claude, sizning ruxsatingiz bilan |
| 2 | Repo yaratish: `github.com/rush7777/ai-montaj`, yopiq | **Siz** (bajarildi) |
| 3 | GitHub'ga kirish: birinchi push'da Git Credential Manager brauzer oynasini ochadi, siz tasdiqlaysiz | **Siz** (parolni Claude kiritmaydi) |
| 4 | `.gitignore`, `.gitkeep`, Bebas Neue litsenziya fayli, README'ga "Repo tuzilishi" bo'limi | Claude |
| 5 | `git init`, ism va email sozlash, birinchi commit | Claude |
| 6 | Commit'dan oldin tekshiruv: 50 MB dan katta fayl yo'q, maxfiy kalit yo'q, video yo'q | Claude |
| 7 | `git push` | Claude |
| 8 | Toza papkaga `git clone` qilib, fayllar to'liqligini tekshirish | Claude |

## 6. Qabul mezonlari

- GitHub'dagi repo hajmi 20 MB dan kichik.
- Repoda birorta ham `.mp4`, `.mov` yoki `.mp3` fayl yo'q.
- Maxfiy kalit yoki parol yo'q.
- Klonlangan nusxada `montaj/`, `remotion/`, `styles/`, `.claude/skills/`, `setup.ps1` to'liq.
- README'da o'rnatish va ishlatish tartibi bor.

## 7. Keyingi ishlar uchun tartib

Har bir katta ish tugagach (yangi funksiya, yangi uslub pasporti, xato tuzatish) Claude commit qiladi va push
qiladi. Commit xabari o'zbekcha, qisqa: masalan `Remotion: StepCard sahnasi qo'shildi`.

## 8. Qarorlar

Hal qilingan:

1. **Repo turi:** yopiq (private).
2. **Repo:** `https://github.com/rush7777/ai-montaj.git` (akkaunt `rush7777`).

Ochiq qolgan:

1. **Commit'dagi email:** ochiq repoda email hammaga ko'rinadi. GitHub'ning yashirin `...@users.noreply.github.com`
   manzilini ishlatish tavsiya etiladi.
2. **Videolar zaxirasi:** videolarni ham saqlash kerak bo'lsa, ular uchun Google Drive tavsiya etiladi (GitHub'ga
   sig'maydi).
