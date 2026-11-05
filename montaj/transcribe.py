"""Videodagi nutqni so'zma-so'z vaqtlari bilan matnga aylantiradi (faster-whisper, lokal).

Misol:
    python montaj/transcribe.py input/video.mp4
    python montaj/transcribe.py input/video.mp4 --model medium --prompt "Claude, montaj, Reels"

Natija: work/<video_nomi>/transcript.json va transcript.txt
"""
import argparse
import os
import subprocess
import time
from pathlib import Path

from common import ROOT, ffmpeg_exe, fmt_time, resolve, save_json

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# Xet yuklash protokoli Windows'da ba'zan 0 baytda qotib qoladi - oddiy HTTP yuklashni ishlatamiz
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

CYR2LAT = {
    "ў": "o'", "Ў": "O'", "ғ": "g'", "Ғ": "G'", "ш": "sh", "Ш": "Sh", "ч": "ch", "Ч": "Ch",
    "ё": "yo", "Ё": "Yo", "ю": "yu", "Ю": "Yu", "я": "ya", "Я": "Ya", "ц": "ts", "Ц": "Ts",
    "қ": "q", "Қ": "Q", "ҳ": "h", "Ҳ": "H", "ъ": "'", "ь": "", "Ъ": "'", "Ь": "",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ф": "f", "х": "x", "ы": "i", "э": "e", "щ": "sh",
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ж": "J", "З": "Z", "И": "I",
    "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S",
    "Т": "T", "У": "U", "Ф": "F", "Х": "X", "Ы": "I", "Э": "E", "Щ": "Sh",
    # Whisper o'zbekchani ba'zan turk/ozarbayjon yozuvida chiqaradi
    "ə": "a", "Ə": "A", "ı": "i", "İ": "I", "ğ": "g'", "Ğ": "G'", "ç": "ch", "Ç": "Ch",
    "ş": "sh", "Ş": "Sh", "ö": "o'", "Ö": "O'", "ü": "u", "Ü": "U", "ʻ": "'", "ʼ": "'", "‘": "'", "’": "'",
}


def to_latin(text: str) -> str:
    return "".join(CYR2LAT.get(ch, ch) for ch in text)


def load_audio(path):
    """FFmpeg orqali 16 kHz mono float massiv (PyAV versiyalariga bog'liq bo'lmaslik uchun)."""
    import numpy as np
    raw = subprocess.run([ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-i", str(path),
                          "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--model", default="large-v3",
                    help="large-v3 (aniq, sekin), medium, small yoki HuggingFace'dagi CTranslate2 model nomi")
    ap.add_argument("--lang", default="uz",
                    help="uz (kirill -> lotin), ru, en ... yoki auto. Faqat uz da lotinga o'giriladi")
    ap.add_argument("--prompt", default=None,
                    help="Faqat bir nechta so'z: brend nomlari, ismlar. Uzun gap bersangiz, Whisper uni "
                         "transkriptga ko'chirib qo'yishi mumkin")
    ap.add_argument("--out", help="Natija papkasi (standart: work/<video_nomi>)")
    ap.add_argument("--vad", action="store_true",
                    help="Jimlik filtrini yoqish. Shevali yoki mikrofoni uzoq nutqda gapni kesib "
                         "yuboradi, shuning uchun standart holatda o'chiq")
    args = ap.parse_args()

    video = resolve(args.video)
    out_dir = resolve(args.out) if args.out else ROOT / "work" / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel

    # setup.ps1 / curl orqali qo'lda yuklangan model bo'lsa, o'shani ishlatamiz
    local = Path.home() / ".ai-montaj" / "models" / f"faster-whisper-{args.model}"
    model_ref = str(local) if (local / "model.bin").exists() else args.model
    print(f"Model yuklanmoqda: {model_ref}...", flush=True)
    model = WhisperModel(model_ref, device="cpu", compute_type="int8")
    t0 = time.time()
    conv = to_latin if args.lang == "uz" else (lambda s: s)
    segments, info = model.transcribe(
        load_audio(video), language=None if args.lang == "auto" else args.lang, word_timestamps=True,
        vad_filter=args.vad,
        vad_parameters={"min_silence_duration_ms": 300}, initial_prompt=args.prompt,
        beam_size=5, condition_on_previous_text=False,
    )

    data = {"source": str(video), "language": info.language, "duration": info.duration,
            "model": args.model, "segments": []}
    lines = []
    for seg in segments:
        words = [{"start": round(w.start, 3), "end": round(w.end, 3),
                  "word": conv(w.word.strip()), "prob": round(w.probability, 2)}
                 for w in (seg.words or []) if w.word.strip()]
        if not words:
            continue
        text = conv(seg.text.strip())
        data["segments"].append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                                 "text": text, "words": words})
        lines.append(f"[{fmt_time(seg.start)} - {fmt_time(seg.end)}] {text}")
        print(lines[-1], flush=True)

    save_json(data, out_dir / "transcript.json")
    (out_dir / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nTayyor ({time.time() - t0:.0f} s): {out_dir / 'transcript.json'}")


if __name__ == "__main__":
    main()
