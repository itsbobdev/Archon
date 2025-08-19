"""
MCP Server for Archon (Microservices Version)

This is the MCP server that uses HTTP calls to other services
instead of importing heavy dependencies directly. This significantly reduces
the container size from 1.66GB to ~150MB.

Modules:
- RAG Module: RAG queries, search, and source management via HTTP
- Project Module: Task and project management via HTTP
- Health & Session: Local operations

Note: Crawling and document upload operations are handled directly by the
API service and frontend, not through MCP tools.
"""

import json
import logging
import os
import sys
import threading
import time
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from mcp.server.fastmcp import Context, FastMCP

# Add the project root to Python path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load environment variables from the project root .env file
project_root = Path(__file__).resolve().parent.parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path, override=True)

# Configure logging FIRST before any imports that might use it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/mcp_server.log", mode="a")
        if os.path.exists("/tmp")
        else logging.NullHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Import Logfire configuration
from src.server.config.logfire_config import mcp_logger, setup_logfire

# Import service client for HTTP calls
from src.server.services.mcp_service_client import get_mcp_service_client

# Import session management
from src.server.services.mcp_session_manager import get_session_manager

# Global initialization lock and flag
_initialization_lock = threading.Lock()
_initialization_complete = False
_shared_context = None

server_host = "0.0.0.0"  # Listen on all interfaces

# Require ARCHON_MCP_PORT to be set
mcp_port = os.getenv("ARCHON_MCP_PORT")
if not mcp_port:
    raise ValueError(
        "ARCHON_MCP_PORT environment variable is required. "
        "Please set it in your .env file or environment. "
        "Default value: 8051"
    )
server_port = int(mcp_port)


@dataclass
class ArchonContext:
    """
    Context for MCP server.
    No heavy dependencies - just service client for HTTP calls.
    """

    service_client: Any
    health_status: dict = None
    startup_time: float = None

    def __post_init__(self):
        if self.health_status is None:
            self.health_status = {
                "status": "healthy",
                "api_service": False,
                "agents_service": False,
                "last_health_check": None,
            }
        if self.startup_time is None:
            self.startup_time = time.time()


async def perform_health_checks(context: ArchonContext):
    """Perform health checks on dependent services via HTTP."""
    try:
        # Check dependent services
        service_health = await context.service_client.health_check()

        context.health_status["api_service"] = service_health.get("api_service", False)
        context.health_status["agents_service"] = service_health.get("agents_service", False)

        # Overall status
        all_critical_ready = context.health_status["api_service"]

        context.health_status["status"] = "healthy" if all_critical_ready else "degraded"
        context.health_status["last_health_check"] = datetime.now().isoformat()

        if not all_critical_ready:
            logger.warning(f"Health check failed: {context.health_status}")
        else:
            logger.info("Health check passed - dependent services healthy")

    except Exception as e:
        logger.error(f"Health check error: {e}")
        context.health_status["status"] = "unhealthy"
        context.health_status["last_health_check"] = datetime.now().isoformat()


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[ArchonContext]:
    """
    Lifecycle manager - no heavy dependencies.
    """
    global _initialization_complete, _shared_context

    # Quick check without lock
    if _initialization_complete and _shared_context:
        logger.info("♻️ Reusing existing context for new SSE connection")
        yield _shared_context
        return

    # Acquire lock for initialization
    with _initialization_lock:
        # Double-check pattern
        if _initialization_complete and _shared_context:
            logger.info("♻️ Reusing existing context for new SSE connection")
            yield _shared_context
            return

        logger.info("🚀 Starting MCP server...")

        try:
            # Initialize session manager
            logger.info("🔐 Initializing session manager...")
            session_manager = get_session_manager()
            logger.info("✓ Session manager initialized")

            # Initialize service client for HTTP calls
            logger.info("🌐 Initializing service client...")
            service_client = get_mcp_service_client()
            logger.info("✓ Service client initialized")

            # Create context
            context = ArchonContext(service_client=service_client)

            # Perform initial health check
            await perform_health_checks(context)

            logger.info("✓ MCP server ready")

            # Store context globally
            _shared_context = context
            _initialization_complete = True

            yield context

        except Exception as e:
            logger.error(f"💥 Critical error in lifespan setup: {e}")
            logger.error(traceback.format_exc())
            raise
        finally:
            # Clean up resources
            logger.info("🧹 Cleaning up MCP server...")
            logger.info("✅ MCP server shutdown complete")


