"""
Learning Capture Module for Archon MCP Server

This module provides MCP tools that allow external projects (like Claude Code)
to send debugging experiences to Archon for structured storage and retrieval.

Key Features:
- Accepts raw debugging information via MCP
- Structures it into learning entries
- Stores in Archon's knowledge base for RAG retrieval
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from mcp.server.fastmcp import Context

# Import Archon's metacognition components
from src.server.services.metacognition import (
    create_learning_entries,
    save_learning_file,
    store_in_archon_knowledge_base
)

logger = logging.getLogger(__name__)


def register_learning_capture_tools(mcp):
    """
    Register learning capture tools with the MCP server.
    
    Args:
        mcp: FastMCP server instance
    """
    logger.info("[NOTE] Registering Learning Capture module tools...")
    
    @mcp.tool()
    async def capture_learning(
        ctx: Context,
        problem_description: str,
        investigation_steps: List[str] = None,
        solution_applied: str = "",
        outcome: str = "",
        project_context: str = "unknown",
        additional_context: Dict[str, Any] = None
    ) -> str:
        """
        Capture a debugging experience and store it in Archon's knowledge base.
        
        This is the primary MCP tool that external projects call to store their
        debugging experiences. It accepts raw information and structures it into
        a learning entry for future retrieval.
        
        Args:
            problem_description: Description of the problem encountered
            investigation_steps: List of steps taken to investigate (optional)
            solution_applied: The solution that was applied
            outcome: The result of applying the solution
            project_context: Name or context of the project
            additional_context: Any additional metadata or context
            
        Returns:
            JSON string with storage results
        """
        try:
            logger.info(f"[NOTE] Capturing learning for project: {project_context}")
            
            # Generate session ID
            timestamp = datetime.now()
            session_id = f"external-{project_context}-{timestamp.strftime('%Y%m%d-%H%M%S')}"
            
            # Create debugging experience structure
            debugging_experience = {
                "problem_description": problem_description,
                "investigation_steps": investigation_steps or [
                    "Identified the problem",
                    "Investigated potential causes",
                    "Applied solution"
                ],
                "solution_applied": solution_applied or "Solution applied to resolve the issue",
                "outcome": outcome or "Issue resolved successfully"
            }
            
            # Create session data
            session_data = {
                "session_id": session_id,
                "timestamp": timestamp.isoformat(),
                "project_context": project_context,
                "debugging_experiences": [debugging_experience],
                "additional_context": additional_context or {}
            }
            
            # Create structured learning entries
            logger.info("[NOTE] Creating structured learning entries...")
            learning_entries = create_learning_entries(session_data, use_v2_format=True)
            
            if not learning_entries:
                return json.dumps({
                    "success": False,
                    "error": "Failed to create learning entries from provided data"
                })
            
            # Save to markdown file
            logger.info("[NOTE] Saving learning file...")
            markdown_filepath = save_learning_file(learning_entries, session_id)
            logger.info(f"[SUCCESS] Saved to: {markdown_filepath}")
            
            # Store in Archon's knowledge base
            stored_entries = []
            context = getattr(ctx.request_context, "lifespan_context", None)
            
            if context and hasattr(context, "service_client"):
                logger.info("[NOTE] Storing in Archon knowledge base...")
                service_client = context.service_client
                
                for entry in learning_entries:
                    try:
                        # Format for Archon storage
                        archon_content = _format_for_archon_storage(
                            entry, 
                            session_data,
                            problem_description,
                            solution_applied
                        )
                        
                        # Store via service client
                        storage_result = await service_client.store_knowledge(
                            content=archon_content["content"],
                            title=archon_content["title"],
                            source_type="learning_capture",
                            metadata={
                                "session_id": session_id,
                                "entry_id": entry.get("id"),
                                "project_context": project_context,
                                "trigger": entry.get("trigger"),
                                "timestamp": timestamp.isoformat(),
                                "markdown_file": markdown_filepath,
                                **additional_context or {}
                            }
                        )
                        
                        stored_entries.append({
                            "entry_id": entry.get("id"),
                            "document_id": storage_result.get("document_id"),
                            "status": "stored"
                        })
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to store entry {entry.get('id')}: {e}")
                        stored_entries.append({
                            "entry_id": entry.get("id"),
                            "status": "failed",
                            "error": str(e)
                        })
            else:
                logger.warning("[WARNING] Service client not available - only saved to markdown")
            
            # Return results
            result = {
                "success": True,
                "session_id": session_id,
                "entries_created": len(learning_entries),
                "markdown_file": markdown_filepath,
                "archon_storage": stored_entries,
                "message": f"Successfully captured learning from {project_context}"
            }
            
            logger.info(f"[SUCCESS] Learning capture complete: {len(learning_entries)} entries")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"[ERROR] capture_learning failed: {e}")
            logger.error(traceback.format_exc())
            return json.dumps({
                "success": False,
                "error": f"Failed to capture learning: {str(e)}",
                "traceback": traceback.format_exc()
            })
    
    @mcp.tool()
    async def capture_session_learning(
        ctx: Context,
        session_content: str,
        project_name: str = "unknown",
        session_type: str = "debugging",
        tags: List[str] = None
    ) -> str:
        """
        Capture learning from a full session transcript or content.
        
        This tool accepts a complete session transcript (like a Claude Code conversation)
        and extracts debugging experiences from it automatically.
        
        Args:
            session_content: Full session transcript or conversation
            project_name: Name of the project
            session_type: Type of session (debugging, development, analysis)
            tags: Optional tags for categorization
            
        Returns:
            JSON string with extraction and storage results
        """
        try:
            logger.info(f"[NOTE] Processing session content for project: {project_name}")
            
            # Parse session content to extract debugging experiences
            experiences = _extract_experiences_from_content(session_content)
            
            if not experiences:
                # Create a default experience from the session
                experiences = [{
                    "problem_description": f"Session learning from {session_type} session",
                    "investigation_steps": [
                        "Analyzed session content",
                        "Extracted key insights",
                        "Identified patterns and solutions"
                    ],
                    "solution_applied": "Captured session knowledge for future reference",
                    "outcome": "Session learning successfully extracted"
                }]
            
            # Generate session ID
            timestamp = datetime.now()
            session_id = f"session-{project_name}-{timestamp.strftime('%Y%m%d-%H%M%S')}"
            
            # Create session data
            session_data = {
                "session_id": session_id,
                "timestamp": timestamp.isoformat(),
                "project_context": project_name,
                "debugging_experiences": experiences,
                "session_type": session_type,
                "tags": tags or []
            }
            
            # Create structured learning entries
            learning_entries = create_learning_entries(session_data, use_v2_format=True)
            
            # Save to markdown
            markdown_filepath = save_learning_file(learning_entries, session_id)
            
            # Store in Archon
            stored_entries = []
            context = getattr(ctx.request_context, "lifespan_context", None)
            
            if context and hasattr(context, "service_client"):
                service_client = context.service_client
                
                for entry in learning_entries:
                    try:
                        # Create comprehensive content
                        content_parts = [
                            f"# Session Learning: {project_name}",
                            f"**Type**: {session_type}",
                            f"**Session ID**: {session_id}",
                            f"**Tags**: {', '.join(tags) if tags else 'none'}",
                            "",
                            "## Session Context",
                            session_content[:1000] + "..." if len(session_content) > 1000 else session_content,
                            "",
                            _format_learning_entry_content(entry)
                        ]
                        
                        storage_result = await service_client.store_knowledge(
                            content="\n".join(content_parts),
                            title=f"Session Learning: {entry.get('title', project_name)}",
                            source_type="session_capture",
                            metadata={
                                "session_id": session_id,
                                "project_name": project_name,
                                "session_type": session_type,
                                "tags": tags or [],
                                "timestamp": timestamp.isoformat()
                            }
                        )
                        
                        stored_entries.append({
                            "entry_id": entry.get("id"),
                            "document_id": storage_result.get("document_id"),
                            "status": "stored"
                        })
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to store session entry: {e}")
                        stored_entries.append({
                            "entry_id": entry.get("id"),
                            "status": "failed",
                            "error": str(e)
                        })
            
            result = {
                "success": True,
                "session_id": session_id,
                "experiences_found": len(experiences),
                "entries_created": len(learning_entries),
                "markdown_file": markdown_filepath,
                "archon_storage": stored_entries
            }
            
            logger.info(f"[SUCCESS] Session learning captured: {len(experiences)} experiences")
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"[ERROR] capture_session_learning failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Failed to capture session learning: {str(e)}"
            })
    
    @mcp.tool()
    async def search_learning(
        ctx: Context,
        query: str,
        project_filter: str = None,
        max_results: int = 5
    ) -> str:
        """
        Search for debugging knowledge in Archon's learning database.
        
        Args:
            query: Search query for debugging experiences
            project_filter: Optional filter by project name
            max_results: Maximum number of results
            
        Returns:
            JSON string with search results
        """
        try:
            context = getattr(ctx.request_context, "lifespan_context", None)
            if not context or not hasattr(context, "service_client"):
                return json.dumps({
                    "success": False,
                    "error": "Service client not available for search"
                })
            
            service_client = context.service_client
            
            # Build search query
            search_query = query
            if project_filter:
                search_query = f"{query} project:{project_filter}"
            
            # Add learning-specific tags
            search_query += " [source:learning_capture OR source:session_capture OR source:metacognition]"
            
            # Perform search
            search_results = await service_client.search_knowledge(
                query=search_query,
                max_results=max_results
            )
            
            # Format results
            formatted_results = []
            if search_results and search_results.get("results"):
                for result in search_results["results"]:
                    formatted_results.append({
                        "content": result.get("content", "")[:500],
                        "title": result.get("title", ""),
                        "metadata": result.get("metadata", {}),
                        "score": result.get("score", 0)
                    })
            
            return json.dumps({
                "success": True,
                "query": query,
                "project_filter": project_filter,
                "results_count": len(formatted_results),
                "results": formatted_results
            }, indent=2)
            
        except Exception as e:
            logger.error(f"[ERROR] search_learning failed: {e}")
            return json.dumps({
                "success": False,
                "error": f"Search failed: {str(e)}"
            })
    
    logger.info("[SUCCESS] Learning Capture module tools registered")
    return True


def _format_for_archon_storage(
    entry: Dict[str, Any], 
    session_data: Dict[str, Any],
    problem_description: str,
    solution_applied: str
) -> Dict[str, str]:
    """
    Format a learning entry for storage in Archon's knowledge base.
    """
    # Extract components
    situation = entry.get("situation", {})
    debug_journey = entry.get("debug_journey", {})
    resolution = entry.get("resolution", {})
    knowledge_synthesis = entry.get("knowledge_synthesis", {})
    synopsis = entry.get("synopsis", {})
    
    # Create title
    title = synopsis.get("title") if synopsis else f"Learning: {problem_description[:80]}"
    
    # Build content
    content_parts = [
        f"# {title}",
        f"**Project**: {session_data.get('project_context', 'unknown')}",
        f"**Session**: {session_data.get('session_id', 'unknown')}",
        f"**Timestamp**: {entry.get('timestamp', datetime.now().isoformat())}",
        "",
        "## Problem",
        problem_description,
        "",
        "## Investigation",
    ]
    
    # Add investigation steps
    for step in debug_journey.get("investigation_path", []):
        content_parts.append(f"- {step}")
    
    content_parts.extend([
        "",
        "## Solution",
        solution_applied or resolution.get("solution", "Solution implemented"),
        "",
        "## Key Learnings",
        f"- **Domain**: {knowledge_synthesis.get('domain_principle', '')}",
        f"- **Universal**: {knowledge_synthesis.get('universal_principle', '')}",
        f"- **Pattern**: {knowledge_synthesis.get('pattern_recognition', '')}",
        "",
        "---",
        "Tags: learning, debugging, " + session_data.get('project_context', 'unknown')
    ])
    
    return {
        "title": title,
        "content": "\n".join(content_parts)
    }


def _extract_experiences_from_content(content: str) -> List[Dict[str, Any]]:
    """
    Extract debugging experiences from session content.
    """
    import re
    
    experiences = []
    
    # Look for error patterns
    error_patterns = [
        r"error[:\s]+(.*?)(?:\n|$)",
        r"exception[:\s]+(.*?)(?:\n|$)",
        r"failed[:\s]+(.*?)(?:\n|$)",
        r"issue[:\s]+(.*?)(?:\n|$)",
        r"problem[:\s]+(.*?)(?:\n|$)"
    ]
    
    for pattern in error_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            description = match.group(1).strip()
            if description and len(description) > 10:  # Meaningful description
                # Look for solution near the error
                solution = _find_nearby_solution(content, match.start())
                
                experiences.append({
                    "problem_description": description,
                    "investigation_steps": [
                        "Identified the error",
                        "Analyzed the context",
                        "Investigated potential causes"
                    ],
                    "solution_applied": solution or "Applied appropriate fix",
                    "outcome": "Issue resolved"
                })
                
                # Limit to first 5 experiences
                if len(experiences) >= 5:
                    break
        
        if len(experiences) >= 5:
            break
    
    return experiences


def _find_nearby_solution(content: str, error_position: int) -> Optional[str]:
    """
    Look for solution patterns near an error position.
    """
    # Look ahead for solution keywords
    search_window = content[error_position:error_position + 500]
    
    solution_patterns = [
        r"fixed[:\s]+(.*?)(?:\n|$)",
        r"solution[:\s]+(.*?)(?:\n|$)",
        r"resolved[:\s]+(.*?)(?:\n|$)",
        r"by\s+(.*?)(?:\n|$)"
    ]
    
    for pattern in solution_patterns:
        match = re.search(pattern, search_window, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None


def _format_learning_entry_content(entry: Dict[str, Any]) -> str:
    """
    Format a learning entry as markdown content.
    """
    lines = []
    
    # Add main sections
    situation = entry.get("situation", {})
    if situation:
        lines.extend([
            "## Situation",
            f"- Goal: {situation.get('goal', '')}",
            f"- Action: {situation.get('action_taken', '')}",
            f"- Expected: {situation.get('expected_result', '')}",
            f"- Actual: {situation.get('actual_result', '')}",
            ""
        ])
    
    resolution = entry.get("resolution", {})
    if resolution:
        lines.extend([
            "## Resolution",
            f"- Root Cause: {resolution.get('root_cause', '')}",
            f"- Solution: {resolution.get('solution', '')}",
            f"- Verification: {resolution.get('verification', '')}",
            ""
        ])
    
    knowledge = entry.get("knowledge_synthesis", {})
    if knowledge:
        lines.extend([
            "## Knowledge Synthesis",
            f"- Domain: {knowledge.get('domain_principle', '')}",
            f"- Universal: {knowledge.get('universal_principle', '')}",
            f"- Pattern: {knowledge.get('pattern_recognition', '')}",
            ""
        ])
    
    return "\n".join(lines)