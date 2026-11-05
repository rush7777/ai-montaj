# AI montaj (pro)

Xom videoni tashlaysiz, Claude'ga **"montaj qil"** deysiz. Tizim:

1. nutqni so'zma-so'z vaqtlari bilan matnga aylantiradi (o'zbekcha, Whisper large-v3, lokal, bepul);
2. dublar, jimlik va "ee-mm" ni kesadi, eng kuchli gapni boshiga (hook) qo'yadi;
3. **uslub pasporti** bo'yicha ritm va zoom beradi, **yuzni avtomatik kadrlaydi**; kamera harakati
   (**punch-in**, **Ken Burns**), o'tishlar (**crossfade**, **dramatic zoom**, dip) va oxirida **qoraga fade**;
4. animatsiyali o'zbekcha subtitr yozadi (Montserrat, Bebas Neue);
5. **HyperFrames** bilan animatsiyalar qo'shadi: kinetik matn, sanovchi raqamlar, emoji, stiker, ro'yxat,
   CTA tugma, flash o'tish, progress-bar, **qo'lda chizilgan belgilar** (marker, aylana, ramka, chizib tashlash);
   **Remotion** (React) bilan murakkab sahnalar: prujinali kinetik sarlavha, split-screen qadam kartochkalari;
6. rang korreksiyasi, ovozni tozalash, **426 ta SFX** va **bitga moslangan** musiqa;
7. render qilishdan oldin **storyboard** (HTML) ko'rsatadi - siz tasdiqlaysiz yoki o'zgartirasiz;
8. o'zini **0-100 ball** bilan baholaydi (ovoz, qora kadr, ritm, subtitr yuzni yopishi) va xatoni tuzatadi.

## O'rnatish (bir marta)

Kerak: Windows, Python 3.10+, ~6 GB bo'sh joy, kamida 16 GB RAM tavsiya etiladi.

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Barcha vositalar (`FFmpeg`, `Node.js`, `HyperFrames`, `Remotion`, Whisper modeli) `%USERPROFILE%\.ai-montaj` ga o'rnatiladi -
tizimga tegmaydi, admin huquqi kerak emas, har bir fayl SHA256 bilan tekshiriladi.

## Ishlatish

1. Bu papkani Claude ilovasining **Code** bo'limida oching.
2. Videoni (yoki kliplarni) `input/` papkasiga qo'ying.
3. Yozing:
   - `input/video.mp4 ni montaj qil`
   - `input/ dagi kliplardan reklama reels qil, sotuv-reklama uslubida`
   - `input/podcast.mp4 dan 3 ta reels qil`
4. Claude avval `work/<video>/storyboard.html` ni ko'rsatadi: sahnalar eskizi, vaqtlar, gaplar, ekrandagi
   matnlar, o'tishlar. "Ha" desangiz render qiladi; *"3-sahnaga punch-in"*, *"oxirini fade bilan tugat"* deb
   o'zgartirishingiz mumkin. Storyboardsiz kerak bo'lsa: *"to'g'ridan render qil"*.
5. Tayyor video `output/` da. Tuzatishlarni oddiy so'z bilan bering: *"musiqa baland"*, *"subtitr kattaroq"*,
   *"premiumroq qil"*, *"30 soniyaga qisqartir"*.

## Uslub pasportlari

`hormozi`, `ekspert-premium`, `sotuv-reklama`, `kino`, `podcast`, `yangiliklar`, `talim`, `motivatsiya`,
`kulgili`, `premium-mahsulot`, `lifestyle`, `tiktok-trend`. Ro'yxat: `montaj/passport.py --list`.

**Yangi uslub o'rgatish**: yoqtirgan blogger videolarining havolasini bering (YouTube/TikTok) yoki videolarni
`input/reference/` ga qo'ying va ayting: *"shu uslubni o'rgan"*. Claude ularni tahlil qilib, yangi pasport yozadi.

## Musiqa va SFX

- `assets/sfx/` - 426 ta litsenziyasiz ovoz (Kenney CC0 + sintez). O'zingiznikini `assets/sfx/custom/` ga qo'ying.
- `assets/music/` - **o'zingiz** qo'yasiz (masalan YouTube Audio Library). Tizim tempini aniqlab, kesimlarni bitga moslaydi.

## Repo tuzilishi

| Papka | Nima | Git'da |
|---|---|---|
| `montaj/` | Python skriptlar | ha |
| `remotion/` | Remotion (React) sahnalari | ha |
| `styles/` | subtitr uslublari, uslub pasportlari | ha |
| `.claude/skills/montaj/` | Claude uchun montaj ish tartibi | ha |
| `assets/fonts/`, `assets/sfx/` | shriftlar (OFL), SFX (CC0 + sintez) | ha |
| `assets/music/` | musiqa (faqat `LITSENZIYA.txt` repoda, mp3'larni o'zingiz qo'yasiz) | yo'q |
| `input/`, `output/`, `work/` | xom videolar, tayyor videolar, oraliq fayllar | yo'q |

Boshqa kompyuterda tiklash: `git clone https://github.com/rush7777/ai-montaj.git`, keyin `setup.ps1`.

## Litsenziyalar

Kenney ovozlari - CC0. Montserrat va Bebas Neue - SIL Open Font License. HyperFrames - Apache-2.0.
Remotion - shaxslar va 3 kishigacha jamoalar uchun bepul; kattaroq kompaniyalar uchun pullik litsenziya (remotion.pro).
