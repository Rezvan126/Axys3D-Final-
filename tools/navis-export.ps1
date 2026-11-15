# Open a Revit (or other) model in Navisworks Manage 2026 and export it to FBX, unattended.
#   powershell -File tools\navis-export.ps1 <model.rvt> <out.fbx>
param([string]$In, [string]$Out)
$ErrorActionPreference = "Stop"
$dir = "C:\Program Files\Autodesk\Navisworks Manage 2026"
Add-Type -Path (Join-Path $dir "Autodesk.Navisworks.Automation.dll")
$In = (Resolve-Path $In).Path
$Out = [System.IO.Path]::GetFullPath($Out)
$app = New-Object Autodesk.Navisworks.Api.Automation.NavisworksApplication
try {
    $app.DisableProgress()
    Write-Output "opening $In"
    $app.OpenFile($In)
    $nwd = [System.IO.Path]::ChangeExtension($Out, ".nwd")
    $app.SaveFile($nwd)
    Write-Output "saved nwd"
    $r = $app.ExecuteAddInPlugin("NativeExportPluginAdaptor_LcFbxExporterPlugin_Export.Navisworks", @($Out))
    Write-Output "fbx plugin returned $r"
} finally {
    $app.Dispose()
}
Get-Item $Out, ([System.IO.Path]::ChangeExtension($Out, ".nwd")) -ErrorAction SilentlyContinue | Select-Object Name, Length
