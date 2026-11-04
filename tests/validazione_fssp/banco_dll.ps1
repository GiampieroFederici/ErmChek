# F1 (D047): calcola i riferimenti chiamando la parte scientifica vera di FSSP (FSSP.Models.dll),
# con la stessa sequenza di chiamate delle finestre di FSSP.exe (frmBacteriaGrowth, frmLmLAB, frmLmBoundary,
# calcolatrici) e passi di 1 minuto come la finestra.
# Uso (Windows PowerShell 5.1): powershell -File banco_dll.ps1 -Casi casi.json -Uscita <cartella>
# Uscita: <cartella>\scalari.jsonl (numeri in "G17", si rileggono esatti) e <cartella>\<id>.bin (curve, double).
param([Parameter(Mandatory)][string]$Casi, [Parameter(Mandatory)][string]$Uscita,
      [string]$Dll = "C:\Program Files (x86)\DTU Food\FSSP\FSSP.Models.dll")
$ErrorActionPreference = 'Stop'
$inv = [Globalization.CultureInfo]::InvariantCulture
[void][Reflection.Assembly]::LoadFrom($Dll)
New-Item -ItemType Directory -Force $Uscita | Out-Null

function D([object]$s) { return [double]::Parse([string]$s, $inv) }
function T([object]$v) {
    if ($null -eq $v) { return $null }
    if ($v -is [bool]) { return $v }
    return ([double]$v).ToString("G17", $inv)
}

# imposta un modello come fanno le finestre (pH prima degli acidi; CO2 alla temperatura della casella)
function Imposta($m, $p) {
    $m.Temperature = D $p.temperatura
    $m.Aw = D $p.sale_fase_acquosa
    $m.PH = D $p.ph
    $m.LacticAcid = D $p.lattico
    $m.Phenol = D $p.fenoli
    $m.CO2 = D $p.co2
    $m.Diacetate = D $p.diacetato
    $m.AceticAcid = D $p.acetico
    $m.BenzoicAcid = D $p.benzoico
    $m.CitricAcid = D $p.citrico
    $m.SorbicAcid = D $p.sorbico
    $m.Nirite = D $p.nitrito
}

function Profilo($prof) {
    $tp = New-Object FSSP.Models.TimeProfile
    foreach ($tr in $prof) { $tp.Add((D $tr[0]), (D $tr[1])) }
    return [FSSP.Models.TimeProfile]::Expand($tp, 1.0)
}

function ScriviCurve($id, [double[][]]$serie) {
    $fs = [IO.File]::Create((Join-Path $Uscita "$id.bin"))
    $bw = New-Object IO.BinaryWriter($fs)
    foreach ($a in $serie) {
        $b = New-Object byte[] ($a.Length * 8)
        [Buffer]::BlockCopy($a, 0, $b, 0, $b.Length)
        $bw.Write($b)
    }
    $bw.Close()
}

