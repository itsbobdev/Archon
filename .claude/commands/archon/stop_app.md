# Stop Archon Application

Stop all Archon services including frontend, main server, MCP server, and agents service.

## Command
```powershell
# Primary method - Windows PowerShell script (most reliable)
./stop_app.ps1

# Alternative method - Bash script for Unix/WSL
./stop_app.sh
```

## Description
Robustly stops all Archon microservices for non-Docker environments using platform-specific methods:

**PowerShell Script (stop_app.ps1) - Recommended for Windows:**
- Uses Windows-native process management (netstat, WMI, Stop-Process)
- Handles process trees and child processes correctly
- Provides graceful shutdown with force kill fallback
- Comprehensive process pattern matching
- Built-in endpoint verification

**Bash Script (stop_app.sh) - Unix/Linux/WSL:**
- Multi-method port detection (netstat, ss, lsof)
- Graceful then force termination
- Pattern-based process cleanup
- Cross-platform compatibility

## Usage
Type `/archon:stop_app` to stop all Archon services.

## Troubleshooting
If services don't stop:
1. **First**: Try the PowerShell script: `./stop_app.ps1`
2. **Second**: Run the script again (handles process spawning races)
3. **Manual check**: 
   - Windows: Task Manager or `Get-Process python, node`
   - Unix: `ps aux | grep -E '(python.*src|node.*vite)'`
4. **Force kill specific PIDs**:
   - Windows: `Stop-Process -Id <PID> -Force`
   - Unix: `kill -9 <PID>`
5. **Admin privileges**: Run terminal as Administrator on Windows

## Why Multiple Attempts Were Needed Previously

The original issue was caused by:
1. **Process Tree Complexity**: Python/Node processes spawn children that aren't tracked by simple PID killing
2. **Windows vs Unix Tools**: The bash script used Unix commands not available on Windows
3. **Race Conditions**: New processes spawning while others are being killed
4. **Socket Lag**: Windows shows ports as "in use" even after processes terminate

The PowerShell script solves these by using Windows-native process management and comprehensive pattern matching.

## Related Commands
- `/archon:start_app`: Start all Archon services