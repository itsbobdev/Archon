"""
Knowledge Storage Module for Meta-Cognition Layer

Creates structured markdown files from learning entries and integrates
with Archon's Supabase knowledge base for unified search and retrieval.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


def save_learning_file(learning_entries: List[Dict[str, Any]], session_id: str = None) -> str:
    """
    Save learning entries to a structured markdown file.
    
    Args:
        learning_entries: List of structured learning entry dictionaries
        session_id: Optional session ID, will be generated if not provided
        
    Returns:
        Full filepath of the created markdown file
    """
    if not learning_entries:
        raise ValueError("No learning entries provided to save")
    
    # Generate session metadata
    if not session_id:
        timestamp = datetime.now()
        session_id = f"claude-code-{timestamp.strftime('%Y%m%d-%H%M%S')}"
    else:
        # Extract timestamp from session_id or use current time
        try:
            timestamp_str = session_id.split('-')[-1]
            timestamp = datetime.strptime(timestamp_str, '%H%M%S')
            timestamp = timestamp.replace(
                year=datetime.now().year,
                month=datetime.now().month, 
                day=datetime.now().day
            )
        except:
            timestamp = datetime.now()
    
    # Get project context
    project_name = os.path.basename(os.getcwd())
    
    # Generate filename - store in Archon's knowledge directory
    filename = f"learning-{timestamp.strftime('%Y%m%d-%H%M%S')}.md"
    
    # Use Archon's knowledge directory structure
    knowledge_dir = Path(__file__).parent.parent.parent.parent.parent / "knowledge" / "metacognition"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = knowledge_dir / filename
    
    # Generate markdown content
    markdown_content = _generate_markdown_content(
        session_id=session_id,
        project_name=project_name,
        start_time=timestamp.isoformat(),
        learning_entries=learning_entries
    )
    
    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    logger.info(f"[SUCCESS] Saved learning file: {filepath}")
    return str(filepath.absolute())


def get_learning_file_paths(learning_entries: List[Dict[str, Any]], session_id: str = None) -> Dict[str, str]:
    """
    Get both absolute and relative paths for a learning file without creating it.
    
    Args:
        learning_entries: List of structured learning entry dictionaries
        session_id: Optional session ID, will be generated if not provided
        
    Returns:
        Dictionary with 'absolute' and 'relative' file paths
    """
    if not learning_entries:
        raise ValueError("No learning entries provided")
    
    # Generate session metadata (same logic as save_learning_file)
    if not session_id:
        timestamp = datetime.now()
    else:
        try:
            timestamp_str = session_id.split('-')[-1]
            timestamp = datetime.strptime(timestamp_str, '%H%M%S')
            timestamp = timestamp.replace(
                year=datetime.now().year,
                month=datetime.now().month, 
                day=datetime.now().day
            )
        except:
            timestamp = datetime.now()
    
    # Generate filename and paths
    filename = f"learning-{timestamp.strftime('%Y%m%d-%H%M%S')}.md"
    
    knowledge_dir = Path(__file__).parent.parent.parent.parent.parent / "knowledge" / "metacognition"
    filepath = knowledge_dir / filename
    
    # Get project root for relative path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    relative_path = filepath.relative_to(project_root)
    
    return {
        "absolute": str(filepath.absolute()),
        "relative": str(relative_path),
        "filename": filename
    }


async def store_in_archon_knowledge_base(
    learning_entries: List[Dict[str, Any]], 
    session_id: str,
    service_client: Any = None
) -> List[Dict[str, Any]]:
    """
    Store learning entries in Archon's Supabase knowledge base.
    
    Args:
        learning_entries: List of structured learning entries
        session_id: Session identifier
        service_client: Archon service client for database operations
        
    Returns:
        List of storage results with document IDs
    """
    if not service_client:
        logger.warning("[WARNING] Service client not provided, skipping Archon storage")
        return []
    
    storage_results = []
    
    for entry in learning_entries:
        try:
            # Format content for Archon's knowledge base
            content = _format_entry_for_archon(entry, session_id)
            
            # Store via service client
            result = await service_client.store_knowledge(
                content=content["content"],
                title=content["title"],
                source_type="metacognition",
                metadata={
                    "session_id": session_id,
                    "entry_id": entry.get("id"),
                    "trigger": entry.get("trigger"),
                    "timestamp": entry.get("timestamp", datetime.now().isoformat()),
                    "version": entry.get("version", 2),
                    "has_synopsis": "synopsis" in entry
                }
            )
            
            storage_results.append({
                "entry_id": entry.get("id"),
                "document_id": result.get("document_id", str(uuid.uuid4())),
                "status": "success"
            })
            
            logger.info(f"[SUCCESS] Stored entry {entry.get('id')} in Archon knowledge base")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to store entry {entry.get('id')}: {e}")
            storage_results.append({
                "entry_id": entry.get("id"),
                "status": "failed",
                "error": str(e)
            })
    
    return storage_results


def _generate_markdown_content(session_id: str, project_name: str, start_time: str, 
                             learning_entries: List[Dict[str, Any]]) -> str:
    """
    Generate markdown content following the exact PRD format.
    
    Args:
        session_id: Unique session identifier
        project_name: Name of the current project
        start_time: ISO timestamp string
        learning_entries: List of learning entry dictionaries
        
    Returns:
        Complete markdown content as string
    """
    lines = []
    
    # Header section
    lines.append("# Session Learning Log")
    lines.append(f"**Session ID**: {session_id}")
    lines.append(f"**Project**: {project_name}")
    lines.append(f"**Start Time**: {start_time}")
    lines.append("")
    
    # Learning entries
    for i, entry in enumerate(learning_entries, 1):
        lines.extend(_format_learning_entry(entry, entry_number=i))
        
        # Add separator between entries (except after the last one)
        if i < len(learning_entries):
            lines.append("---")
            lines.append("")
    
    return "\n".join(lines)


def _format_learning_entry(entry: Dict[str, Any], entry_number: int) -> List[str]:
    """
    Format a single learning entry into markdown following PRD format.
    
    Args:
        entry: Learning entry dictionary
        entry_number: Entry number for display
        
    Returns:
        List of markdown lines for this entry
    """
    lines = []
    
    # Entry header
    lines.append(f"## Learning Entry {entry_number}")
    lines.append(f"**ID**: {entry.get('id', f'L{entry_number:03d}')}")
    lines.append(f"**Timestamp**: {entry.get('timestamp', datetime.now().isoformat())}")
    lines.append(f"**Trigger**: {entry.get('trigger', 'investigation')}")
    lines.append("")
    
    # Situation section
    situation = entry.get('situation', {})
    lines.append("### Situation")
    lines.append(f"**Goal**: {situation.get('goal', 'Goal not specified')}")
    lines.append(f"**Action Taken**: {situation.get('action_taken', 'Action not specified')}")
    lines.append(f"**Expected Result**: {situation.get('expected_result', 'Expected result not specified')}")
    lines.append(f"**Actual Result**: {situation.get('actual_result', 'Actual result not specified')}")
    lines.append("")
    
    # Debug Journey section
    debug_journey = entry.get('debug_journey', {})
    lines.append("### Debug Journey")
    lines.append(f"**Initial Hypothesis**: {debug_journey.get('initial_hypothesis', 'Initial hypothesis not specified')}")
    
    # Investigation Path
    lines.append("**Investigation Path**:")
    investigation_path = debug_journey.get('investigation_path', [])
    if investigation_path:
        for i, step in enumerate(investigation_path, 1):
            lines.append(f"{i}. {step}")
    else:
        lines.append("1. Investigation steps not documented")
    lines.append("")
    
    # Dead Ends
    lines.append("**Dead Ends**:")
    dead_ends = debug_journey.get('dead_ends', [])
    if dead_ends:
        for dead_end in dead_ends:
            lines.append(f"- {dead_end}")
    else:
        lines.append("- No dead ends documented")
    lines.append("")
    
    # Resolution section
    resolution = entry.get('resolution', {})
    lines.append("### Resolution")
    lines.append(f"**Root Cause**: {resolution.get('root_cause', 'Root cause not identified')}")
    lines.append(f"**Solution**: {resolution.get('solution', 'Solution not specified')}")
    lines.append(f"**Verification**: {resolution.get('verification', 'Verification method not specified')}")
    lines.append("")
    
    # Knowledge Synthesis section
    knowledge_synthesis = entry.get('knowledge_synthesis', {})
    lines.append("### Knowledge Synthesis")
    lines.append(f"**Domain Principle**: {knowledge_synthesis.get('domain_principle', 'Domain principle not identified')}")
    lines.append(f"**Universal Principle**: {knowledge_synthesis.get('universal_principle', 'Universal principle not identified')}")
    lines.append(f"**Pattern Recognition**: {knowledge_synthesis.get('pattern_recognition', 'Pattern not identified')}")
    lines.append(f"**Mental Model**: {knowledge_synthesis.get('mental_model', 'Mental model not specified')}")
    lines.append("")
    
    # Add synopsis section if available (v2 format)
    if 'synopsis' in entry:
        synopsis = entry['synopsis']
        lines.append("### Quick Reference Synopsis")
        if 'bullets' in synopsis:
            bullets = synopsis['bullets']
            lines.append(f"- **Symptoms**: {bullets.get('symptoms', '')}")
            lines.append(f"- **Context**: {bullets.get('context', '')}")
            lines.append(f"- **Root Cause**: {bullets.get('root_cause', '')}")
            lines.append(f"- **Fix**: {bullets.get('fix', '')}")
            lines.append(f"- **Applies When**: {bullets.get('applies_when', '')}")
        lines.append("")
    
    return lines


def _format_entry_for_archon(entry: Dict[str, Any], session_id: str) -> Dict[str, str]:
    """
    Format a learning entry for storage in Archon's knowledge base.
    
    Creates a comprehensive markdown document that includes all the debugging
    context and makes it highly searchable through RAG.
    
    Args:
        entry: Learning entry from meta-cognition
        session_id: Session identifier
        
    Returns:
        Dictionary with formatted content and title
    """
    # Extract key components
    situation = entry.get("situation", {})
    debug_journey = entry.get("debug_journey", {})
    resolution = entry.get("resolution", {})
    knowledge_synthesis = entry.get("knowledge_synthesis", {})
    synopsis = entry.get("synopsis", {})
    
    # Create searchable title
    title = entry.get("title") or synopsis.get("title") if synopsis else None
    if not title:
        title = f"Debug: {situation.get('goal', 'Learning Entry')}"[:120]
    
    # Build comprehensive content for RAG
    content_parts = [
        f"# {title}",
        f"**Session**: {session_id}",
        f"**Entry ID**: {entry.get('id', 'unknown')}",
        f"**Timestamp**: {entry.get('timestamp', datetime.now().isoformat())}",
        f"**Trigger**: {entry.get('trigger', 'investigation')}",
        "",
        "## Problem Context",
        f"**Goal**: {situation.get('goal', 'Not specified')}",
        f"**Action Taken**: {situation.get('action_taken', 'Not specified')}",
        f"**Expected Result**: {situation.get('expected_result', 'Not specified')}",
        f"**Actual Result**: {situation.get('actual_result', 'Not specified')}",
        "",
        "## Investigation Process",
        f"**Initial Hypothesis**: {debug_journey.get('initial_hypothesis', 'Not specified')}",
        "",
        "**Investigation Steps**:"
    ]
    
    # Add investigation steps
    for step in debug_journey.get("investigation_path", []):
        content_parts.append(f"- {step}")
    
    # Add dead ends
    content_parts.extend([
        "",
        "**Dead Ends Encountered**:"
    ])
    for dead_end in debug_journey.get("dead_ends", []):
        content_parts.append(f"- {dead_end}")
    
    # Add resolution
    content_parts.extend([
        "",
        "## Resolution",
        f"**Root Cause**: {resolution.get('root_cause', 'Not identified')}",
        f"**Solution**: {resolution.get('solution', 'Not specified')}",
        f"**Verification**: {resolution.get('verification', 'Not specified')}",
        "",
        "## Key Learnings",
        f"**Domain Principle**: {knowledge_synthesis.get('domain_principle', 'Not identified')}",
        f"**Universal Principle**: {knowledge_synthesis.get('universal_principle', 'Not identified')}",
        f"**Pattern Recognition**: {knowledge_synthesis.get('pattern_recognition', 'Not identified')}",
        f"**Mental Model**: {knowledge_synthesis.get('mental_model', 'Not specified')}"
    ])
    
    # Add synopsis if available
    if synopsis and synopsis.get("bullets"):
        bullets = synopsis["bullets"]
        content_parts.extend([
            "",
            "## Quick Reference",
            f"- **Symptoms**: {bullets.get('symptoms', '')}",
            f"- **Context**: {bullets.get('context', '')}",
            f"- **Root Cause**: {bullets.get('root_cause', '')}",
            f"- **Fix**: {bullets.get('fix', '')}",
            f"- **Applies When**: {bullets.get('applies_when', '')}"
        ])
    
    # Add searchable tags
    content_parts.extend([
        "",
        "---",
        f"Tags: debugging, {entry.get('trigger', 'investigation')}, metacognition, learning, archon",
        f"Source: Meta-Cognition Layer",
        f"Version: {entry.get('version', 2)}"
    ])
    
    return {
        "title": title,
        "content": "\n".join(content_parts)
    }


def load_learning_file(filepath: str) -> Dict[str, Any]:
    """
    Load and parse a learning file back into structured data.
    
    This is a utility function for testing and future phases.
    
    Args:
        filepath: Path to the learning file to load
        
    Returns:
        Dictionary with session metadata and learning entries
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Learning file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Basic parsing
    lines = content.split('\n')
    
    # Extract session metadata
    session_data = {
        "session_id": _extract_field_value(lines, "Session ID"),
        "project": _extract_field_value(lines, "Project"),
        "start_time": _extract_field_value(lines, "Start Time"),
        "learning_entries": []
    }
    
    # Note: Full parsing implementation would be added here for complete entry extraction
    
    return session_data


def _extract_field_value(lines: List[str], field_name: str) -> str:
    """
    Extract field value from markdown lines.
    
    Args:
        lines: List of markdown lines
        field_name: Name of the field to extract
        
    Returns:
        Field value or empty string if not found
    """
    for line in lines:
        if line.startswith(f"**{field_name}**:"):
            return line.split(f"**{field_name}**:")[1].strip()
    return ""


def list_learning_files() -> List[str]:
    """
    List all learning files in the metacognition directory.
    
    Returns:
        List of learning file paths
    """
    knowledge_dir = Path(__file__).parent.parent.parent.parent.parent / "knowledge" / "metacognition"
    
    if not knowledge_dir.exists():
        return []
    
    learning_files = []
    for filename in knowledge_dir.glob("learning-*.md"):
        learning_files.append(str(filename.absolute()))
    
    return sorted(learning_files)