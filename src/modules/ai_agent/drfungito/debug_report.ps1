param(
    [string]$ReportId = "",
    [string]$UserID = "anonymous",
    [string]$DrFungitoUrl = "http://localhost:4009"
)

Write-Host "🔧 Debug del Sistema de Reportes - FungiGT" -ForegroundColor Green
Write-Host ""

# Función para hacer peticiones HTTP
function Invoke-DrFungitoRequest {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [hashtable]$Headers = @{}
    )
    
    $Headers["X-User-Id"] = $UserID
    
    try {
        $response = Invoke-RestMethod -Uri "$DrFungitoUrl$Endpoint" -Method $Method -Headers $Headers
        return $response
    } catch {
        Write-Host "❌ Error en petición a $Endpoint`: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Verificar conexión
Write-Host "1. Verificando conexión con Dr. Fungito..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$DrFungitoUrl/health" -TimeoutSec 5
    Write-Host "✅ Dr. Fungito está disponible" -ForegroundColor Green
} catch {
    Write-Host "❌ Dr. Fungito no está disponible en $DrFungitoUrl" -ForegroundColor Red
    Write-Host "   Asegúrate de que el servicio esté ejecutándose" -ForegroundColor Yellow
    exit 1
}

# Función para debugear reporte específico
function Debug-SpecificReport {
    param([string]$Id)
    
    Write-Host "🔍 Debugeando reporte: $Id" -ForegroundColor Cyan
    
    $reportDebug = Invoke-DrFungitoRequest -Endpoint "/debug/report/$Id"
    if ($reportDebug) {
        $report = $reportDebug.report
        
        Write-Host "📄 Título: $($report.title)" -ForegroundColor White
        Write-Host "🆔 ID: $($report.reportId)" -ForegroundColor White
        Write-Host "📁 Ruta PDF: $($report.pdfPath)" -ForegroundColor White
        Write-Host "✅ PDF existe: $($report.debug.pdfExists)" -ForegroundColor $(if ($report.debug.pdfExists) { "Green" } else { "Red" })
        Write-Host "📏 Tamaño: $([math]::Round($report.debug.pdfSize / 1KB, 2)) KB" -ForegroundColor White
        Write-Host "🔗 URL descarga: $($report.downloadUrl)" -ForegroundColor White
        Write-Host ""
        
        # Probar descarga HEAD
        Write-Host "🔍 Probando descarga HEAD..." -ForegroundColor Cyan
        try {
            $headResponse = Invoke-WebRequest -Uri "$DrFungitoUrl$($report.downloadUrl)" -Method Head -Headers @{"X-User-Id" = $UserID}
            Write-Host "✅ HEAD Status: $($headResponse.StatusCode)" -ForegroundColor Green
        } catch {
            Write-Host "❌ HEAD Error: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        # Preguntar si probar descarga completa
        $testDownload = Read-Host "¿Quieres probar la descarga completa? (y/n)"
        if ($testDownload -eq "y") {
            Write-Host "📥 Probando descarga completa..." -ForegroundColor Cyan
            try {
                $fileName = "debug_report_$($report.reportId).pdf"
                Invoke-WebRequest -Uri "$DrFungitoUrl$($report.downloadUrl)" -OutFile $fileName -Headers @{"X-User-Id" = $UserID}
                Write-Host "✅ Descarga exitosa: $fileName" -ForegroundColor Green
            } catch {
                Write-Host "❌ Error en descarga: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
}

# Si se proporciona un ID específico, debugear ese reporte
if ($ReportId) {
    Debug-SpecificReport -Id $ReportId
    exit 0
}

# Obtener lista de reportes
Write-Host "2. Obteniendo lista de reportes..." -ForegroundColor Cyan
$reportsData = Invoke-DrFungitoRequest -Endpoint "/debug/reports"

if ($reportsData) {
    Write-Host "✅ Encontrados $($reportsData.totalReports) reportes" -ForegroundColor Green
    Write-Host ""
    
    if ($reportsData.totalReports -eq 0) {
        Write-Host "⚠️ No hay reportes para debugear" -ForegroundColor Yellow
        exit 0
    }
    
    # Mostrar reportes disponibles
    Write-Host "📋 Reportes disponibles:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $reportsData.reports.Count; $i++) {
        $report = $reportsData.reports[$i]
        Write-Host "  $($i + 1). $($report.title)" -ForegroundColor White
        Write-Host "      ID: $($report.reportId)" -ForegroundColor Gray
        Write-Host "      PDF: $($report.pdfAvailable)" -ForegroundColor $(if ($report.pdfAvailable) { "Green" } else { "Red" })
        Write-Host ""
    }
    
    # Preguntar cuál debugear
    $choice = Read-Host "¿Cuál reporte quieres debugear? (número o ID completo)"
    
    if ($choice -match '^\d+$') {
        $index = [int]$choice - 1
        if ($index -ge 0 -and $index -lt $reportsData.reports.Count) {
            Debug-SpecificReport -Id $reportsData.reports[$index].reportId
        } else {
            Write-Host "❌ Número inválido" -ForegroundColor Red
        }
    } else {
        Debug-SpecificReport -Id $choice
    }
} else {
    Write-Host "❌ No se pudieron obtener los reportes" -ForegroundColor Red
}

Write-Host ""
Write-Host "💡 Para debugear un reporte específico directamente:" -ForegroundColor Yellow
Write-Host "   .\debug_report.ps1 -ReportId 'ID_DEL_REPORTE'" -ForegroundColor Yellow 