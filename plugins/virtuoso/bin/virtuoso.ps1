# Virtuoso launcher (version-agnostic — identical content for every installed
# version, so concurrent versions writing it is idempotent).
#
# Resolves the plugin root from $env:VIRTUOSO_PLUGIN_ROOT, else the newest valid
# entry in ~/.virtuoso/installs.json.
#
# Usage: virtuoso.ps1 <script-name> [args...]
#   ./virtuoso.ps1 virtuoso_preflight --root . --mode check
#   ./virtuoso.ps1 virtuoso_registry --root . next
param(
  [Parameter(Mandatory = $true, Position = 0)][string]$Script,
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest
)

function Test-VirtuosoRoot([string]$Path) {
  return $Path -and (Test-Path (Join-Path $Path 'scripts/virtuoso_preflight.py'))
}

$root = $env:VIRTUOSO_PLUGIN_ROOT
if (-not (Test-VirtuosoRoot $root)) {
  $stateHome = if ($env:VIRTUOSO_HOME) { $env:VIRTUOSO_HOME } else { $HOME }
  $record = Join-Path $stateHome '.virtuoso/installs.json'
  $root = ''
  if (Test-Path $record) {
    $installs = (Get-Content $record -Raw | ConvertFrom-Json).installs
    if ($installs) {
      $names = $installs.PSObject.Properties.Name |
        Sort-Object { try { [version](($_ -split '-')[0]) } catch { [version]'0.0.0' } } -Descending
      foreach ($name in $names) {
        $candidate = $installs.$name.root
        if (Test-VirtuosoRoot $candidate) { $root = $candidate; break }
      }
    }
  }
}

if (-not (Test-VirtuosoRoot $root)) {
  Write-Error 'virtuoso: no installed plugin root found. Set VIRTUOSO_PLUGIN_ROOT, or reinstall the plugin.'
  exit 1
}

$py = if (Get-Command python3 -ErrorAction SilentlyContinue) { 'python3' } else { 'python' }
& $py (Join-Path $root "scripts/$Script.py") @Rest
exit $LASTEXITCODE
