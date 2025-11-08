# Скрипт для зупинки всіх запущених екземплярів бота
# Використовуйте це якщо отримуєте помилку "Conflict: terminated by other getUpdates request"

Write-Host "🔍 Пошук запущених екземплярів бота..." -ForegroundColor Yellow

# Шукаємо процеси Python, які запускають main.py
$processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*main.py*" -or $_.MainWindowTitle -like "*main.py*"
}

if ($processes) {
    Write-Host "⚠️  Знайдено $($processes.Count) запущених екземплярів:" -ForegroundColor Red
    $processes | ForEach-Object {
        Write-Host "   PID: $($_.Id) | CPU: $($_.CPU) | Memory: $([math]::Round($_.WorkingSet64/1MB, 2)) MB" -ForegroundColor Cyan
    }
    
    $confirm = Read-Host "`nЗупинити всі екземпляри? (Y/N)"
    if ($confirm -eq 'Y' -or $confirm -eq 'y') {
        $processes | ForEach-Object {
            Stop-Process -Id $_.Id -Force
            Write-Host "✅ Зупинено процес PID: $($_.Id)" -ForegroundColor Green
        }
        Write-Host "`n✨ Всі екземпляри зупинено!" -ForegroundColor Green
    } else {
        Write-Host "❌ Скасовано користувачем" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Немає запущених екземплярів бота" -ForegroundColor Green
}

Write-Host "`nТепер можна безпечно запустити бота:" -ForegroundColor Cyan
Write-Host "python main.py" -ForegroundColor White
