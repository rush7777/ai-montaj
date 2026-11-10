---
name: uslub-azizon
description: "Azizon" brend-hikoya uslubida montaj - intervyu (A-roll) + har bir gapni ko'rsatadigan kinematografik AI-tasvirlar (B-roll), krem devor sahnalari (savol, X belgili predmet, brend kartochka), ingichka serif subtitr (so'zlar birma-bir yumshoq chiqadi, kalit so'z tik), sariq vaqt yorlig'i, odam orqasidagi katta so'z, yumshoq dissolve, musiqasiz. Foydalanuvchi "Azizon uslubida", "hikoya qilib", "brend hikoyasi", "storytelling reklama", "premium hikoya", "referensdagidek (Azizon)" desa yoki mijoz bilan bo'lgan voqea/kompaniya qadriyati haqidagi intervyuni montaj qilishni so'rasa ishlatiladi. Asosiy ish tartibi montaj skillida - bu skill uslub qoidalari va tayyor bloklarni beradi.
---

# Azizon uslubi (brend-hikoya)

Referens: `input/reference/Azizon_reels_v2.mp4` (51.6 s), kadrma-kadr tahlil `work/reference/azizon/frames/`
(frames.csv - 1549 kadr, shots.json, sheet_01..07.png). Pasport: `styles/passports/azizon-hikoya.json`.
Montajning umumiy tartibi (transkripsiya, tuzatish, storyboard, render, baholash) - **montaj** skillida; bu yerda
faqat shu uslubga xos qoidalar.

## O'lchangan raqamlar (referens)