# Initialize the main FastMCP server with fixed configuration
try:
    logger.info("🏗️ MCP SERVER INITIALIZATION:")
    logger.info("   Server Name: archon-mcp-server")
    logger.info("   Description: MCP server using HTTP calls")

    mcp = FastMCP(
        "archon-mcp-server",
        lifespan=lifespan,
        host=server_host,
        port=server_port,
    )
    logger.info("✓ FastMCP server instance created successfully")

except Exception as e:
    logger.error(f"✗ Failed to create FastMCP server: {e}")
    logger.error(traceback.format_exc())
    raise


# Health check endpoint
@mcp.tool()
async def health_check(ctx: Context) -> str:
    """
    Perform a health check on the MCP server and its dependencies.

    Returns:
        JSON string with current health status
    """
    try:
        # Try to get the lifespan context
        context = getattr(ctx.request_context, "lifespan_context", None)

        if context is None:
            # Server starting up
            return json.dumps({
                "success": True,
                "status": "starting",
                "message": "MCP server is initializing...",
                "timestamp": datetime.now().isoformat(),
            })

        # Server is ready - perform health checks
        if hasattr(context, "health_status") and context.health_status:
            await perform_health_checks(context)

            return json.dumps({
                "success": True,
                "health": context.health_status,
                "uptime_seconds": time.time() - context.startup_time,
                "timestamp": datetime.now().isoformat(),
            })
        else:
            return json.dumps({
                "success": True,
                "status": "ready",
                "message": "MCP server is running",
                "timestamp": datetime.now().isoformat(),
            })

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return json.dumps({
            "success": False,
            "error": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        })


# Session management endpoint
@mcp.tool()
async def session_info(ctx: Context) -> str:
    """
    Get information about the current session and all active sessions.

    Returns:
        JSON string with session information
    """
    try:
        session_manager = get_session_manager()

        # Build session info
        session_info_data = {
            "active_sessions": session_manager.get_active_session_count(),
            "session_timeout": session_manager.timeout,
        }

        # Add server uptime
        context = getattr(ctx.request_context, "lifespan_context", None)
        if context and hasattr(context, "startup_time"):
            session_info_data["server_uptime_seconds"] = time.time() - context.startup_time

        return json.dumps({
            "success": True,
            "session_management": session_info_data,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Session info failed: {e}")
        return json.dumps({
            "success": False,
            "error": f"Failed to get session info: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        })


# Import and register modules
def register_modules():
    """Register all MCP tool modules."""
    logger.info("🔧 Registering MCP tool modules...")

    modules_registered = 0

    # Import and register RAG module (HTTP-based version)
    try:
        from src.mcp.modules.rag_module import register_rag_tools

        register_rag_tools(mcp)
        modules_registered += 1
        logger.info("✓ RAG module registered (HTTP-based)")
    except ImportError as e:
        logger.warning(f"⚠ RAG module not available: {e}")
    except Exception as e:
        logger.error(f"✗ Error registering RAG module: {e}")
        logger.error(traceback.format_exc())

    # Import and register Project module - only if Projects are enabled
    projects_enabled = os.getenv("PROJECTS_ENABLED", "true").lower() == "true"
    if projects_enabled:
        try:
            from src.mcp.modules.project_module import register_project_tools

            register_project_tools(mcp)
            modules_registered += 1
            logger.info("✓ Project module registered (HTTP-based)")
        except ImportError as e:
            logger.warning(f"⚠ Project module not available: {e}")
        except Exception as e:
            logger.error(f"✗ Error registering Project module: {e}")
            logger.error(traceback.format_exc())
    else:
        logger.info("⚠ Project module skipped - Projects are disabled")

    logger.info(f"📦 Total modules registered: {modules_registered}")

    if modules_registered == 0:
        logger.error("💥 No modules were successfully registered!")
        raise RuntimeError("No MCP modules available")


# HTTP JSON-RPC endpoint for standard MCP transport
@mcp.custom_route("/mcp", ["POST"])
async def mcp_http_endpoint(request: Request) -> JSONResponse:
    """
    HTTP JSON-RPC 2.0 endpoint for MCP tools.
    
    This provides standard MCP HTTP transport support alongside SSE.
    """
    try:
        # Parse JSON-RPC request
        body = await request.json()
        logger.info(f"HTTP MCP request: {body}")
        
        # Validate JSON-RPC structure
        if not isinstance(body, dict):
            raise HTTPException(400, "Request must be JSON object")
            
        if body.get("jsonrpc") != "2.0":
            raise HTTPException(400, "Must be JSON-RPC 2.0")
            
        method = body.get("method")
        if not method:
            raise HTTPException(400, "Missing 'method' field")
            
        request_id = body.get("id")
        params = body.get("params", {})
        
        # Get the tool from FastMCP's tool manager
        if method not in mcp._tool_manager._tools:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                    "data": {"available_methods": list(mcp._tool_manager._tools.keys())}
                }
            })
        
        tool_handler = mcp._tool_manager._tools[method]
        
        # Create a mock context for the tool call
        class MockContext:
            def __init__(self):
                self.request_context = type('RequestContext', (), {
                    'lifespan_context': _shared_context
                })()
        
        mock_ctx = MockContext()
        
        # Execute the tool with parameters
        try:
            if params:
                # Call with named parameters
                result = await tool_handler.fn(mock_ctx, **params)
            else:
                # Call with context only
                result = await tool_handler.fn(mock_ctx)
                
            # Return successful JSON-RPC response
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": json.loads(result) if isinstance(result, str) else result
            })
            
        except TypeError as te:
            # Parameter mismatch
            return JSONResponse({
                "jsonrpc": "2.0", 
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Invalid params for {method}: {str(te)}",
                    "data": {"method": method, "params": params}
                }
            })
            
        except Exception as tool_error:
            # Tool execution error
            logger.error(f"Tool {method} execution error: {tool_error}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id, 
                "error": {
                    "code": -32000,
                    "message": f"Tool execution failed: {str(tool_error)}",
                    "data": {"method": method, "error_type": type(tool_error).__name__}
                }
            })
            
    except json.JSONDecodeError:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": "Parse error: Invalid JSON"
            }
        })
        
    except HTTPException as he:
        return JSONResponse({
            "jsonrpc": "2.0", 
            "id": body.get("id") if 'body' in locals() else None,
            "error": {
                "code": -32600,
                "message": he.detail
            }
        })
        
    except Exception as e:
        logger.error(f"HTTP MCP endpoint error: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id") if 'body' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        })


