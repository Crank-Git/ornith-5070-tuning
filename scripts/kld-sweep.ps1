<#
.SYNOPSIS
    KL-divergence sweep: score several GGUF quants of one model against a reference quant.

.DESCRIPTION
    For each corpus, the reference model's logits are saved once (llama-perplexity
    --kl-divergence-base); each candidate is then scored against them. A candidate is
    "name|path|extra llama-perplexity args" (one per line in -CandidatesFile). Results go to <OutDir>\<corpus>-<name>.log,
    and a one-line summary per run to <OutDir>\summary.tsv.

    Run detached; it stops any running llama-server first because the card holds one model.
#>
param(
    [string]$Llama   = 'C:\AI\llama.cpp',
    [string]$OutDir  = 'C:\AI\kld',
    [string]$RefPath,
    # One candidate per line: name|path|extra args. (A file, because powershell -File does not split arrays.)
    [string]$CandidatesFile,
    [string]$Corpora = 'prose,code',
    [int]$Ctx = 4096,
    [int]$Chunks = 12
)
$ErrorActionPreference = 'Stop'
$Candidates = Get-Content $CandidatesFile | Where-Object { $_.Trim() -and -not $_.StartsWith('#') }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$common = @('-c', $Ctx, '--chunks', $Chunks, '-b', $Ctx, '-ub', 2048, '-fa', 'on', '--fit', 'on')
$sum = Join-Path $OutDir 'summary.tsv'
if (-not (Test-Path $sum)) { "corpus`tname`tmean_kld`tkld_p99`tsame_top_p`tppl_q`tppl_base`trms_dp`tseconds" | Set-Content $sum }

function Get-Stat($text, $pat) { if ($text -match $pat) { $Matches[1] } else { '' } }

foreach ($c in ($Corpora -split ',')) {
    $corpus = Join-Path $OutDir "$c.txt"
    $base = Join-Path $OutDir "base-$c.kld"
    if (-not (Test-Path $base)) {
        $log = Join-Path $OutDir "$c-REF.log"
        "[$(Get-Date -f s)] reference $c" | Add-Content (Join-Path $OutDir 'progress.log')
        $a = @('-m', $RefPath, '-f', $corpus) + $common + @('--kl-divergence-base', $base)
        cmd /c "`"$Llama\llama-perplexity.exe`" $($a -join ' ') > `"$log`" 2>&1"
        if ($LASTEXITCODE -ne 0) { "[$(Get-Date -f s)] REF FAILED $c ($LASTEXITCODE)" | Add-Content (Join-Path $OutDir 'progress.log'); exit 1 }
    }
    foreach ($cand in $Candidates) {
        $name, $path, $extra = $cand -split '\|', 3
        $log = Join-Path $OutDir "$c-$name.log"
        if ((Test-Path $log) -and (Select-String -Path $log -Pattern 'Mean +KLD' -Quiet)) { continue }
        "[$(Get-Date -f s)] $c $name" | Add-Content (Join-Path $OutDir 'progress.log')
        $xa = if ($extra) { $extra -split ' ' } else { @() }
        $t0 = Get-Date
        $a = @('-m', $path, '-f', $corpus) + $common + $xa + @('--kl-divergence-base', $base, '--kl-divergence')
        cmd /c "`"$Llama\llama-perplexity.exe`" $($a -join ' ') > `"$log`" 2>&1"
        $secs = [int]((Get-Date) - $t0).TotalSeconds
        $t = Get-Content $log -Raw
        $row = @($c, $name,
            (Get-Stat $t 'Mean +KLD:\s+([0-9.]+)'),
            (Get-Stat $t '99\.0%\s+KLD:\s+([0-9.]+)'),
            (Get-Stat $t 'Same top p:\s+([0-9.]+)'),
            (Get-Stat $t 'Mean PPL\(Q\)\s+:\s+([0-9.]+)'),
            (Get-Stat $t 'Mean PPL\(base\)\s+:\s+([0-9.]+)'),
            (Get-Stat $t 'RMS .p\s+:\s+([0-9.]+)'),
            $secs) -join "`t"
        $row | Add-Content $sum
    }
}
"[$(Get-Date -f s)] DONE" | Add-Content (Join-Path $OutDir 'progress.log')
