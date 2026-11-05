---
name: montaj
description: Xom videoni professional darajada AI bilan montaj qiladi - dublar va jimlikni kesadi, uslub pasporti bo'yicha ritm va zoom beradi, punch-in/Ken Burns harakati, crossfade/zoom o'tishlar va fade qo'yadi, yuzni avtomatik kadrlaydi, render oldidan storyboard ko'rsatadi, o'zbekcha animatsiyali subtitr, HyperFrames animatsiyalari (kinetik matn, raqam sanovchi, emoji, CTA, flash), rang korreksiyasi, 426 ta SFX va bitga moslangan musiqa qo'shadi, so'ng o'zini 0-100 ballga baholab tekshiradi. Foydalanuvchi "montaj qil", "reels qil", "subtitr qo'y", "videoni kes", "uslubini o'rgan", "edit this video" desa yoki tayyor montajga tuzatish bersa ("musiqa baland", "subtitr kattaroq", "qisqartir") ishlatiladi.
---

# AI montaj tizimi (pro)

Sen bu loyihada **montaj rejissyori**san. Videoni "chizmaysan": skriptlar orqali transkript olasan, `edit.json`
montaj rejasini yozasan, HyperFrames va FFmpeg bilan render qilasan. Buyruqlar loyiha ildizidan PowerShell'da:

```powershell
$py = "$env:USERPROFILE\.ai-montaj\venv\Scripts\python.exe"
```
Bu fayl yoki `%USERPROFILE%\.ai-montaj\{ffmpeg,node,hf,models}` yo'q bo'lsa - `powershell -ExecutionPolicy Bypass -File setup.ps1`.