# Add CORS and health endpoint for HTTP transport  
@mcp.custom_route("/mcp", ["GET"])
async def mcp_http_info(request: Request) -> JSONResponse:
    """
    GET endpoint for MCP HTTP transport info and health check.
    """
    return JSONResponse({
        "name": "archon-mcp-server",
        "description": "Archon MCP server with HTTP and SSE transport support",
        "version": "1.0.0",
        "transports": ["http", "sse"],
        "endpoints": {
            "http": "/mcp",
            "sse": "/sse"
        },
        "tools": list(mcp._tool_manager._tools.keys()),
        "status": "ready"
    })


# Register all modules when this file is imported
try:
    register_modules()
    logger.info("✓ HTTP JSON-RPC endpoints added via decorators")
    
except Exception as e:
    logger.error(f"💥 Critical error during module registration: {e}")
    logger.error(traceback.format_exc())
    raise


def main():
    """Main entry point for the MCP server."""
    try:
        # Initialize Logfire first
        setup_logfire(service_name="archon-mcp-server")

        logger.info("🚀 Starting Archon MCP Server")
        logger.info("   Mode: SSE + HTTP JSON-RPC")
        logger.info(f"   SSE URL: http://{server_host}:{server_port}/sse")
        logger.info(f"   HTTP URL: http://{server_host}:{server_port}/mcp")

        mcp_logger.info("🔥 Logfire initialized for MCP server")
        mcp_logger.info(f"🌟 Starting MCP server - host={server_host}, port={server_port}")

        mcp.run(transport="sse")

    except Exception as e:
        mcp_logger.error(f"💥 Fatal error in main - error={str(e)}, error_type={type(e).__name__}")
        logger.error(f"💥 Fatal error in main: {e}")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 MCP server stopped by user")
    except Exception as e:
        logger.error(f"💥 Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