| Ko'rsatkich | Qiymat |
|---|---|
| Uzunlik | 50-55 s |
| Planlar | 19 ta, o'rtacha 2.7 s, eng uzuni 7.7 s (intervyu) |
| O'tishlar | 14 dissolve (0.25 s, xiralik bilan), 2 qattiq kesim (faqat intervyu burchagi almashganda), 2 punch |
| Ekran ulushi | B-roll AI-tasvirlar ~52%, intervyu ~36%, devor sahnalari ~12% |
| Matn ekranda | kadrlarning 83% ida |
| Subtitr | y ~0.66-0.70, 2 qatorgacha, 2-6 so'z |
| Ovoz | -16 LUFS, LRA 3, **musiqa yo'q** (pauzalarda -88 dB), SFX yo'q |
| Rang | iliq kino (A-roll to'yinganlik ~120, iliqlik +33; B-roll iliqlik +45), o'tmish - oq-qora |

## Hikoya formulasi (sahnalar ketma-ketligi)

1. **Hook - devor + kartina (0-3.3 s).** Krem devor, tilla ramkada birinchi AI-tasvir. Ostida intervyuerning
   savoli to'q serif subtitrda ("...deyishadi. O'zi nima deysiz?"). Oxirida kamera kartina ichiga kiradi
   (`zoom_into`) va o'sha tasvir to'liq ekranda B-roll bo'lib davom etadi.
2. **Javob boshlanadi - intervyu (2-3 s).** Ism bilan murojaat, "bir voqea esimga keldi".
3. **Voqea - B-roll zanjiri (har biri 2.5-4 s).** Spiker aytayotgan har bir aniq narsa alohida tasvirda:
   - kim keldi (odam darvoza oldida, **oq-qora**, chunki o'tmish) + sariq yorliq "Bundan 4-5 yil oldin";
   - nima olib keldi (odam mashina yonida) + **katta so'z odam orqasida** ("GO'SHT");
   - nimani ko'rdi (yuqoridan: bagajdagi go'sht) + oq qo'lda chizilgan doira.
4. **Muammo - devor + predmet.** Krem devor, o'rtada predmet (idish), tepada kichik sans "Hech qanaqa" va katta
   qizil-jigarrang serif "idishsiz,"; so'ng qizil **X** chiziladi.
5. **Bizning javobimiz - intervyu (5-8 s).** To'g'ridan-to'g'ri nutq qo'shtirnoqda, kalit so'z tagiga sariq chiziq.
6. **Ikkinchi savol - bo'sh devor.** Intervyuerning savoli ("Bundan nima xulosa qilsa bo'ladi, aka?") devor
   markazida to'q serifda.
7. **Xulosa - intervyu + katta qizil so'z odam orqasida** ("KO'CHADAN"), tagiga chiziq.
8. **Ishonch - 2 ta B-roll.** Hamkorlar (qo'l berishish), toza ombor/ishlab chiqarish (simmetrik, sovuq-toza).
9. **Brend kartochka (1.5 s).** Krem devorda brend nomi (katta serif) + shior "pill".

Material boshqacha bo'lsa ham shu mantiq saqlanadi: **savol -> voqea -> biz nima qildik -> xulosa -> brend**.

## Ish tartibi

1. Transkripsiya (`--lang uz`) va tuzatish. **Subtitr toza adabiy o'zbekchada bo'ladi**, spiker shevada
   gapirsa ham ("opkeldim" -> "olib keldim", "masdigi" -> "mashinada"). Tuzatishni `transcript.json` da qil.
2. Hikoyani bosqichlarga bo'l (yuqoridagi formula). Har bosqich uchun: vaqt oralig'i, ko'rsatiladigan tasvir,
   ekrandagi element.
3. **B-roll tasvirlar.** Foydalanuvchidan so'ra: o'zining rasmlari/videolari bormi? Yo'q bo'lsa - tasvirlar
   ro'yxatini promptlari bilan ber (pastdagi qo'llanma) va fayllarni `input/broll/` ga qo'yishini so'ra.
   AI-tasvir yasovchi ulangan vosita bo'lsa - foydalanuvchi roziligi bilan ishlat. Tasvir 9:16, kamida 1080x1920.
4. **Brend nomi va shiorini foydalanuvchidan so'ra** - o'ylab topma.
5. `edit.json` ni pasport bilan boshla: `& $py montaj/passport.py --apply azizon-hikoya work/VIDEO/edit.json`
   (yoki qo'lda: `"grade": "story-warm"`, `"subtitles": {"style": "hikoya"}`), so'ng bloklarni qo'sh (pastda).
6. Storyboard -> tasdiq -> render -> `review.py --score`. Uslubga moslikni tekshirish uchun natijani ham
   `frames.py output/VIDEO.mp4 --name VIDEO_check` bilan tahlil qil va raqamlarni yuqoridagi jadval bilan solishtir.

## Tayyor bloklar (`edit.json`)

A-roll bo'laklari: intervyu burchaklari almashganda `"transition": {"type": "crossfade", "dur": 0.25}`. 6 s dan
uzun bo'lakka `"move": {"type": "kenburns", "from": 1.0, "to": 1.05}`. Punch-in faqat 1-2 marta, yumshoq (1.12).

```json
"grade": "story-warm",
"subtitles": {"style": "hikoya", "underline": ["mashinada", "olmaymiz", "ko'chadan", "ishonchli"]},
"animations": [
  {"type": "remotion", "comp": "WallCard", "start": 0.0, "end": 3.4,
   "props": {"image": {"src": "input/broll/01_bozor.jpg", "style": "frame", "x": 0.5, "y": 0.3, "w": 0.4, "h": 0.2},
             "zoom_into": {"at": 2.95, "dur": 0.45}},
   "subs": {"color": "#241D18", "shadow": false, "y": 0.64}},
  {"type": "remotion", "comp": "Broll", "start": 3.4, "end": 6.0,
   "props": {"src": "input/broll/01_bozor.jpg", "zoom": [1.12, 1.2], "fade_in": 0.2, "fade_out": 0.3}},

  {"type": "remotion", "comp": "Broll", "start": 10.4, "end": 14.3,
   "props": {"src": "input/broll/02_darvoza.jpg", "bw": true, "zoom": [1.0, 1.07]}},
  {"type": "remotion", "comp": "LabelBox", "start": 10.6, "end": 14.2,
   "props": {"text": "Bundan 4-5 yil\noldin", "at": 0.1, "x": 0.07, "y": 0.2, "w": 0.6}},

  {"type": "remotion", "comp": "Broll", "start": 14.2, "end": 18.3, "props": {"src": "input/broll/03_mashina.jpg"}},
  {"type": "remotion", "comp": "BigWord", "start": 15.3, "end": 18.2, "layer": "behind",
   "props": {"text": "GO'SHT", "at": 0.1, "y": 0.2, "size": 270, "color": "#F4EFE6"}},

  {"type": "remotion", "comp": "WallCard", "start": 26.2, "end": 29.7, "subs": false,
   "props": {"lines": [{"text": "Hech qanaqa", "kind": "kicker", "at": 0.2, "y": 0.2},
                       {"text": "idishsiz,", "kind": "title", "at": 0.5, "y": 0.255},
                       {"text": "hech narsa", "kind": "kicker", "at": 1.5, "y": 0.2},
                       {"text": "to'shalmagan", "kind": "title", "at": 1.8, "y": 0.255}],
             "image": {"src": "input/broll/04_idish.png", "style": "object", "x": 0.5, "y": 0.55, "w": 0.5, "h": 0.2},
             "mark": {"shape": "cross", "at": 1.3, "x": 0.5, "y": 0.55, "w": 0.4, "h": 0.12}}},

  {"type": "remotion", "comp": "WallCard", "start": 37.4, "end": 39.6, "subs": {"color": "#241D18", "shadow": false, "y": 0.46}},
  {"type": "remotion", "comp": "BigWord", "start": 41.0, "end": 43.6, "layer": "behind",
   "props": {"text": "KO'CHADAN", "at": 0.1, "y": 0.2, "size": 270, "color": "#C8352B"}},

  {"type": "remotion", "comp": "WallCard", "start": 50.2, "end": 51.7, "subs": false,
   "props": {"lines": [{"text": "BREND", "kind": "brand", "at": 0.2, "y": 0.45}],
             "pill": {"text": "SHIOR", "at": 0.6, "y": 0.505}, "fade_in": 0.3}}
]
```

Eslatmalar:
- **WallCard ostida subtitr** standart holatda to'q rangga o'tadi. `"subs": {...}` bilan joyi yoki rangi
  o'zgartiriladi, `"subs": false` bilan yashiriladi (devorning o'z matni bo'lsa).
- WallCard `lines` da `*so'z*` - tik va 1.3 baravar katta. `kind`: `serif` (to'q kursiv), `title` (katta,
  qizil-jigarrang), `kicker` (kichik sans, kulrang), `brand`. Matn har so'zi `stagger` (0.16 s) bilan chiqadi.
  Bir xil joyda matn almashadigan bo'lsa (idishsiz -> to'shalmagan), ikkita WallCard blokiga bo'l.
- **BigWord orqada**: so'z boshga tegadigan balandlikda bo'lsin - yuz odatda y 0.3-0.45 da, so'z markazi
  y 0.18-0.25. Shunda bosh harflarning bir qismini to'sadi. Bu effekt faqat odam ko'rinadigan kadrda
  ishlaydi (A-roll yoki odamli B-roll). Render paytida niqob har kadr uchun ~0.13 s hisoblanadi.
- **Kalit so'z**: `"emphasis": "auto"` (har bo'lakdagi eng uzun so'z) yoki ro'yxat `["voqea", "aytib", ...]`.
  Referensda har bo'lakda bitta: ma'noli fe'l yoki ot (voqea, aytib, tushuntirib, olmaymiz, xulosa).
- **Tagiga chiziq** (`underline`) - butun video uchun 3-4 ta tayanch so'z, ko'p emas.
- Hikoya ichidagi qo'shtirnoqli nutq: transkriptda `“Keling,` va `ko‘ring”` kabi qo'shtirnoqlar bilan yoz.
- Oq doira (B-roll ustida predmet atrofida): HyperFrames `mark` bloki, `"color": "#FFFFFF"`, `"shape": "circle"`.
- Oxirgi kartochkadan oldin `fade` kerak emas: WallCard o'zi `fade_in` bilan chiqadi.

## Taqiqlar (uslubni buzadi)
Emoji, stiker, flash, whoosh/pop SFX, progress-bar, Montserrat Black subtitr, sakraydigan rangli so'zlar,
tez jump-cut ketma-ketligi, baland musiqa. Rang palitrasi faqat: krem devor, iliq kino tusi, oq/qora, sariq
(#E2B93B) chiziq va yorliq, qizil (#C8352B) X va katta so'z, qizil-jigarrang (#7A2E22) sarlavha.

## B-roll AI-tasvir promptlari (qo'llanma)
Umumiy qo'shimcha (har promptga): `cinematic photo, 9:16 vertical, warm golden light, shallow depth of field,
35mm film look, realistic, Central Asian setting, no text`.
- Odamlar: yoshi, kiyimi va kayfiyatini ayt ("50 yoshli o'zbek erkak, eski kurtka, do'ppi, darvoza oldida tik
  turibdi, to'liq bo'y, kameraga qaraydi"). Bir odam bir nechta tasvirda bo'lsa - tashqi ko'rinishini bir xil yoz.
- O'tmish voqeasi: rangli tasvir qil, oq-qora qilishni `bw: true` bajaradi.
- Predmet (devor sahnasi uchun): "oq fonda, yon tomondan, yumshoq soya, studiya" - so'ng fonini olib tashlab PNG qil.
- Oxirgi "ishonch" tasvirlari: toza, simmetrik, yorug' (hamkorlar qo'l berishmoqda; toza zamonaviy ombor).

## Tekshiruv ro'yxati (render'dan keyin)
- [ ] Birinchi 3 s: devor + kartina + savol, kartina ichiga kirish bor.
- [ ] B-roll ulushi 40-55%, har biri 2.5-4 s, hammasi dissolve bilan.
- [ ] Subtitr: serif kursiv, so'zlar birma-bir, bitta kalit so'z tik, devorda to'q rang, adabiy o'zbekcha.
- [ ] Katta so'z boshning orqasida (kadrni kattalashtirib tekshir: bosh harflarni to'sadimi).
- [ ] Emoji, SFX, musiqa yo'q (yoki musiqa juda past), ovoz -14..-16 LUFS.
- [ ] Oxirida brend nomi + shior, foydalanuvchi bergan matn bilan.