$righe = New-Object Collections.Generic.List[string]
$dati = Get-Content -Raw -Encoding UTF8 $Casi | ConvertFrom-Json
foreach ($c in $dati.casi) {
    $o = [ordered]@{ id = $c.id; tipo = $c.tipo }
    try {
        switch ($c.tipo) {
            'secondario' {
                foreach ($nome in 'listeria', 'lab') {
                    $m = if ($nome -eq 'listeria') { New-Object FSSP.Models.Safety.Listeria } else { New-Object FSSP.Models.Safety.LacticAcidBacteria }
                    Imposta $m $c.prodotto
                    $o["mu_$nome"] = T $m.SecondaryGrowth(); $o["psi_$nome"] = T $m.Psi
                    if ($nome -eq 'listeria') {
                        $o.aw = T $m.Aw; $o.co2_disciolta = T $m.CO2
                        $o.nd_lattico = T $m.LacticAcid; $o.nd_acetico = T $m.AceticAcid; $o.nd_diacetato = T $m.Diacetate
                        $o.nd_citrico = T $m.CitricAcid; $o.nd_sorbico = T $m.SorbicAcid; $o.nd_benzoico = T $m.BenzoicAcid
                    }
                }
            }
            'singola' {
                $m = if ($c.organismo -eq 'listeria') { New-Object FSSP.Models.Safety.Listeria } else { New-Object FSSP.Models.Safety.LacticAcidBacteria }
                Imposta $m $c.prodotto
                $m.CellCount = D $c.n0
                $m.IncludeLagTime = [bool]$c.lag
                $o.mu = T $m.SecondaryGrowth(); $o.psi = T $m.Psi
                $g = New-Object FSSP.Models.Safety.SingleBacteriaGrowth($m)
                $g.CalculateGrowth((Profilo $c.profilo))
                $o.lag_giorni = T $m.LagPhaseDays
                $o.cento_volte_giorni = T $g.HundredFoldIncrease
                $o.sette_log_giorni = T $g.LogSevenIncrease
                $o.punti = $g.StoragePeriod.Length
                ScriviCurve $c.id @($g.StoragePeriod, $g.ModelGrowth)
            }
            'lm_lab' {
                $lab = New-Object FSSP.Models.Safety.LacticAcidBacteria
                $lm = New-Object FSSP.Models.Safety.Listeria
                $lm.Gamma = D $c.gamma
                Imposta $lm $c.prodotto
                Imposta $lab $c.prodotto
                $o.mu_listeria = T $lm.SecondaryGrowth(); $o.psi_listeria = T $lm.Psi
                $o.mu_lab = T $lab.SecondaryGrowth(); $o.psi_lab = T $lab.Psi
                $lab.CellCount = D $c.n0_lab
                $lm.CellCount = D $c.n0_listeria
                $lm.IncludeLagTime = [bool]$c.lag
                $o.lag_giorni = T $lm.LagPhaseDays
                $g = New-Object FSSP.Models.Safety.ListeriaLabGrowth($lab, $lm)
                $g.CalculateGrowth((Profilo $c.profilo))
                $o.cento_volte_listeria_giorni = T $g.HundredFoldIncrease
                $o.cento_volte_lab_giorni = T $g.LabHundredFold
                $o.sette_log_lab_giorni = T $g.LogSevenIncrease
                $o.punti = $g.StoragePeriod.Length
                ScriviCurve $c.id @($g.StoragePeriod, $g.ModelGrowth, $g.LabGrowth)
            }
            'confine' {
                $p = $c.prodotto
                $l = New-Object FSSP.Models.Safety.Listeria
                $l.IncludeNirite = $true
                $psi = D $c.psi
                $ac = D $p.acetico; $be = D $p.benzoico; $ci = D $p.citrico; $di = D $p.diacetato; $la = D $p.lattico; $so = D $p.sorbico; $co = D $p.co2
                $ns = 'FSSP.Models.Safety.BoundaryCalculators.'
                $calc = switch ($c.combinazione) {
                    'temperatura_lattico_diacetato' { New-Object ($ns + 'ListeriaTLD') $l, $psi, (35000.0 * 2.5), $co }
                    'ph_lattico_diacetato' { New-Object ($ns + 'ListeriaPLD') $l, $psi, (35000.0 * 2.5), $ac, $be, $ci, $so }
                    'ph_sale_fenoli' { New-Object ($ns + 'ListeriaPAS') $l, $psi, 8.0, $ac, $be, $ci, $di, $la, $so }
                    'temperatura_ph_co2' { New-Object ($ns + 'ListeriaPTC') $l, $psi, 100.0, $ac, $be, $ci, $di, $la, $so }
                    'temperatura_benzoico_sorbico' { New-Object ($ns + 'ListeriaTBS') $l, $psi, (1200.0 * 2.5), $co }
                    'ph_benzoico_sorbico' { New-Object ($ns + 'ListeriaPBS') $l, $psi, (1200.0 * 2.5), $ac, $ci, $di, $la }
                    'temperatura_acetico_citrico' { New-Object ($ns + 'ListeriaTAC') $l, $psi, (11000.0 * 2.5), $co }
                    'ph_acetico_citrico' { New-Object ($ns + 'ListeriaPAC') $l, $psi, (11000.0 * 2.5), $be, $di, $la, $so }
                }
                $calc.Steps = $false
                Imposta $l $p   # come frmLmBoundary.ComputeGrowthBoundary, prima di ogni curva
                [double[]]$xs = $null; [double[]]$zs = $null
                $calc.ComputeGrowthBoundary((D $c.x), [ref]$xs, [ref]$zs)
                $o.punti = $xs.Length
                ScriviCurve $c.id @($xs, $zs)
            }
            'calcolatrici' {
                $o.sale_fase_acquosa = T ([FSSP.Models.Calculators.WaterPhase]::Calculate((D $c.nacl), (D $c.secco)))
                $o.sale_da_aw = T ([FSSP.Models.Calculators.WaterPhase]::WaterPhaseSaltFromWaterActivity((D $c.aw)))
                $l = New-Object FSSP.Models.Safety.Listeria; $l.Aw = D $c.nacl
                $o.aw_da_sale = T $l.Aw
                $o.acido_da_sale = T ([FSSP.Models.Calculators.OrganicAcid]::InProduct((D $c.sale_sodio), 90.08, 112.06))
                $o.sale_da_acido = T ([FSSP.Models.Calculators.OrganicAcid]::Sodiumlactate((D $c.acido_prodotto), 90.08, 112.06))
                $o.acido_fase_acquosa = T ([FSSP.Models.Calculators.OrganicAcid]::AcidInWaterPhase((D $c.acido_prodotto), (D $c.secco)))
                $o.percento_a_ppm = T ([FSSP.Models.Calculators.OrganicAcid]::Calculate((D $c.percento)))
                foreach ($tipo in 'Acetic', 'Benzoic', 'Citric', 'Diacetate', 'Lactic', 'Sorbic') {
                    $o["ppm_$tipo"] = T ([FSSP.Models.Calculators.OrganicAcid]::UndissociatedAcidToPpm([FSSP.Models.Calculators.OrganicAcidType]::$tipo, (D $c.mic), (D $c.ph)))
                }
                $o.co2_fase_acquosa = T ([FSSP.Models.Calculators.Co2]::InWaterPhase((D $c.gas_prodotto), (D $c.temperatura), (D $c.co2_iniziale)))
                $o.co2_spazio_di_testa = T ([FSSP.Models.Calculators.Co2]::InHeadspace((D $c.co2_acquosa), (D $c.temperatura)))
            }
        }
    } catch {
        $o.errore = $_.Exception.GetType().Name + ": " + $_.Exception.Message
    }
    $righe.Add(($o | ConvertTo-Json -Compress))
}
[IO.File]::WriteAllLines((Join-Path $Uscita "scalari.jsonl"), $righe)
"FATTO: $($righe.Count) casi"
