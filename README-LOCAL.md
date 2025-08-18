# Archon Local Setup Guide (No Docker Required)

This guide provides complete instructions for running Archon locally without Docker. Everything you need is included here - no need to reference other documentation.

## Prerequisites

### Required Software

1. **Python 3.12+** with `uv` package manager
   - Download Python: https://www.python.org/downloads/
   - Install `uv` package manager:
     ```bash
     # Windows (PowerShell)
     irm https://astral.sh/uv/install.ps1 | iex
     
     # macOS/Linux
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. **Node.js 18+** and npm
   - Download Node.js: https://nodejs.org/en/download/

3. **Supabase Account** (free tier works)
   - Sign up at: https://supabase.com/
   - Create a new project

### Required API Keys

- **Supabase credentials** (required)
- **OpenAI API Key** (recommended) - Get from: https://platform.openai.com/api-keys
- **Google Gemini API Key** (optional) - Alternative to OpenAI
- **Ollama** (optional) - For local LLM hosting

## Installation & Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/coleam00/archon.git
cd archon
```

### Step 2: Supabase Database Setup

1. **Get Supabase Credentials**:
   - Go to your [Supabase Dashboard](https://supabase.com/dashboard)
   - Select your project
   - Go to Settings → API
   - Copy your `Project URL` and `service_role` key (use the legacy/longer key)

2. **Initialize Database**:
   - In Supabase Dashboard, go to SQL Editor
   - Copy the entire contents of `migration/complete_setup.sql`
   - Paste and execute in SQL Editor
   - This creates all required tables, functions, and initial settings

### Step 3: Environment Configuration

1. **Create Environment File**:
   ```bash
   cp .env.example .env
   ```

2. **Configure .env File** (add your credentials):
   ```bash
   # Required - Supabase Configuration
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_SERVICE_KEY=your-service-key-here
   
   # Required for non-Docker setup
   DOCKER_ENV=false
   
   # Optional but Recommended - API Keys
   OPENAI_API_KEY=your-openai-key-here
   
   # Optional - Service Configuration
   ARCHON_UI_PORT=3737
   ARCHON_SERVER_PORT=8181
   ARCHON_MCP_PORT=8051
   ARCHON_AGENTS_PORT=8052
   HOST=localhost
   LOG_LEVEL=INFO
   
   # Optional - Alternative LLM Providers
   GOOGLE_API_KEY=your-gemini-key-here
   ```

### Step 4: Backend Setup

```bash
# Navigate to Python directory
cd python

# Install ALL dependencies using uv (this creates a virtual environment)
uv sync

# IMPORTANT: If you see any missing dependency errors later, run:
# uv sync --reinstall

# Verify installation
uv run python -c "import fastapi; import psutil; import pydantic_ai; print('All core dependencies installed successfully')"
```

### Step 5: Frontend Setup

```bash
# Navigate to frontend directory
cd archon-ui-main

# Install dependencies
npm install

# Verify installation
npm list react
```

## Running Archon Services

Archon consists of 4 services that need to run simultaneously. Open 4 separate terminal windows/tabs:

### Terminal 1: Main Server (Port 8181)

```bash
cd python
uv run python -m src.server.main
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
🚀 Starting Archon backend...
✅ Credentials initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8181 (Press CTRL+C to quit)
```

### Terminal 2: MCP Server (Port 8051)

```bash
cd python
uv run python -m src.mcp.mcp_server
```

**Expected Output**:
```
INFO:     Started server process [12346]
MCP Server running on http://localhost:8051
```

### Terminal 3: Agents Service (Port 8052)

```bash
cd python
uv run python -m src.agents.server
```

**Expected Output**:
```
INFO:     Started server process [12347]
Agents service running on http://localhost:8052
```

### Terminal 4: Frontend (Port 3737)

```bash
cd archon-ui-main
npm run dev
```

**Expected Output**:
```
  VITE v5.2.0  ready in 1234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Note**: The frontend runs on port 5173 internally but is configured to be accessed on port 3737 via proxy.

## Service URLs

Once all services are running:

- **Web Interface**: http://localhost:5173 (or sometimes 5174/5175 if 5173 is in use)
- **Main API**: http://localhost:8181
- **MCP Server**: http://localhost:8051 (MCP protocol endpoints)
- **Agents Service**: http://localhost:8052

## Initial Configuration

### Step 1: Access Web Interface

1. Open http://localhost:5173 in your browser (check console output for actual port)
2. You should see the Archon dashboard

### Step 2: Configure API Keys

1. Go to **Settings** in the web interface
2. Select your LLM provider (OpenAI, Google, or Ollama)
3. Enter your API key
4. Save settings

### Step 3: Test Setup

1. **Test Knowledge Base**:
   - Go to **Knowledge Base** → **Crawl Website**
   - Enter a documentation URL (e.g., `https://ai.pydantic.dev/llms-full.txt`)
   - Click "Start Crawling"

2. **Test Document Upload**:
   - Go to **Knowledge Base** → **Upload Document**
   - Upload a PDF or text file

3. **Test MCP Integration**:
   - Go to **MCP Dashboard**
   - Check that MCP server shows as "Connected"
   - Copy the configuration for your AI coding assistant

## Environment Variables Reference

### Required Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key-here
```

### Optional Configuration

```bash
# Service Ports
ARCHON_UI_PORT=3737              # Frontend port
ARCHON_SERVER_PORT=8181          # Main API server port
ARCHON_MCP_PORT=8051             # MCP server port
ARCHON_AGENTS_PORT=8052          # Agents service port

# Network
HOST=localhost                   # Host to bind to

# Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR

# API Keys
OPENAI_API_KEY=sk-...           # OpenAI API key
GOOGLE_API_KEY=...              # Google Gemini API key

# Observability (Optional)
LOGFIRE_TOKEN=...               # Logfire token for monitoring
```

### Service Discovery

For local development, the services use environment variable discovery mode automatically when not running in Docker.

## Database Reset (If Needed)

If you need to start fresh:

1. **Reset Database**:
   - In Supabase SQL Editor, run contents of `migration/RESET_DB.sql`
   - Then run `migration/complete_setup.sql` again

2. **Restart Services**:
   - Stop all running services (Ctrl+C in each terminal)
   - Start them again following the "Running Archon Services" section

## Development Commands

### Running Tests

```bash
# Backend tests
cd python
uv run pytest

# Frontend tests
cd archon-ui-main
npm run test

# Frontend tests with coverage
npm run test:coverage
```

### Code Quality

```bash
# Python linting and type checking
cd python
uv run ruff check
uv run mypy src/

# Frontend linting
cd archon-ui-main
npm run lint
```

### Hot Reload Development

All services are configured with hot reload:
- **Backend services**: Use `--reload` flag (already included in commands above)
- **Frontend**: Vite automatically watches for changes

## Troubleshooting

### Service Won't Start

**Problem**: Service fails to start with port in use error
```bash
# Check what's using the port
netstat -ano | findstr :8181  # Windows
lsof -i :8181                 # macOS/Linux

# Kill the process if needed
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                # macOS/Linux
```

**Solution**: Either kill the conflicting process or change ports in `.env`

### Database Connection Issues

**Problem**: `Connection to database failed`

**Check**:
1. Verify Supabase credentials in `.env`
2. Ensure you used the correct (longer) service key
3. Check Supabase project is active
4. Verify you ran `complete_setup.sql`

### MCP Server Connection Issues

**Problem**: MCP shows as disconnected or "Docker_unavailable"

**Check**:
1. Ensure `DOCKER_ENV=false` is set in your `.env` file
2. Ensure MCP server is running on port 8051
3. Check no firewall blocking the port
4. Verify all services started successfully
5. Check service logs for errors
6. Make sure you're using `uv run` to start the services

### Frontend Can't Connect to Backend

**Problem**: Frontend shows connection errors

**Check**:
1. Backend server is running on port 8181
2. No CORS issues in browser console
3. Verify proxy configuration in `vite.config.ts`

### Missing Dependencies

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
# Reinstall Python dependencies
cd python
uv sync --reinstall

# Reinstall Node dependencies
cd archon-ui-main
rm -rf node_modules package-lock.json
npm install
```

### Agents Service Connection Issues

**Problem**: Agents Service shows `getaddrinfo failed` or can't connect to main server

**Check**:
1. Ensure `DOCKER_ENV=false` is set in your `.env` file
2. Ensure Main Server is running and healthy on port 8181
3. The Agents Service needs to fetch credentials from Main Server
4. If you haven't configured API keys in Settings, the service will run but with limited functionality

### Performance Issues

**Problem**: Slow startup or operation

**Tips**:
1. Disable reranking if not needed (edit settings in web interface)
2. Reduce concurrent workers for embeddings
3. Use local Ollama instead of OpenAI for better privacy and potentially lower latency

## Advanced Configuration

### Custom Ports

To use different ports, modify `.env`:

```bash
ARCHON_SERVER_PORT=8282
ARCHON_MCP_PORT=8151
ARCHON_AGENTS_PORT=8152
ARCHON_UI_PORT=3838
```

After changing ports, update the frontend configuration by restarting the frontend service.

### Custom Hostname

To use a custom hostname or IP:

```bash
HOST=192.168.1.100    # Use specific IP
HOST=archon.local     # Use custom domain
```

### RAG Strategy Configuration

Modify these in the web interface Settings or directly in Supabase:

- **USE_HYBRID_SEARCH**: Combines vector + keyword search
- **USE_AGENTIC_RAG**: Code example extraction and specialized search
- **USE_RERANKING**: Cross-encoder reranking for better results
- **USE_CONTEXTUAL_EMBEDDINGS**: Enhanced embeddings with context

### LLM Provider Configuration

**OpenAI** (Default):
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

**Google Gemini**:
```bash
LLM_PROVIDER=google
GOOGLE_API_KEY=...
```

**Ollama** (Local):
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
```

## Connecting AI Coding Assistants

### Claude Code / Claude Desktop

1. Go to **MCP Dashboard** in web interface
2. Copy the MCP server configuration
3. Add to your Claude configuration file

### Cursor / Windsurf

1. Install the MCP extension
2. Configure the connection to `http://localhost:8051`
3. Available tools:
   - `archon:perform_rag_query` - Search knowledge base
   - `archon:search_code_examples` - Find code snippets
   - `archon:manage_project` - Project operations
   - `archon:manage_task` - Task management

## Support

- **GitHub Discussions**: https://github.com/coleam00/Archon/discussions
- **Issues**: https://github.com/coleam00/Archon/issues
- **Contributing**: See CONTRIBUTING.md

## Architecture Summary

Archon uses a microservices architecture:

- **Frontend**: React + TypeScript + Vite + TailwindCSS (Port 3737)
- **Main Server**: FastAPI + Socket.IO for real-time updates (Port 8181)
- **MCP Server**: Lightweight HTTP-based MCP protocol server (Port 8051)
- **Agents Service**: PydanticAI agents for AI/ML operations (Port 8052)
- **Database**: Supabase (PostgreSQL + pgvector for embeddings)

All services communicate via HTTP APIs with Socket.IO for real-time updates between Frontend and Main Server.