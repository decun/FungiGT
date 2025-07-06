param(
    [string]$ReportId = ""
)

$DrFungitoUrl = "http://localhost:4009"
$UserID = "anonymous"

Write-Host "🔧 Debug Simple del Sistema de Reportes" -ForegroundColor Green
Write-Host ""

# Verificar conexión
Write-Host "Verificando conexión..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$DrFungitoUrl/health" -TimeoutSec 5
    Write-Host "✅ Dr. Fungito disponible" -ForegroundColor Green
} catch {
    Write-Host "❌ Dr. Fungito no disponible" -ForegroundColor Red
    exit 1
}

if ($ReportId) {
    Write-Host "Debug del reporte: $ReportId" -ForegroundColor Cyan
    
    try {
        $reportData = Invoke-RestMethod -Uri "$DrFungitoUrl/debug/report/$ReportId" -Headers @{"X-User-Id" = $UserID}
        $report = $reportData.report
        
        Write-Host "Título: $($report.title)" -ForegroundColor White
        Write-Host "PDF existe: $($report.debug.pdfExists)" -ForegroundColor White
        Write-Host "Ruta: $($report.pdfPath)" -ForegroundColor White
        
        if ($report.debug.pdfSize) {
            Write-Host "Tamaño: $([math]::Round($report.debug.pdfSize / 1024, 2)) KB" -ForegroundColor White
        }
        
        # Probar descarga
        try {
            $headResponse = Invoke-WebRequest -Uri "$DrFungitoUrl$($report.downloadUrl)" -Method Head -Headers @{"X-User-Id" = $UserID}
            Write-Host "✅ Descarga OK (Status: $($headResponse.StatusCode))" -ForegroundColor Green
        } catch {
            Write-Host "❌ Error descarga: $($_.Exception.Message)" -ForegroundColor Red
        }
        
    } catch {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "Obteniendo lista de reportes..." -ForegroundColor Cyan
    
    try {
        $reportsData = Invoke-RestMethod -Uri "$DrFungitoUrl/debug/reports" -Headers @{"X-User-Id" = $UserID}
        
        Write-Host "Total reportes: $($reportsData.totalReports)" -ForegroundColor Green
        
        foreach ($report in $reportsData.reports) {
            Write-Host ""
            Write-Host "- $($report.title)" -ForegroundColor White
            Write-Host "  ID: $($report.reportId)" -ForegroundColor Gray
            Write-Host "  PDF: $($report.pdfAvailable)" -ForegroundColor White
        }
        
        Write-Host ""
        Write-Host "Para debug específico usa:" -ForegroundColor Yellow
        Write-Host ".\debug_simple.ps1 -ReportId 'ID_DEL_REPORTE'" -ForegroundColor Yellow
        
    } catch {
        Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
} 