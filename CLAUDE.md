# AI montaj tizimi

Claude Code + FFmpeg + Whisper + HyperFrames asosida xom videoni professional darajada avtomatik montaj qiluvchi loyiha.
Foydalanuvchi o'zbek tilida gaplashadi - javoblarni o'zbekcha (lotin yozuvida) yoz.

Montaj so'ralganda `montaj` skillidan foydalan (`.claude/skills/montaj/SKILL.md`) - u to'liq ish tartibini beradi.

- Vositalar `%USERPROFILE%\.ai-montaj\` da: `venv` (Python), `models` (Whisper), `ffmpeg`, `node`, `hf` (HyperFrames),
  `anim` (animatsiya kompozitsiyalari). Yo'q bo'lsa - `setup.ps1`.
- `montaj/` - skriptlar (ro'yxati SKILL.md da)
- `styles/subtitles.json` - subtitr uslublari; `styles/passports.json` - o'rnatilgan uslub pasportlari;
  `styles/passports/*.json` - o'rganilgan yangi pasportlar
- `assets/sfx/` - Kenney CC0 + sintez SFX, `catalog.json` (teglar); `assets/sfx/custom/` - foydalanuvchiniki
- `assets/fonts/` - Montserrat, Bebas Neue (OFL); `assets/music/` - foydalanuvchining musiqalari
- `input/` xom videolar, `input/reference/` namuna videolar, `output/` tayyor videolar, `work/` oraliq fayllar.
  Foydalanuvchi uchun `Montajchi\` ildizida shu papkalarga yorliqlar (junction) bor: `1_Isxodniklar` -> `input`,
  `2_Referenslar` -> `input\reference`, `3_Tayyor` -> `output` - u videoni shularga tashlaydi
- Bitta papkada bir nechta reja bo'lishi mumkin: `edit.json`, `pro.edit.json`, `reel1.edit.json` - har biri o'z
  `*.timeline.txt`, `*.segments` fayllariga ega.
