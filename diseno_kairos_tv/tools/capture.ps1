$ErrorActionPreference = 'Stop'

$designRoot = Split-Path -Parent $PSScriptRoot
$htmlRoot = Join-Path $designRoot 'html'
$imageRoot = Join-Path $designRoot 'images'
$profileRoot = Join-Path $designRoot '.edge-profile'
$browser = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

if (-not (Test-Path -LiteralPath $browser)) {
    $browser = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
}
if (-not (Test-Path -LiteralPath $browser)) {
    throw 'No se encontró Chrome ni Edge para generar las capturas.'
}

New-Item -ItemType Directory -Force -Path $imageRoot | Out-Null
New-Item -ItemType Directory -Force -Path $profileRoot | Out-Null

$files = Get-ChildItem -LiteralPath $htmlRoot -Filter '*.html' | Sort-Object Name
foreach ($file in $files) {
    $isMobile = $file.BaseName.StartsWith('mobile-')
    $size = if ($isMobile) { '390,844' } else { '1920,1080' }
    $output = Join-Path $imageRoot ($file.BaseName + '.png')
    $uri = [System.Uri]::new($file.FullName).AbsoluteUri

    & $browser `
        '--headless=new' `
        '--disable-gpu' `
        '--hide-scrollbars' `
        '--disable-background-mode' `
        '--disable-background-networking' `
        '--disable-extensions' `
        '--no-first-run' `
        '--allow-file-access-from-files' `
        '--force-device-scale-factor=1' `
        '--run-all-compositor-stages-before-draw' `
        '--virtual-time-budget=1200' `
        "--user-data-dir=$profileRoot" `
        "--window-size=$size" `
        "--screenshot=$output" `
        $uri | Out-Null

    if (-not (Test-Path -LiteralPath $output)) {
        throw "No se generó $output"
    }
}

Write-Host "Generadas $($files.Count) capturas en $imageRoot"
