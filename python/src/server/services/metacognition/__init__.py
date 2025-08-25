"""
Meta-Cognition Service for Archon

This module provides debugging knowledge capture and learning functionality
integrated with Archon's knowledge base system.
"""

from .session_analyzer import analyze_current_session
from .learning_formatter import create_learning_entries, SynopsisGenerator
from .knowledge_storage import (
    save_learning_file,
    store_in_archon_knowledge_base,
    list_learning_files,
    load_learning_file
)

__all__ = [
    'analyze_current_session',
    'create_learning_entries',
    'SynopsisGenerator',
    'save_learning_file',
    'store_in_archon_knowledge_base',
    'list_learning_files',
    'load_learning_file'
]