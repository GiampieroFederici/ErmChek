# Installa ErmChek per questo utente: copia dist\ErmChek in %LOCALAPPDATA%\ErmChek e crea i collegamenti
# sul Desktop e nel menu Start (come ProfileMetaNanni). Nessun permesso di amministratore, nessuna rete.
param([string]$Sorgente = '')
if (-not $Sorgente) {   # dallo zip: cartella ErmChek accanto allo script; dal progetto: dist\ErmChek
    $Sorgente = Join-Path $PSScriptRoot 'ErmChek'
    if (-not (Test-Path (Join-Path $Sorgente 'ErmChek.exe'))) { $Sorgente = Join-Path $PSScriptRoot '..\dist\ErmChek' }
}
$ErrorActionPreference = 'Stop'
$Sorgente = (Resolve-Path $Sorgente).Path
$Dest = Join-Path $env:LOCALAPPDATA 'ErmChek'
$Exe = Join-Path $Dest 'ErmChek.exe'
$Icona = Join-Path $Dest '_internal\assets\logo\ErmChek_icona.ico'   # Windows legge l'icona sempre da un .ico
if (-not (Test-Path (Join-Path $Sorgente 'ErmChek.exe'))) { throw "ErmChek.exe non trovato in ${Sorgente}: costruisci prima l'app." }
if (Get-Process -Name 'ErmChek' -ErrorAction SilentlyContinue) { throw 'ErmChek è aperto: chiudilo e riprova.' }
if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
Copy-Item -Recurse $Sorgente $Dest
Get-ChildItem -Recurse -File $Dest | Unblock-File
$sh = New-Object -ComObject WScript.Shell
foreach ($cartella in 'Desktop', 'Programs') {
    $lnk = Join-Path ([Environment]::GetFolderPath($cartella)) 'ErmChek.lnk'
    $l = $sh.CreateShortcut($lnk); $l.TargetPath = $Exe; $l.WorkingDirectory = $Dest
    $l.IconLocation = "$Icona,0"; $l.Description = 'ErmChek'; $l.Save()
}
"ErmChek installato in $Dest. Collegamenti: Desktop e menu Start."
"Ora apro ErmChek. La prima volta Windows controlla i file: l'apertura può richiedere fino a un minuto."
"ErmChek installed. Opening it now: the first start can take up to a minute while Windows checks the files."
Start-Process $Exe
