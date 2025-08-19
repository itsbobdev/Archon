# Start Archon Application

Launch all Archon services including frontend, main server, MCP server, and agents service.

## Command
```bash
# Run the robust startup script
./start_app.sh
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