| Skript | Vazifasi |
|---|---|
| `transcribe.py` | nutq -> so'zma-so'z vaqtli matn (Whisper large-v3, o'zbekcha) |
| `words.py` | transkriptni tuzatish uchun so'zlar ro'yxati, shubhalilari "!" bilan |
| `autocut.py` | jimlik va "ee-mm" ni kesib, boshlang'ich `edit.json` |
| `passport.py` | uslub pasporti: ritm, zoom, subtitr, rang, SFX palitrasi, yo'riqnoma |
| `reframe.py` | yuzni topib kadrni avtomatik moslash (pasport buni o'zi chaqiradi) |
| `storyboard.py` | render oldidan reja: sahna eskizlari (harakat, rang, animatsiya bilan) + ogohlantirishlar -> HTML |
| `render.py` | yig'ish; `--timeline-only` - tayyor videodagi vaqtlar; `--preview` - tez |
| `animate.py` | HyperFrames animatsiya qatlami (render o'zi chaqiradi); `--snapshot` - kadrlarni oldindan ko'rish |
| `remotion_layer.py` | Remotion qatlami: `"type": "remotion"` bloklari -> shaffof klip (render va storyboard o'zi chaqiradi); `--still KOMP SONIYA '{props}'` - bitta kadr |
| `sfx_catalog.py` | 426 ta SFX'dan teg bo'yicha qidirish |
| `beats.py` | musiqa tempi va bitlari |
| `review.py` | kadrlar jadvali va `--score` - 0-100 ball |
| `reference.py` | namuna videodan uslubni o'rganish |

## Ish tartibi

### 1. Videoni aniqlash
Video `input/` da yoki foydalanuvchi ko'rsatgan yo'lda. **Bir nechta klip** (C0001.MP4, C0002.MP4...) bo'lsa -
nom tartibida sifat yo'qotmasdan ula (`-f concat -c copy`, `work/clips.txt` orqali) va har klipning
umumiy videodagi boshlanish vaqtini (offset) yozib qo'y. Format standarti: 9:16.

### 2. Transkripsiya
```powershell
& $py montaj/transcribe.py input/VIDEO.mp4
```
- 45 s video taxminan 2-4 daqiqa. Uzoq ishni fonda ishga tushir.
- **VAD standart holatda o'chiq** (shevali nutqni kesib tashlaydi). Uzun pauzalarda gallyutsinatsiya bo'lsa
  ("1, 2, 3..." sanoq, takroriy gap) - `--vad`.
- `--prompt` ga **faqat bir nechta so'z** (ismlar, brend). Uzun gap transkriptga ko'chib qoladi.
- Dublar bo'lsa yoki biror qism tushib qolsa / bitta so'z 1.5 s dan uzun bo'lsa - kerakli klipni **alohida**
  transkripsiya qil (`--out work/clips/C0002`), vaqtlarga klip offsetini qo'shib umumiy transkriptga yoz.

### 3. Transkriptni tuzatish (MUHIM)
```powershell
& $py montaj/words.py work/VIDEO/transcript.json
```
`word` matnlarini **adabiy o'zbekchaga** tuzat: imlo (o', g', sh, ch), sheva (bar -> bor), brend nomlari.
Bo'lingan so'zlarni birlashtir ("shunca"+"ki" -> "shunchaki", vaqt: birinchining boshi - oxirgisining oxiri).
Asl faylni `transcript_raw.json` qilib saqla. Ishonching komil bo'lmagan raqam/ism/summalarni foydalanuvchiga
ayt va tasdiqlat - subtitr va animatsiyalar shu so'zlardan yasaladi.

### 4. Kesish va rejissyorlik
```powershell
& $py montaj/autocut.py work/VIDEO/transcript.json --format 9:16
```
`edit.json` dagi `segments` ni tahrirla:
- **Dublar**: bir gap qayta aytilgan bo'lsa - oxirgi/yaxshisini qoldir. Chalg'ish, "qancha sekund?" - o'chir.
- **Hook**: eng kuchli gap (raqam, va'da, og'riqli savol) birinchi bo'lsin; kerak bo'lsa bo'lakni boshiga ko'chir.
- Reels uchun 15-60 s. Bo'laklar bir-birini qoplamasin.

**Kamera harakati va o'tishlar** (bo'lak maydonlari; vaqtlar bo'lak boshidan, soniyada):

| Maydon | Qiymat | Qachon |
|---|---|---|
| `move` punch-in | `{"type": "punch", "at": 1.0, "to": 1.22, "in": 0.2, "hold": 1.2, "out": 0.3}` (`hold` yo'q - bo'lak oxirigacha turadi) | urg'uli so'z/raqam aytilgan lahza; 10 s ga 1-2 ta |
| `move` Ken Burns | `{"type": "kenburns", "from": 1.0, "to": 1.08, "pan": [0.03, 0], "ease": "linear"}` | 4 s+ uzun bo'lak, sokin hikoya, rasm/B-roll; zoom-out: `from` 1.1, `to` 1.0 |
| `move.anchor` | `[0.5, 0.35]` (standart - reframe yuzni shu nuqtaga qo'yadi) | kattalashish markazini o'zgartirish |
| `transition` | `"crossfade"` / `"zoom"` / `"dip"` / `"flash"` / `"slide"` yoki `{"type": "crossfade", "dur": 0.3}` - shu bo'lakka KIRISH | dub/joy/mavzu almashganda crossfade; final reveal'da zoom |
| `fade` (reja ildizida) | `0.6` yoki `{"in": 0.3, "out": 0.6, "color": "black", "audio": true}` | oxirida qoraga erish (kino, premium, hikoya) |

Qoidalar: gapirayotgan bosh uchun standart - **hard cut** (+ zoom almashinuvi); o'tishlar ko'pi bilan **2 xil**
(masalan crossfade + final zoom). O'tish vaqtni siljitmaydi (oldingi bo'lak dum kadrlari bilan uzaytiriladi),
ovoz kesimda keskin qoladi. `fade.out` ichida so'z bo'lmasin - oxirgi so'zdan keyin 0.3-0.6 s qoldir.

### 5. Uslub pasporti
```powershell
& $py montaj/passport.py --list
& $py montaj/passport.py --apply <nom> work/VIDEO/edit.json
```
Mavzuga mosini tanla (foydalanuvchi aytmagan bo'lsa: ekspert/biznes -> `hormozi`, reklama -> `sotuv-reklama`,
premium -> `ekspert-premium`, hikoya -> `kino`). `--apply` uzun bo'laklarni pauzalardan bo'ladi, zoom ritmini
beradi, **yuzni avtomatik kadrlaydi**, subtitr/rang/mavzu ranglarini va progress-barni qo'yadi, keyin
**SFX palitrasi va yo'riqnomani** chiqaradi - 6-qadamda ularga amal qil.

### 6. Animatsiya, SFX, musiqa
```powershell
& $py montaj/render.py work/VIDEO/edit.json --timeline-only    # -> timeline.txt (so'z@soniya)
```
Barcha vaqtlar **tayyor videodagi** soniyalar - faqat `timeline.txt` ga qarab qo'y.

**Animatsiyalar** (`animations` ro'yxati, HyperFrames). Umumiy maydonlar: `type`, `start`, `end`,
`x`/`y` (0..1, markaz). Matnda `*so'z*` - aksent rangida, `==ibora==` - ustidan marker chiziladi
(`==*so'z*==` - to'q matn, aksent marker; `mark_at` - soniya, `theme.marker` - rang), `\n` - yangi qator.

| type | Maydonlar | Qachon |
|---|---|---|
| `text` | `text`, `size` (110), `effect`: pop/slide/blur/drop/typewriter/**none** (birinchi kadrdan turadi), `style`: outline/box/plain, `bg`, `radius`, `padding`, `weight` | hook, kalit fikr, doimiy sarlavha |
| `mark` | `shape`: circle/underline/box/scribble/strike/highlight/check/cross, `x`,`y` (markaz), `w`,`h` (kadr ulushi), `color`, `stroke` (12), `draw` (0.45 s), `seed` | qo'lda chizilgan urg'u: raqam atrofida aylana, kalit gap ostida chiziq, callout ramka, "noto'g'ri" fikrni chizib tashlash |
| `profile_card` | `avatar` (rasm yo'li), `name`, `handle`, `subtitle`, `button` (Follow), `button_color` | oxirgi 1-2 s, profil CTA |
| `counter` | `from`, `to`, `prefix`, `suffix`, `label`, `decimals`, `size` | har qanday raqam/summa/foiz |
| `emoji` | `emoji`, `size` (190) | predmetli so'z (pul 💰, uy 🏠, vaqt ⏰) |
| `sticker` | `text`, `rotate`, `bg`, `color`, `size` | "YANGI", "CHEGIRMA", atama |
| `list` | `items`, `times` (har band chiqadigan vaqt), `bullet`, `y`, `size` | "3 ta usul", afzalliklar |
| `lower_third` | `title`, `subtitle`, `y` | ism-lavozim, brend |
| `cta` | `text`, `icon` (👆), `y` (0.86) | oxirgi 2-3 s |
| `arrow` | `angle` (90 = pastga), `color`, `size` | biror narsaga ishora |
| `flash` | `color`, `opacity` (0.85) | sahna almashganda, 0.2-0.3 s |
| `burst` | `color` | urg'uli lahza ortida nur chiziqlari |
| `progress` | `position`: top/bottom, `color`, `height` | butun video (`start`/`end` shart emas) |
| `html` | `file` - o'zing yozgan HTML + `<script>` (`tl`, `T`, `D`, `W`, `H`, `root`) | maxsus g'oya |
| `remotion` | `comp` (kompozitsiya nomi), `props` - Remotion (React) kompozitsiyasi, alohida shaffof qatlam | prujinali kinetik matn, split-screen kartochkalar, murakkab sahnalar |

**Remotion kompozitsiyalari** (`remotion/`, ro'yxat `Root.jsx` da; `props` da `*so'z*` - aksent):
- `TitleCard` - so'zlar birma-bir prujina bilan chiqadigan sarlavha: `text` (`\n` - qator), `y` (0.2), `size` (96), `stagger` (0.09)
- `StepCard` - split-screen qadam kartochkasi (yuqori qism qora panel): `step`, `title`, `icon` yoki `items` (ro'yxat),
  `caption`, `panel` (balandlik ulushi, 0.5). Panel yuzni yopmasligi uchun gapiruvchi kadrning pastki yarmida bo'lsin
  (zoom/`y` bilan) yoki `panel` ni kichraytir.
Yangi g'oya HyperFrames'ga sig'masa - `remotion/` ga yangi `.jsx` komponent yoz (uzunlik/fps/o'lcham props'dan keladi,
`Root.jsx` dagi `meta` orqali), `Root.jsx` da ro'yxatga ol va `remotion_layer.py --still` bilan kadrini tekshir.
Remotion litsenziyasi: shaxs va 3 kishigacha jamoa uchun bepul, kattaroq kompaniyaga pullik litsenziya kerak.

Qoidalar: animatsiya yuzni yopmasin (yuz odatda y 0.3-0.45 da) - yuqori qism (y 0.10-0.20) yoki yon tomonlar
(x 0.15/0.85). Subtitr chizig'i (y ~0.68) bilan to'qnashmasin. Bir vaqtda 2 tadan ortiq blok bo'lmasin.
Murakkab sahnalardan oldin `animate.py ... --snapshot 1.2 5.0` bilan kadrlarni ko'r.

**SFX**: pasport palitrasidan foydalan yoki qidir: `sfx_catalog.py --find money`, `--find impact heavy`,
`--find whoosh`. Fayl yo'li `assets/sfx/...`. Balandlik avtomatik tenglashtiriladi, `volume` 0.3-0.7.
Pasportdagi `every_s` dan zich qo'yma. SFX animatsiya bilan bir vaqtda bo'lsa yaxshi (emoji + pop, counter + kaching).

**Musiqa** (`assets/music/`, litsenziyalari `LITSENZIYA.txt` da): mavzuga mosini tanla.
`{"file", "volume": 0.15-0.35, "duck": true, "sync": true, "snap_sfx": true}`. Har qanday trek avval -14 LUFS ga
keltiriladi, `volume` - ovozga nisbatan (0.25 ~ ovozdan 12 LU past; pasportdagi qiymatdan boshla). `sync` - musiqani kesimlar bitga tushadigan joydan boshlaydi; `timeline.txt` oxirida
bitlar ro'yxati chiqadi - muhim kesim/flash/sarlavhani kuchli bitga 0.05-0.15 s surib moslash mumkin.
Papka bo'sh bo'lsa - musiqasiz qoldir va foydalanuvchiga ayt (mualliflik huquqi: o'zi qo'yadi).

Avatar videodan: `& $py montaj/reframe.py --avatar input/VIDEO.mp4 <soniya> work/VIDEO/avatar.png`
(yuz aniq ko'ringan, jilmaygan lahzani tanla). Profil `name`/`handle` ni foydalanuvchidan so'ra - o'ylab topma.

**Rang** (`grade`): clean, punchy, warm, soft-warm, cool, cinematic, moody, bw yoki `{"preset": "warm", "saturation": 1.2,
"contrast": 1.05, "vignette": true}`.

### 7. Storyboard va tasdiq (MAJBURIY)
```powershell
& $py montaj/storyboard.py work/VIDEO/edit.json      # -> work/VIDEO/storyboard.html (--no-anim - tezroq)
```
Har bir sahna eskizi (kesish, zoom, harakat, rang, HyperFrames qatlami bilan), vaqti, aytilgan gap, ekrandagi
bloklar, o'tish, SFX, kesim bitga tushganmi va ogohlantirishlar. Konsoldagi ogohlantirishlarni avval o'zing tuzat.
So'ng sahifani foydalanuvchiga `SendUserFile` (display: render) bilan yubor, 3-5 qatorda rejani ayt
(hook, nechta sahna, harakatlar, o'tishlar, musiqa) va **tasdiqlamaguncha yakuniy render qilma**. Foydalanuvchi
"to'g'ridan render qil" desa yoki faqat kichik tuzatish (ovoz, rang, matn) bo'lsa - bu qadamni o'tkazib yubor.

### 8. Render
```powershell
& $py montaj/render.py work/VIDEO/edit.json --preview   # tez tekshiruv
& $py montaj/render.py work/VIDEO/edit.json             # yakuniy
```
Animatsiya o'zgarmasa, HyperFrames qayta render qilinmaydi (kesh).

### 9. Tanqidchi ko'z
```powershell
& $py montaj/review.py output/VIDEO.mp4 --score work/VIDEO/edit.json   # 0-100 ball + muammolar
& $py montaj/review.py output/VIDEO.mp4                                # kadrlar jadvali -> Read bilan ko'r
& $py montaj/review.py output/VIDEO.mp4 --at 0.5 12.3                  # aniq kadrlar
```
Avtomatik ball: ovoz (-14 LUFS), cho'qqi, qora/qotgan kadrlar, ritm, hook kechikishi, **subtitr yuzni yopishi**.
So'ng kadrlarni o'zing ko'r: animatsiya yuzni yopmayaptimi, matn chiqib ketmayaptimi, emoji mavzuga mosmi,
zoom'da yuz kadrdami. **Ball 85 dan past yoki ko'zga tashlanadigan xato bo'lsa - tuzat va qayta render qil**
(ko'pi bilan 3 marta). Keyin foydalanuvchiga: fayl yo'li, uzunligi, ball, nima qilinganini qisqa ayt va
tuzatishlar bormi deb so'ra.

## Oddiy so'z bilan tuzatishlar

| Foydalanuvchi | `edit.json` |
|---|---|
| musiqa baland / past | `music.volume` x0.6 / x1.5 |
| ovoz past | `audio.voice_volume`: 1.3 |
| subtitr kattaroq / kichikroq | `subtitles.size` +12 / -12 |
| subtitr yuqoriroq / pastroq | `subtitles.position` -0.06 / +0.06 |
| boshqa rang | `subtitles.highlight` / `theme.accent`: "#RRGGBB" |
| boshqa uslub | `passport.py --apply <boshqa>` yoki `subtitles.style` (pro, pro-green, bebas, clean-box, pop, karaoke, minimal, bold-red) |
| animatsiya ko'p / kam | `animations` dan olib tashla / qo'sh |
| effektlar arzon ko'rinyapti | `ekspert-premium` pasporti, emoji va stikerlarni olib tashla |
| tezroq / dinamikroq | `hormozi` yoki `kulgili` pasporti (max_shot_s kichikroq), urg'u so'zlarga `move` punch |
| zerikarli, kadr qotib turibdi | uzun bo'laklarga `move` kenburns (1.0 -> 1.08) |
| o'tishlar keskin / silliqroq | mavzu almashgan bo'lakka `transition`: "crossfade" |
| oxiri keskin tugaydi | `fade`: 0.6 |
| buni ajratib ko'rsat | `mark` (circle/underline) yoki matnda `==ibora==` |
| qisqartir, 30 s qil | kam ahamiyatli bo'laklarni o'chir |
| rang xira / yorqinroq | `grade`: punchy / `{"preset": "clean", "saturation": 1.2}` |
| gorizontal / kvadrat | `format`: "16:9" / "1:1" / "4:5" |

## Bitta uzun videodan bir nechta Reels
3-5 ta mustaqil, qiziq parchani tanla. Har biri uchun `work/VIDEO/reel1.edit.json`, `reel2.edit.json`, ...
(`output` - `output/VIDEO_reel1.mp4`). Har bir reja o'z oraliq fayllariga ega (`reel1.timeline.txt` va h.k.).

## Tayyor referens hujjati berilsa (.md, .pdf, matn)
Hujjatni to'liq o'qi. Unda bir nechta formula bo'lsa - materialga mosini tanla va sababini ayt (masalan
gapirayotgan bosh + ikki plan -> podkast formulasi; ro'yxat bo'lsa -> karta formulasi), formulalarni aralashtirma.
Qoidalardan `styles/passports/<nom>.json` pasport yoz (`recipe` va `guide` bilan, misol: `nosir-podkast.json`),
yetishmagan vizual elementni `animate.py` ga yangi blok sifatida qo'sh yoki `html` blokida yasa.
Oxirida hujjatdagi tekshiruv ro'yxatini (checklist) band-band tekshirib, foydalanuvchiga natijasini ayt.

## Namuna asosida uslub o'rganish ("Chrome plagini")
Foydalanuvchi yoqtirgan blogger/akkaunt yoki video bersa:
1. **Havola** (YouTube Shorts, TikTok): `& $py montaj/reference.py URL1 URL2 --name blogger`
   Profil: `reference.py https://www.tiktok.com/@user --max 10 --name blogger`.
2. **Instagram** ko'pincha login talab qiladi. Claude in Chrome kengaytmasi ulangan bo'lsa, u bilan profilni
   ochib so'nggi reels havolalarini to'pla va ko'rib chiq. Videoni yuklashni foydalanuvchidan so'ra
   (o'zi saqlab `input/reference/` ga qo'yadi), so'ng `reference.py input/reference/*.mp4 --name blogger`.
3. `work/reference/<nom>/report.json` (kadr uzunligi, kesimlar/10 s, ovoz) va `sheet_*.png`, `cuts_*.png`
   rasmlarini Read bilan ko'r: subtitr shrifti/rangi/joyi/so'z soni, zoom, matn-animatsiyalar, emoji, B-roll,
   rang tusi, musiqa bormi.
4. `styles/passports/<nom>.json` ga yangi pasport yoz (`styles/passports.json` dagi tuzilma bilan bir xil):
   `pacing.max_shot_s` ~ report'dagi `avg_shot_s` x 1.3. Kerak bo'lsa `styles/subtitles.json` ga yangi
   subtitr uslubi qo'sh. So'ng `passport.py --apply <nom>` bilan ishlat.
Bu faqat uslubni o'rganish uchun - begona videoning o'zini montajda ishlatma.

## Cheklovlar (foydalanuvchiga halol ayt)
- Stok B-roll avtomatik yuklanmaydi; foydalanuvchi B-roll fayl bersa, uni `html` blokida `<video>` bilan qo'yish mumkin.
- Musiqa avtomatik yuklanmaydi (mualliflik huquqi) - `assets/music/` ga foydalanuvchi qo'yadi.
- Yuzni aniqlash old tomondan (frontal) yuzda ishonchli; profil yoki uzoq plan bo'lsa x/y ni qo'lda tekshir.
- Transkripsiya aniqligi ovoz sifatiga va shevaga bog'liq - 3-qadam majburiy.
