$ErrorActionPreference = "Stop"

$python = if (Test-Path ".venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "py" }
$icon_png = "ChatGPT Image Aug 28, 2026, 09_52_01 PM.png"
$icon_ico = "PaymentReconciliation.ico"
$work_path = "build\PaymentReconciliation-$PID"

Write-Host "Installing application dependencies..."
& $python -m pip install -r requirements.txt

if (Test-Path $icon_png) {
    Write-Host "Creating application icon..."
    & $python -c "from PIL import Image; Image.open(r'$icon_png').convert('RGBA').save(r'$icon_ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])"
    if ($LASTEXITCODE -ne 0) { throw "Could not create application icon." }
} elseif (-not (Test-Path $icon_ico)) {
    throw "No application icon found. Add a PNG named '$icon_png' or an ICO named '$icon_ico'."
} else {
    Write-Host "Using existing application icon: $icon_ico"
}

Write-Host "Building PaymentReconciliation.exe..."
& $python -m PyInstaller --clean --noconfirm --onefile --windowed --icon $icon_ico --add-data "$icon_ico;." --workpath $work_path --name PaymentReconciliation app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$exe_path = (Resolve-Path "dist\PaymentReconciliation.exe").Path
$desktop_path = [Environment]::GetFolderPath("Desktop")
$shortcut_path = Join-Path $desktop_path "Payment Reconciliation System.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcut_path)
$shortcut.TargetPath = $exe_path
$shortcut.WorkingDirectory = Split-Path $exe_path
$shortcut.IconLocation = "$exe_path,0"
$shortcut.Save()

Write-Host "Build complete: $exe_path"
Write-Host "Desktop shortcut created: $shortcut_path"