---
name: uslub-qadam-gaid
description: Qadamma-qadam gaid uslubida montaj - hook to'liq kadrda (oq sarlavha qutisi), so'ng split-screen - tepada to'q panel "Qadam N." va nutq bilan birga yig'iladigan sxema (ikonka, papka daraxti, ilova oynasida yoziladigan prompt, so'rov-javob, brendbuk), pastda gapiruvchi; 1-3 so'zli sans subtitr, "Saqlab qo'ying" va "Obuna bo'ling" tugmalari, oxirida izohga yoziladigan kalit so'z. Foydalanuvchi "qadamma-qadam", "gaid qilib", "N qadamda", "how-to", "yo'riqnoma", "split-screen", "ruscha referensdagidek" desa yoki ko'rsatma/sozlash haqidagi videoni montaj qilishni so'rasa ishlatiladi. Asosiy ish tartibi montaj skillida.
---

# Qadamma-qadam gaid uslubi

Referens: `input/reference/ref_DfSb0yJIOwn.mp4` (91.6 s), kadrma-kadr tahlil
`work/reference/ref_DfSb0yJIOwn/frames/` (2748 kadr, sheet_01..12.png). Pasport: `styles/passports/qadam-gaid.json`.
Umumiy tartib (transkripsiya, tuzatish, storyboard, render, baholash) - **montaj** skillida.

## O'lchangan raqamlar

| Ko'rsatkich | Qiymat |
|---|---|
| Uzunlik | 60-95 s |
| Kamera | deyarli kesimsiz: 7 plan, eng uzun dubl 48.6 s (pauzalar kesilgan, kadr o'zgarmaydi) |
| Split-screen | videoning ~62% i (14.6-79 s), panel 50% balandlik |
| Panel ichidagi o'zgarish | har ~1.5 s da yangi element |
| Subtitr | 1-3 so'z, oq qalin sans, konturisiz; to'liq kadrda y 0.56, splitda y 0.465 (panel pastki cheti) |
| Ovoz | -14 LUFS, doimiy musiqa foni (~129 BPM), pauzalarda ham fon bor |
| Rang | neytral, tabiiy (to'yinganlik past), panel #141210 + o'rtada iliq yorug'lik |

## Tuzilma

1. **Hook (0-4.5 s, to'liq kadr):** oq quti ichida qora qalin sarlavha "O'z AI-montajchingiz Claude Code'da 4 qadamda 🎬".
   Referensda bosh orqasida boshqa reels kartochkalari suzadi (ijtimoiy isbot). Material bo'lsa `Broll`/`html`
   bilan qo'shish mumkin, shart emas.
2. **Og'riq va va'da (4.5-14.6 s, to'liq kadr):** "hamma qiladi, lekin hech kim ko'rsatmaydi -> hozir hammasini
   ko'rsataman". "Saqlab qo'ying" degan joyda tepada `PillTag` "🔖 Saqlab qo'ying".
3. **Qadamlar (split-screen):** o'tish - zoom 0.3 s. Har qadam - bitta `GuidePanel` bloki. Panel elementlari
   aynan aytilayotgan narsani ko'rsatadi: "ilovani yukla" -> ilova ikonkasi; "papka och, ichida 3 ta papka" ->
   papka daraxti, shoxlari aytilishi bilan chiqadi; "shu promptni ber" -> oyna, prompt harfma-harf yoziladi;
   "brendbuk yig'adi" -> brendbuk kartochkasi; "tuzatishni ayt" -> sariq so'rov + oq javob.
4. **Xulosa sxemasi:** bitta panelda hamma qadam nomlari bir joyda.
5. **CTA (to'liq kadr):** "izohga MONTAJ deb yozing" - kalit so'z katta krem rangda ko'krak oldida
   (`BigWord`, `"layer": "behind"` - mikrofon/qo'l uning ustida). Oxirgi 3 s - `PillTag` "Obuna bo'ling" (ko'k).

## Tayyor bloklar

Split-screen bo'laklarida yuz pastki yarmga tushishi uchun `shift_y` ishlatiladi (kadr pastga suriladi, tepasi
panel bilan yopiladi). Bir xil dublning split qismini alohida bo'lak qil:
```json
{"start": 14.6, "end": 79.0, "zoom": 1.0, "shift_y": 0.3, "transition": {"type": "zoom", "dur": 0.3}}
```
Agar yuz manbada past joylashgan bo'lsa, `shift_y` ni 0.2-0.25 ga tushir. Yuz panel chegarasidan (y 0.5) pastda
va iyak kadr ichida bo'lishi kerak.

```json
"subtitles": {"style": "gaid"},
"music": {"file": "assets/music/...", "volume": 0.18, "duck": true},
"animations": [
  {"type": "text", "start": 0.0, "end": 4.4, "text": "O'z AI-montajchingiz\nClaude Code'da 4 qadamda 🎬",
   "style": "box", "bg": "#FFFFFF", "color": "#111111", "size": 54, "y": 0.55, "effect": "none"},
  {"type": "remotion", "comp": "PillTag", "start": 12.4, "end": 14.5, "props": {"text": "Saqlab qo'ying", "icon": "🔖"}},

  {"type": "remotion", "comp": "GuidePanel", "start": 14.6, "end": 33.4, "subs": {"y": 0.465},
   "props": {"step": 1, "title": "Tayyorgarlik", "exit": false, "elements": [
     {"kind": "icon", "at": 0.3, "until": 4.2, "icons": [{"emoji": "✳️", "label": "Claude Code", "note": "↓ kompyuterga"}]},
     {"kind": "tree", "at": 4.2, "until": 12.0, "root": "AI montaj",
      "children": ["Isxodniklar", "Referenslar", "Tayyor"], "times": [3.5, 4.5, 5.5]},
     {"kind": "window", "at": 12.0, "title": "Yangi chat", "text": "Qayerda ishlash: Lokal\nPapka: AI montaj", "cps": 30}]}},
  {"type": "remotion", "comp": "GuidePanel", "start": 33.4, "end": 45.0, "subs": {"y": 0.465},
   "props": {"step": 2, "title": "Vositalar", "enter": false, "exit": false, "elements": [
     {"kind": "list", "at": 1.0, "until": 6.0, "items": [{"text": "Remotion"}, {"text": "HyperFrames"}, {"text": "FFmpeg"}, {"text": "Whisper"}]},
     {"kind": "window", "at": 6.0, "title": "Claude Code", "text": "Sen mening montajchimsan. Shu vositalarni o'rnat: ..."}]}},
  {"type": "remotion", "comp": "GuidePanel", "start": 55.0, "end": 70.6, "subs": {"y": 0.465},
   "props": {"step": 4, "title": "Montaj", "enter": false, "elements": [
     {"kind": "chips", "at": 9.0, "items": [{"text": "Sarlavhani kattaroq qil", "at": 0},
                                            {"text": "Tayyor: sarlavha kattalashdi", "at": 1.2, "kind": "reply"}]}]}},

  {"type": "remotion", "comp": "BigWord", "start": 84.9, "end": 88.0, "layer": "behind",
   "props": {"text": "MONTAJ", "font": "Montserrat", "y": 0.6, "size": 130, "color": "#EFE3C8", "at": 0.1}},
  {"type": "remotion", "comp": "PillTag", "start": 88.0, "end": 91.6,
   "props": {"text": "Obuna bo'ling", "bg": "#1E88E5", "color": "#FFFFFF"}}
]
```

Eslatmalar:
- `GuidePanel` elementlarida `at`/`until` - **blok boshidan** soniya. Element ketma-ket almashsa, oldingisiga
  `until` = keyingisining `at` qo'y. Bitta qadam ichida bir vaqtda bitta katta element bo'lsin.
- Element vaqtini `timeline.txt` dagi so'z vaqtidan ol: element so'z aytilishidan 0.1-0.2 s oldin chiqsin.
- Ketma-ket qadamlarda panel qayta tushmasin: birinchisida `enter` (standart true), keyingilarida
  `"enter": false`; oxirgisigacha `"exit": false`.
- Panel paytida subtitr `"subs": {"y": 0.465}` bilan panel pastiga ko'tariladi (blokning `subs` maydoni).
- `label` (standart "Qadam") - boshqa so'z kerak bo'lsa ("Bosqich", "Шаг").
- Prompt matni uzun bo'lsa, `window` ning `size` ini (30) 26 ga tushir va `cps` ni oshir (40).

## Taqiqlar
Tez kamera jump-cutlari, punch-in ketma-ketligi, rangli sakraydigan subtitr, ko'p SFX (faqat panel almashganda
ixtiyoriy yumshoq whoosh), 2 dan ortiq aksent rang (faqat to'q sariq #F5A623 + oq).

## Tekshiruv ro'yxati
- [ ] Hook 0-4.5 s: oq sarlavha qutisi, "N qadam" va'dasi.
- [ ] Splitda yuz pastki yarmda, panel yuzni yopmaydi, iyak kadr ichida.
- [ ] Panel elementlari aytilgan so'z bilan bir vaqtda chiqadi (+-0.2 s), har 1-3 s da o'zgarish bor.
- [ ] Subtitr 1-3 so'z, splitda panel pastida, to'liq kadrda ko'krak ustida.
- [ ] CTA kalit so'zi va "Obuna bo'ling" oxirida; musiqa past, ovoz -14 LUFS.
