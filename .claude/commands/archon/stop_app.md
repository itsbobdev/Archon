# Stop Archon Application

Stop all Archon services including frontend, main server, MCP server, and agents service.

## Command
```bash
echo "==========================================="
echo "[ARCHON] Stopping all services..."
echo "==========================================="
echo ""

# Function to kill process on a specific port
kill_port() {
    local port=$1
    local service=$2
    echo "Checking port $port ($service)..."
    
    # Get PID using netstat and awk
    local pids=$(netstat -ano | grep ":$port.*LISTENING" | awk '{print $NF}' | sort -u)
    
    if [ -z "$pids" ]; then
        echo "  [INFO] No process found on port $port"
    else
        for pid in $pids; do
            if [ "$pid" != "0" ]; then
                echo "  [FOUND] Process $pid on port $port"
                taskkill //F //PID $pid 2>nul
                if [ $? -eq 0 ]; then
                    echo "  [SUCCESS] Killed process $pid"
                else
                    echo "  [WARNING] Could not kill process $pid (may already be stopped)"
                fi
            fi
        done
    fi
}

# Stop all known Archon services
echo "1. Stopping Frontend Services..."
kill_port 3737 "Frontend (config port)"
kill_port 5173 "Frontend (Vite default)"
kill_port 5174 "Frontend (alternate 1)"
kill_port 5175 "Frontend (alternate 2)"

echo ""
echo "2. Stopping Backend Services..."
kill_port 8181 "Main Server"
kill_port 8051 "MCP Server"
kill_port 8052 "Agents Service"

# Extra cleanup - kill any remaining Python processes that might be Archon-related
echo ""
echo "3. Checking for orphaned Python/uv processes..."

# Find Python processes running Archon modules (including those started with uv)
for pid in $(tasklist | grep -E "(python|uv)\.exe" | awk '{print $2}'); do
    # Check if this Python/uv process is running an Archon module
    wmic process where "ProcessId=$pid" get CommandLine 2>nul | grep -E "(src\.(server|mcp|agents)|archon)" >nul 2>&1
    if [ $? -eq 0 ]; then
        echo "  [FOUND] Orphaned Archon process (PID: $pid)"
        taskkill //F //PID $pid 2>nul
        if [ $? -eq 0 ]; then
            echo "  [SUCCESS] Killed orphaned process $pid"
        fi
    fi
done

# Also check for any npm/node processes running dev servers
echo ""
echo "4. Checking for Node.js processes..."
for pid in $(tasklist | grep -E "(node|npm)\.exe" | awk '{print $2}'); do
    # Check if this is running vite or archon-related
    wmic process where "ProcessId=$pid" get CommandLine 2>nul | grep -E "(vite|archon-ui)" >nul 2>&1
    if [ $? -eq 0 ]; then
        echo "  [FOUND] Frontend process (PID: $pid)"
        taskkill //F //PID $pid 2>nul
        if [ $? -eq 0 ]; then
            echo "  [SUCCESS] Killed frontend process $pid"
        fi
    fi
done

# Verify all services are stopped
echo ""
echo "5. Verifying shutdown..."
all_stopped=true

# Check each service endpoint
curl -s http://localhost:8181/health >nul 2>&1
if [ $? -eq 0 ]; then
    echo "  [WARNING] Main Server still responding on port 8181"
    all_stopped=false
else
    echo "  [OK] Main Server stopped"
fi

# MCP server check
curl -s http://localhost:8051/mcp >nul 2>&1
if [ $? -eq 0 ]; then
    echo "  [WARNING] MCP Server still responding on port 8051"
    all_stopped=false
else
    echo "  [OK] MCP Server stopped"
fi

curl -s http://localhost:8052/health >nul 2>&1
if [ $? -eq 0 ]; then
    echo "  [WARNING] Agents Service still responding on port 8052"
    all_stopped=false
else
    echo "  [OK] Agents Service stopped"
fi

# Check if any Vite dev server is running
frontend_running=false
for port in 5173 5174 5175 3737; do
    curl -s http://localhost:$port >nul 2>&1
    if [ $? -eq 0 ]; then
        echo "  [WARNING] Frontend still responding on port $port"
        all_stopped=false
        frontend_running=true
        break
    fi
done
if [ "$frontend_running" = false ]; then
    echo "  [OK] Frontend stopped"
fi

# Final status
echo ""
echo "==========================================="
if [ "$all_stopped" = true ]; then
    echo "[SUCCESS] All Archon services stopped successfully"
else
    echo "[WARNING] Some services may still be running"
    echo ""
    echo "Try running this command again or manually kill the processes:"
    echo "  1. Open Task Manager (Ctrl+Shift+Esc)"
    echo "  2. Look for python.exe, uv.exe, node.exe processes"
    echo "  3. End those tasks manually"
fi
echo "==========================================="
echo ""
echo "Use /archon:start_app to restart services"
```

## Description
Robustly stops all Archon microservices for non-Docker environments:
- Stops services on all known ports
- Cleans up Python processes started with `uv run`
- Cleans up Node.js/npm processes running Vite
- Verifies services are actually stopped
- Provides clear feedback on what was found and stopped

## Usage
Type `/archon:stop_app` to stop all Archon services.

## Troubleshooting
If services don't stop:
1. Run the command again
2. Check Task Manager for `python.exe`, `uv.exe`, `node.exe` processes
3. Manually end those tasks if needed
4. On Windows, you may need to run your terminal as Administrator

## Related Commands
- `/archon:start_app`: Start all Archon services