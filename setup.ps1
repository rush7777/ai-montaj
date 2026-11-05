# AI montaj tizimini o'rnatish (bir marta; qayta ishga tushirsa, borlarini o'tkazib yuboradi).
# Ishga tushirish: powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Hamma vositalar %USERPROFILE%\.ai-montaj ga o'rnatiladi (tizimga emas, admin huquqi kerak emas):
#   venv\     Python muhiti (Whisper, librosa, yt-dlp, OpenCV)
#   models\   Whisper large-v3 (~3 GB)
#   ffmpeg\   to'liq FFmpeg + ffprobe
#   node\     portativ Node.js 22
#   hf\       HyperFrames (animatsiya) + GSAP
#   remotion\ Remotion (React kompozitsiyalar) + Chrome Headless Shell (~525 MB)
# Qisqa yo'l tanlangan - Windows'ning 260 belgilik yo'l chegarasiga tushmaslik uchun.
# Har bir yuklangan fayl SHA256 bo'yicha tekshiriladi.

$ErrorActionPreference = "Stop"
$base = "$env:USERPROFILE\.ai-montaj"
$py = "$base\venv\Scripts\python.exe"
New-Item -ItemType Directory -Force $base | Out-Null

function Get-Verified($url, $out, $expected) {
    curl.exe -L --fail --retry 10 --retry-delay 5 -C - -o "$out.part" $url
    if ($LASTEXITCODE -ne 0) { throw "Yuklab bo'lmadi: $url" }
    if (-not $expected) { throw "Xesh topilmadi: $url" }
    $actual = (Get-FileHash "$out.part" -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected.ToLower()) { Remove-Item "$out.part"; throw "Fayl buzilgan (xesh mos emas): $url" }
    Move-Item -Force "$out.part" $out
}

# 1. Python muhiti
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python topilmadi. https://www.python.org/downloads/ dan Python 3.10+ o'rnating." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $py)) { Write-Host "Python muhiti yaratilmoqda..."; python -m venv "$base\venv" }
& $py -m pip install --upgrade pip -q
& $py -m pip install -r "$PSScriptRoot\requirements.txt" -q

# 2. Whisper large-v3
$model = "$base\models\faster-whisper-large-v3"
$hfbase = "https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main"
New-Item -ItemType Directory -Force $model | Out-Null
foreach ($f in "config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json") {
    if (-not (Test-Path "$model\$f")) { curl.exe -sS -L --fail -o "$model\$f" "$hfbase/$f" }
}
if (-not (Test-Path "$model\model.bin")) {
    Write-Host "Whisper modeli yuklanmoqda (~3 GB)..."
    Get-Verified "$hfbase/model.bin" "$model\model.bin" "69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1"
}

# 3. FFmpeg (BtbN, GitHub)
if (-not (Test-Path "$base\ffmpeg\bin\ffprobe.exe")) {
    Write-Host "FFmpeg yuklanmoqda (~190 MB)..."
    $rel = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
    $name = "ffmpeg-n8.1-latest-win64-gpl-8.1.zip"
    $sums = curl.exe -sS -L --fail "$rel/checksums.sha256"
    $line = ($sums -split "`n") | Where-Object { $_ -match [regex]::Escape($name) } | Select-Object -First 1
    Get-Verified "$rel/$name" "$base\ffmpeg.zip" ($line.Trim().Split(' ')[0])
    Expand-Archive "$base\ffmpeg.zip" "$base\ff-tmp" -Force
    if (Test-Path "$base\ffmpeg") { Remove-Item -Recurse -Force "$base\ffmpeg" }
    Move-Item (Get-ChildItem "$base\ff-tmp" -Directory | Select-Object -First 1).FullName "$base\ffmpeg"
    Remove-Item -Recurse -Force "$base\ff-tmp", "$base\ffmpeg.zip"
}

# 4. Node.js 22 (portativ)
if (-not (Test-Path "$base\node\node.exe")) {
    Write-Host "Node.js yuklanmoqda..."
    $v = ((curl.exe -sS https://nodejs.org/dist/index.json | ConvertFrom-Json) | Where-Object { $_.version -like 'v22.*' -and $_.lts } | Select-Object -First 1).version
    $sums = curl.exe -sS "https://nodejs.org/dist/$v/SHASUMS256.txt"
    $line = ($sums -split "`n") | Where-Object { $_ -match "node-$v-win-x64.zip" } | Select-Object -First 1
    Get-Verified "https://nodejs.org/dist/$v/node-$v-win-x64.zip" "$base\node.zip" ($line.Trim().Split(' ')[0])
    Expand-Archive "$base\node.zip" "$base\node-tmp" -Force
    Move-Item "$base\node-tmp\node-$v-win-x64" "$base\node"
    Remove-Item -Recurse -Force "$base\node-tmp", "$base\node.zip"
}

# 5. HyperFrames + GSAP
$env:PATH = "$base\node;$base\ffmpeg\bin;$env:PATH"
if (-not (Test-Path "$base\hf\node_modules\hyperframes")) {
    Write-Host "HyperFrames o'rnatilmoqda..."
    New-Item -ItemType Directory -Force "$base\hf" | Out-Null
    Push-Location "$base\hf"
    if (-not (Test-Path package.json)) { npm init -y | Out-Null }
    npm install hyperframes gsap@3.14.2 --no-fund --no-audit
    npx hyperframes telemetry disable | Out-Null
    Pop-Location
}

# 6. Remotion (kompozitsiyalar loyihaning remotion\ papkasida, render paytida shu yerga ko'chiriladi)
if (-not (Test-Path "$base\remotion\node_modules\@remotion\cli")) {
    Write-Host "Remotion o'rnatilmoqda..."
    New-Item -ItemType Directory -Force "$base\remotion" | Out-Null
    Push-Location "$base\remotion"
    if (-not (Test-Path package.json)) { '{"name":"ai-montaj-remotion","private":true,"version":"1.0.0"}' | Out-File -Encoding ascii package.json }
    npm install remotion@4.0.540 @remotion/cli@4.0.540 react@19.3.1 react-dom@19.3.1 --no-fund --no-audit
    npx remotion browser ensure
    Pop-Location
}

# 7. SFX: sintez + katalog
& $py "$PSScriptRoot\montaj\make_sfx.py" | Out-Null
& $py "$PSScriptRoot\montaj\sfx_catalog.py" --build | Select-Object -Last 1

foreach ($d in "input", "input\reference", "output", "work", "assets\music", "assets\sfx\custom", "styles\passports") {
    New-Item -ItemType Directory -Force "$PSScriptRoot\$d" | Out-Null
}
Write-Host "Tayyor. Videoni input\ papkasiga qo'ying va Claude'ga 'input\video.mp4 ni montaj qil' deb yozing." -ForegroundColor Green
