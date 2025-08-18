# Start Archon Application

Launch all Archon services including frontend, main server, MCP server, and agents service.

## Command
```bash
echo "==========================================="
echo "[ARCHON] Starting all services..."
echo "==========================================="
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    netstat -ano | grep ":$port.*LISTENING" >nul 2>&1
    return $?
}

# Check for already running services
echo "1. Checking for already running services..."
services_running=false

if check_port 8181; then
    echo "  [WARNING] Main Server already running on port 8181"
    services_running=true
fi

if check_port 8051; then
    echo "  [WARNING] MCP Server already running on port 8051"
    services_running=true
fi

if check_port 8052; then
    echo "  [WARNING] Agents Service already running on port 8052"
    services_running=true
fi

for port in 3737 5173 5174 5175; do
    if check_port $port; then
        echo "  [WARNING] Frontend already running on port $port"
        services_running=true
        break
    fi
done

if [ "$services_running" = true ]; then
    echo ""
    echo "  Some services are already running!"
    echo "  Run /archon:stop_app first to stop them, then try again."
    echo ""
    exit 1
fi

echo "  [OK] No conflicting services found"

# Check if logs directory exists, create if not
if [ ! -d "logs" ]; then
    mkdir logs
    echo "  [INFO] Created logs directory"
fi

# Check DOCKER_ENV setting
if ! grep -q "DOCKER_ENV=false" .env 2>nul; then
    echo ""
    echo "  [WARNING] DOCKER_ENV=false not found in .env file"
    echo "  Adding it now for non-Docker operation..."
    echo "" >> .env
    echo "# Docker Environment (set to 'false' for local development without Docker)" >> .env
    echo "DOCKER_ENV=false" >> .env
fi

echo ""
echo "2. Preparing Python environment..."

# Navigate to python directory
cd python 2>nul || {
    echo "  [ERROR] Cannot find python directory"
    echo "  Make sure you're in the Archon project root"
    exit 1
}

# Ensure dependencies are installed
echo "  Checking dependencies with uv..."
uv sync --quiet 2>nul || {
    echo "  [INFO] Installing/updating dependencies..."
    uv sync
}

echo ""
echo "3. Starting Backend Services..."

# Start Main Server
echo "  Starting Main Server (port 8181)..."
uv run python -m src.server.main >../logs/main-server.log 2>&1 &
main_pid=$!
echo "    PID: $main_pid"

# Give main server time to initialize
sleep 5

# Verify main server started
curl -s http://localhost:8181/health >nul 2>&1
if [ $? -ne 0 ]; then
    echo "    [ERROR] Main Server failed to start"
    echo "    Check logs/main-server.log for details"
    echo "    Common issues: Missing dependencies, port already in use"
else
    echo "    [SUCCESS] Main Server is running"
fi

# Start MCP Server
echo "  Starting MCP Server (port 8051)..."
uv run python -m src.mcp.mcp_server >../logs/mcp-server.log 2>&1 &
mcp_pid=$!
echo "    PID: $mcp_pid"

sleep 3

# MCP server doesn't have a /health endpoint, so we check the MCP endpoint
curl -s http://localhost:8051/mcp >nul 2>&1
echo "    [INFO] MCP Server started (check logs/mcp-server.log for status)"

# Start Agents Service
echo "  Starting Agents Service (port 8052)..."
uv run python -m src.agents.server >../logs/agents-server.log 2>&1 &
agents_pid=$!
echo "    PID: $agents_pid"

sleep 3

# Agents service may take time to initialize
echo "    [INFO] Agents Service started (may take time to fully initialize)"

# Return to root directory
cd ..

# Start Frontend
echo ""
echo "4. Starting Frontend..."

# Navigate to frontend directory
cd archon-ui-main 2>nul || {
    echo "  [ERROR] Cannot find archon-ui-main directory"
    echo "  Make sure you're in the Archon project root"
    exit 1
}

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "  [WARNING] Dependencies not installed"
    echo "  Running: npm install"
    npm install || {
        echo "  [ERROR] Failed to install dependencies"
        exit 1
    }
fi

echo "  Starting Frontend development server..."
npm run dev >../logs/frontend.log 2>&1 &
frontend_pid=$!
echo "    PID: $frontend_pid"

cd ..

# Wait for frontend to start
echo ""
echo "5. Waiting for services to initialize..."
sleep 8

# Find which port the frontend actually started on
frontend_port=""
for port in 5173 5174 5175 3737; do
    curl -s http://localhost:$port >nul 2>&1
    if [ $? -eq 0 ]; then
        frontend_port=$port
        break
    fi
done

# Final status check
echo ""
echo "6. Service Status:"
echo "==========================================="

# Check Main Server
curl -s http://localhost:8181/health >nul 2>&1
if [ $? -eq 0 ]; then
    echo "[SUCCESS] Main Server: http://localhost:8181"
else
    echo "[ERROR] Main Server: NOT RESPONDING"
    echo "  Check logs/main-server.log for details"
fi

# Check MCP Server status via main server API
mcp_status=$(curl -s http://localhost:8181/api/mcp/status 2>nul | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$mcp_status" = "running" ]; then
    echo "[SUCCESS] MCP Server: http://localhost:8051 (Local mode)"
else
    echo "[WARNING] MCP Server: Status unknown"
    echo "  Check logs/mcp-server.log for details"
fi

# Check Agents Service (may still be initializing)
curl -s http://localhost:8052/health >nul 2>&1
if [ $? -eq 0 ]; then
    echo "[SUCCESS] Agents Service: http://localhost:8052"
else
    echo "[INFO] Agents Service: Still initializing"
    echo "  This is normal - it needs API keys configured"
fi

# Check Frontend
if [ ! -z "$frontend_port" ]; then
    echo "[SUCCESS] Frontend: http://localhost:$frontend_port"
else
    echo "[ERROR] Frontend: NOT RESPONDING"
    echo "  Check logs/frontend.log for details"
fi

echo "==========================================="
echo ""
echo "🚀 Archon is starting up!"
echo ""
echo "Open http://localhost:${frontend_port:-5173} in your browser"
echo ""
echo "Logs are available in the logs/ directory:"
echo "  - logs/main-server.log"
echo "  - logs/mcp-server.log"
echo "  - logs/agents-server.log"
echo "  - logs/frontend.log"
echo ""
echo "Note: The Agents Service may take time to fully initialize."
echo "Configure your API keys in Settings to complete setup."
echo ""
echo "Use /archon:stop_app to stop all services"
```

## Description
Launches all Archon microservices for local (non-Docker) development:
- Automatically ensures `DOCKER_ENV=false` is set
- Uses `uv run` to ensure proper Python environment
- Syncs dependencies if needed
- Creates log files for debugging
- Verifies each service starts successfully
- Reports actual ports used (frontend typically on 5173)
- Provides clear status and troubleshooting information

## Prerequisites
- Python 3.12+ with `uv` package manager installed
- Node.js 18+ with npm
- `.env` file with Supabase credentials configured

## First-Time Setup
Before first run:
1. `cd python && uv sync` - Install Python dependencies
2. `cd archon-ui-main && npm install` - Install Node dependencies

## Usage
Type `/archon:start_app` to start all services.

## Troubleshooting
If services fail to start:
1. Check the logs/ directory for error messages
2. Ensure `.env` file has correct Supabase credentials
3. Ensure `DOCKER_ENV=false` is in `.env`
4. Run `/archon:stop_app` to clean up any partial starts
5. Run `cd python && uv sync --reinstall` if dependency errors occur

## Related Commands
- `/archon:stop_app`: Stop all Archon services