# Archon Service Shutdown Script for Windows
# This script provides a robust way to stop all Archon services

Write-Host "[ARCHON] Stopping all Archon services..." -ForegroundColor Yellow
Write-Host ""

# Function to kill processes on a specific port
function Stop-ProcessOnPort {
    param(
        [int]$Port,
        [string]$ServiceName,
        [string]$ProcessPattern = ""
    )
    
    Write-Host "Checking port $Port ($ServiceName)..."
    
    try {
        # Get processes using the port
        $netstatOutput = netstat -ano | Select-String ":$Port "
        $pids = @()
        
        foreach ($line in $netstatOutput) {
            if ($line -match "LISTENING\s+(\d+)") {
                $pids += [int]$matches[1]
            }
        }
        
        $pids = $pids | Sort-Object -Unique | Where-Object { $_ -gt 0 }
        
        if ($pids.Count -eq 0) {
            Write-Host "  [INFO] No process found on port $Port" -ForegroundColor Blue
            return $true
        }
        
        $allKilled = $true
        foreach ($pid in $pids) {
            try {
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($process) {
                    $processName = $process.ProcessName
                    $commandLine = ""
                    
                    # Get command line if possible
                    try {
                        $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $pid").CommandLine
                    } catch {
                        # Ignore WMI errors
                    }
                    
                    # If process pattern is specified, check if process matches
                    if ($ProcessPattern -and $commandLine -and $commandLine -notmatch $ProcessPattern) {
                        Write-Host "  [SKIP] Process $pid ($processName) doesn't match pattern '$ProcessPattern'" -ForegroundColor Blue
                        continue
                    }
                    
                    Write-Host "  [FOUND] Process $pid ($processName) on port $Port" -ForegroundColor Red
                    if ($commandLine) {
                        Write-Host "    Command: $($commandLine.Substring(0, [Math]::Min($commandLine.Length, 80)))" -ForegroundColor Gray
                    }
                    
                    # Try graceful termination first
                    try {
                        $process.CloseMainWindow() | Out-Null
                        Start-Sleep -Seconds 2
                        
                        # Check if still running
                        $process.Refresh()
                        if (!$process.HasExited) {
                            Write-Host "  [FORCE] Process $pid didn't stop gracefully, using force kill" -ForegroundColor Yellow
                            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                        }
                        
                        Start-Sleep -Seconds 1
                        $stillRunning = Get-Process -Id $pid -ErrorAction SilentlyContinue
                        if (!$stillRunning) {
                            Write-Host "  [SUCCESS] Killed process $pid" -ForegroundColor Green
                        } else {
                            Write-Host "  [WARNING] Could not kill process $pid (may be protected)" -ForegroundColor Yellow
                            $allKilled = $false
                        }
                    } catch {
                        Write-Host "  [ERROR] Failed to stop process $pid`: $($_.Exception.Message)" -ForegroundColor Red
                        $allKilled = $false
                    }
                } else {
                    Write-Host "  [INFO] Process $pid no longer exists" -ForegroundColor Blue
                }
            } catch {
                Write-Host "  [WARNING] Could not access process $pid`: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
        
        return $allKilled
    } catch {
        Write-Host "  [ERROR] Failed to check port $Port`: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to kill processes by pattern
function Stop-ProcessByPattern {
    param(
        [string]$Pattern,
        [string]$Description
    )
    
    Write-Host "Checking for $Description..."
    
    try {
        # Get all processes and filter by command line
        $matchingProcesses = @()
        $allProcesses = Get-WmiObject Win32_Process -ErrorAction SilentlyContinue
        
        foreach ($proc in $allProcesses) {
            if ($proc.CommandLine -and $proc.CommandLine -match $Pattern) {
                $matchingProcesses += $proc
            }
        }
        
        if ($matchingProcesses.Count -eq 0) {
            Write-Host "  [INFO] No $Description processes found" -ForegroundColor Blue
            return $true
        }
        
        $allKilled = $true
        foreach ($proc in $matchingProcesses) {
            try {
                $process = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "  [FOUND] $Description process (PID: $($proc.ProcessId))" -ForegroundColor Red
                    Write-Host "    Command: $($proc.CommandLine.Substring(0, [Math]::Min($proc.CommandLine.Length, 80)))" -ForegroundColor Gray
                    
                    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
                    Start-Sleep -Seconds 1
                    
                    $stillRunning = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
                    if (!$stillRunning) {
                        Write-Host "  [SUCCESS] Killed $Description process $($proc.ProcessId)" -ForegroundColor Green
                    } else {
                        Write-Host "  [WARNING] Could not kill process $($proc.ProcessId)" -ForegroundColor Yellow
                        $allKilled = $false
                    }
                }
            } catch {
                Write-Host "  [ERROR] Failed to stop process $($proc.ProcessId)`: $($_.Exception.Message)" -ForegroundColor Red
                $allKilled = $false
            }
        }
        
        return $allKilled
    } catch {
        Write-Host "  [ERROR] Failed to check for $Description`: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to test if service is responding
function Test-ServiceEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 2
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSeconds -UseBasicParsing -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Stop all known Archon services by port
Write-Host "1. Stopping Backend Services..."
$backend1 = Stop-ProcessOnPort -Port 8181 -ServiceName "Main Server"
$backend2 = Stop-ProcessOnPort -Port 8051 -ServiceName "MCP Server"
$backend3 = Stop-ProcessOnPort -Port 8052 -ServiceName "Agents Service"

Write-Host ""
Write-Host "2. Stopping Frontend Services..."
$frontend1 = Stop-ProcessOnPort -Port 3737 -ServiceName "Frontend (config port)" -ProcessPattern "node"
$frontend2 = Stop-ProcessOnPort -Port 5173 -ServiceName "Frontend (Vite default)" -ProcessPattern "node"
$frontend3 = Stop-ProcessOnPort -Port 5174 -ServiceName "Frontend (alternate 1)" -ProcessPattern "node"
$frontend4 = Stop-ProcessOnPort -Port 5175 -ServiceName "Frontend (alternate 2)" -ProcessPattern "node"

# Extra cleanup - kill any remaining processes that might be Archon-related
Write-Host ""
Write-Host "3. Checking for orphaned Python processes..."
$python1 = Stop-ProcessByPattern -Pattern "src\.(server|mcp|agents)" -Description "Archon Python"
$python2 = Stop-ProcessByPattern -Pattern "uv run python -m src" -Description "UV Python"

Write-Host ""
Write-Host "4. Checking for orphaned Node.js processes..."
$node1 = Stop-ProcessByPattern -Pattern "vite.*archon" -Description "Archon Vite"
$node2 = Stop-ProcessByPattern -Pattern "npm run dev.*archon" -Description "Archon npm"

# Verify all services are stopped
Write-Host ""
Write-Host "5. Verifying shutdown..."
$allStopped = $true

Write-Host "  Checking service endpoints..."

# Check Main Server
if (Test-ServiceEndpoint -Url "http://localhost:8181/api/health") {
    Write-Host "  [WARNING] Main Server still responding on port 8181" -ForegroundColor Yellow
    $allStopped = $false
} else {
    Write-Host "  [OK] Main Server stopped" -ForegroundColor Green
}

# Check MCP Server
if (Test-ServiceEndpoint -Url "http://localhost:8051/mcp") {
    Write-Host "  [WARNING] MCP Server still responding on port 8051" -ForegroundColor Yellow
    $allStopped = $false
} else {
    Write-Host "  [OK] MCP Server stopped" -ForegroundColor Green
}

# Check Agents Service
if (Test-ServiceEndpoint -Url "http://localhost:8052/health") {
    Write-Host "  [WARNING] Agents Service still responding on port 8052" -ForegroundColor Yellow
    $allStopped = $false
} else {
    Write-Host "  [OK] Agents Service stopped" -ForegroundColor Green
}

# Check Frontend
$frontendRunning = $false
$frontendPorts = @(5173, 5174, 5175, 3737)
foreach ($port in $frontendPorts) {
    if (Test-ServiceEndpoint -Url "http://localhost:$port") {
        Write-Host "  [WARNING] Frontend still responding on port $port" -ForegroundColor Yellow
        $allStopped = $false
        $frontendRunning = $true
        break
    }
}
if (-not $frontendRunning) {
    Write-Host "  [OK] Frontend stopped" -ForegroundColor Green
}

# Final status
Write-Host ""
Write-Host "==========================================="
if ($allStopped) {
    Write-Host "[SUCCESS] All Archon services stopped successfully" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Some services may still be running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "If services are still running, you can:"
    Write-Host "  1. Run this script again"
    Write-Host "  2. Check running processes manually:"
    Write-Host "     - netstat -ano | findstr `":818[1-2]`""
    Write-Host "     - Get-Process python, node | Where-Object {`$_.CommandLine -match 'archon|src\.(server|mcp|agents)|vite'}"
    Write-Host "  3. Kill specific processes:"
    Write-Host "     - Stop-Process -Id <PID> -Force"
}
Write-Host "==========================================="
Write-Host ""
Write-Host "Use ./start_app.sh to restart services"