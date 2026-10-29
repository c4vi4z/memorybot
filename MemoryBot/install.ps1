param([switch]$Uninstall)
$ErrorActionPreference = "Stop"

$src  = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $env:LOCALAPPDATA "MemoryBot"
$venv = Join-Path $dest ".venv-memory"
$desktopLnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Memory Bot.lnk"
$menuLnk    = Join-Path ([Environment]::GetFolderPath("Programs")) "Memory Bot.lnk"

if ($Uninstall) {
    Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $desktopLnk, $menuLnk -Force -ErrorAction SilentlyContinue
    Write-Host "verwijderd (inclusief je lijsten en login)."
    exit 0
}

function Try-Python($cmd, $extra) {
    try {
        $out = & $cmd @extra -c "import sys, tkinter; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return ($out | Select-Object -First 1).Trim() }
    } catch {}
    return $null
}

$py = Try-Python "py" @("-3")
if (-not $py) { $py = Try-Python "python" @() }

if (-not $py) {
    Write-Host "Python (met tkinter) niet gevonden."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $a = Read-Host "Python nu installeren met winget? (j/n)"
        if ($a -eq "j") {
            winget install -e --id Python.Python.3.12 --scope user
            Write-Host "Klaar. Sluit dit venster en start install.bat opnieuw."
            exit 0
        }
    }
    Start-Process "https://www.python.org/downloads/"
    Write-Host "Installeer Python (vink 'Add python.exe to PATH' aan) en start install.bat opnieuw."
    exit 1
}
Write-Host "python: $py"

New-Item -ItemType Directory -Force (Join-Path $dest "app\lists") | Out-Null
Copy-Item (Join-Path $src "app.py"), (Join-Path $src "bot.py"), (Join-Path $src "updater.py") (Join-Path $dest "app") -Force
if (Test-Path (Join-Path $src "lists")) {
    robocopy (Join-Path $src "lists") (Join-Path $dest "app\lists") /E /XC /XN /XO | Out-Null
}

$icoPath = Join-Path $dest "icon.ico"
$pngPath = Join-Path $src "icon.png"
$haveIco = $false
if (Test-Path $pngPath) {
    Copy-Item $pngPath (Join-Path $dest "app\icon.png") -Force
    try {
        Add-Type -AssemblyName System.Drawing
        $img = [System.Drawing.Image]::FromFile($pngPath)
        $bmp = New-Object System.Drawing.Bitmap 256, 256
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.DrawImage($img, 0, 0, 256, 256)
        $g.Dispose()
        $img.Dispose()
        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
        $png = $ms.ToArray()
        $ms.Dispose()
        $fs = [System.IO.File]::Open($icoPath, [System.IO.FileMode]::Create)
        $bw = New-Object System.IO.BinaryWriter($fs)
        $bw.Write([UInt16]0)
        $bw.Write([UInt16]1)
        $bw.Write([UInt16]1)
        $bw.Write([byte]0)
        $bw.Write([byte]0)
        $bw.Write([byte]0)
        $bw.Write([byte]0)
        $bw.Write([UInt16]1)
        $bw.Write([UInt16]32)
        $bw.Write([UInt32]$png.Length)
        $bw.Write([UInt32]22)
        $bw.Write($png)
        $bw.Close()
        $fs.Close()
        $haveIco = $true
    } catch {
        Write-Host "icoon maken mislukt: $_"
    }
}

if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    & $py -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "venv maken mislukt" }
}
$vpy = Join-Path $venv "Scripts\python.exe"
& $vpy -m pip install --quiet selenium
if ($LASTEXITCODE -ne 0) { throw "selenium installeren mislukt (internet?)" }

Write-Host "chrome downloaden..."
& $vpy (Join-Path $dest "app\app.py") --setup
if ($LASTEXITCODE -ne 0) { throw "chrome downloaden mislukt" }

$ws = New-Object -ComObject WScript.Shell
foreach ($p in @($desktopLnk, $menuLnk)) {
    $s = $ws.CreateShortcut($p)
    $s.TargetPath = Join-Path $venv "Scripts\pythonw.exe"
    $s.Arguments = '"' + (Join-Path $dest "app\app.py") + '"'
    $s.WorkingDirectory = Join-Path $dest "app"
    $s.Description = "Memory Bot"
    if ($haveIco) { $s.IconLocation = $icoPath }
    $s.Save()
}

Write-Host ""
Write-Host "klaar. 'Memory Bot' staat op je bureaublad en in het startmenu."
Write-Host "lijsten zetten in: $(Join-Path $dest 'app\lists')"
