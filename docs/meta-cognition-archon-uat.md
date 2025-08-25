# Meta-Cognition Learning Capture - User Acceptance Testing Guide

## Overview

This guide provides step-by-step instructions to test the Learning Capture functionality in Archon's MCP server. Follow these steps to verify that debugging experiences can be captured, stored, and retrieved successfully.

## System Architecture & Flow

### Components Involved

1. **MCP Server** (Port 8051)
   - FastMCP framework handling HTTP/JSON-RPC requests
   - Learning Capture module (`learning_capture_module.py`)
   
2. **Metacognition Service** (`src/server/services/metacognition/`)
   - `session_analyzer.py` - Analyzes and structures raw input
   - `learning_formatter.py` - Creates structured learning entries with synopsis
   - `knowledge_storage.py` - Handles file and database storage

3. **Service Client**
   - HTTP client for communicating with Archon API server
   - Handles Supabase storage operations

4. **Storage Systems**
   - Local filesystem: `knowledge/metacognition/` for markdown files
   - Supabase database: For RAG-searchable documents

### Expected Processing Flow

When a debugging experience is sent to Archon:

```
1. HTTP Request → MCP Server (port 8051)
   ↓
2. MCP Server → Routes to Learning Capture Module
   ↓
3. Learning Capture Module → Validates input parameters
   ↓
4. Session Analyzer → Creates session data structure
   - Generates session ID (e.g., "external-project-20250113-143052")
   - Adds timestamp and project context
   - Wraps raw input into debugging_experiences array
   ↓
5. Learning Formatter → Processes session data
   - Determines trigger type (error/performance/investigation)
   - Extracts situation details (goal, actions, results)
   - Creates debug journey (hypothesis, steps, dead ends)
   - Generates resolution (root cause, solution, verification)
   - Synthesizes knowledge (domain/universal principles)
   - Creates synopsis (v2 format with bullets)
   ↓
6. Knowledge Storage → Saves to filesystem
   - Generates markdown file with PRD format
   - Creates file in knowledge/metacognition/
   - Returns absolute file path
   ↓
7. Archon Integration → Stores in Supabase
   - Formats entry for Archon storage
   - Calls service_client.store_knowledge()
   - Adds metadata (session_id, project_context, tags)
   - Returns document ID
   ↓
8. Response → Returns JSON with results
   - Success status
   - Session ID
   - File path
   - Storage results
```

### Detailed Logic Steps

#### Step 1: Request Reception
- MCP server receives POST request at `/mcp`
- Validates JSON-RPC 2.0 format
- Extracts method name and parameters

#### Step 2: Tool Routing
- Identifies `capture_learning` method
- Passes to registered tool handler
- Extracts context from request

#### Step 3: Data Structuring
```python
# Creates session data structure:
session_data = {
    "session_id": "external-{project}-{timestamp}",
    "timestamp": "ISO-8601 timestamp",
    "project_context": "provided project name",
    "debugging_experiences": [{
        "problem_description": "user provided",
        "investigation_steps": ["user provided list"],
        "solution_applied": "user provided",
        "outcome": "user provided"
    }]
}
```

#### Step 4: Learning Entry Creation
```python
# Learning formatter creates comprehensive entry:
learning_entry = {
    "id": "L001",
    "timestamp": "ISO timestamp",
    "trigger": "error|performance|investigation",
    "situation": {
        "goal": "inferred from problem",
        "action_taken": "extracted from steps",
        "expected_result": "inferred",
        "actual_result": "from problem description"
    },
    "debug_journey": {
        "initial_hypothesis": "from first step",
        "investigation_path": ["cleaned steps"],
        "dead_ends": ["identified failures"]
    },
    "resolution": {
        "root_cause": "inferred from solution",
        "solution": "provided solution",
        "verification": "from outcome"
    },
    "knowledge_synthesis": {
        "domain_principle": "technology-specific",
        "universal_principle": "transferable",
        "pattern_recognition": "reusable indicators",
        "mental_model": "conceptual understanding"
    },
    "synopsis": {
        "title": "max 120 chars",
        "bullets": {
            "symptoms": "what went wrong",
            "context": "environment",
            "root_cause": "why it happened",
            "fix": "solution applied",
            "applies_when": "usage pattern"
        }
    }
}
```

#### Step 5: Markdown Generation
- Creates structured markdown following PRD format
- Includes all sections: Situation, Debug Journey, Resolution, Knowledge Synthesis
- Adds Quick Reference Synopsis for v2 format
- Saves to `knowledge/metacognition/learning-YYYYMMDD-HHMMSS.md`

#### Step 6: Supabase Storage
- Formats content for RAG optimization
- Adds searchable tags and metadata
- Stores via service client HTTP call to API server
- API server saves to Supabase documents table

#### Step 7: Search Processing
When searching for learning:
```
1. Search request → MCP Server
2. Build enhanced query with source filters
3. Service client → API server → Supabase
4. Vector similarity search + full-text search
5. Results ranked by relevance score
6. Formatted results returned to caller
```

### No Agents Involved

**Note**: This implementation does NOT use AI agents. All processing is deterministic:
- Pattern matching for trigger detection
- Rule-based extraction for situation details
- Template-based formatting for output
- No LLM calls or AI agent orchestration

The "intelligence" comes from:
- Structured data format enforcement
- Pattern recognition in problem descriptions
- Heuristic-based inference for missing fields
- Comprehensive template for knowledge synthesis

## Prerequisites

1. **Archon Services Running**:
   - Archon UI running on port 3737
   - Archon API server running on port 8181
   - Archon MCP server running on port 8051
   - Supabase connection configured in `.env`

2. **Test Environment**:
   - Terminal/Command Prompt for curl commands
   - Text editor to view generated files
   - Access to Archon UI at http://localhost:3737

## Test Scenarios

### Scenario 1: Basic Learning Capture

**Objective**: Verify that a single debugging experience can be captured and stored.

#### Step 1.1: Start MCP Server (if not running)

```bash
# Navigate to Archon python directory
cd D:\D drive\GitHub\Archon\python

# Start the MCP server
python -m src.mcp.mcp_server
```

**Expected Result**:
- Server starts on port 8051
- Log shows: "✓ Learning Capture module registered"
- Log shows: "🌟 Starting MCP server - host=0.0.0.0, port=8051"

#### Step 1.2: Verify MCP Server Health

```bash
curl http://localhost:8051/health
```

**Expected Result**:
```json
{
  "status": "healthy",
  "service": "archon-mcp-server",
  "timestamp": "2025-01-13T14:30:00",
  "ready": true
}
```

#### Step 1.3: Send a Test Debugging Experience

```bash
curl -X POST http://localhost:8051/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\": \"2.0\", \"id\": \"test-1\", \"method\": \"capture_learning\", \"params\": {\"problem_description\": \"ImportError: No module named requests even though requests is installed\", \"investigation_steps\": [\"Checked if requests is installed with pip list\", \"Verified Python version matches pip version\", \"Discovered virtual environment was not activated\"], \"solution_applied\": \"Activated the virtual environment before running the script\", \"outcome\": \"Script ran successfully with all imports working\", \"project_context\": \"test-python-project\", \"additional_context\": {\"language\": \"python\", \"error_type\": \"import_error\", \"python_version\": \"3.10\"}}}"
```

**For Unix/Mac**:
```bash
curl -X POST http://localhost:8051/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "capture_learning",
    "params": {
      "problem_description": "ImportError: No module named requests even though requests is installed",
      "investigation_steps": [
        "Checked if requests is installed with pip list",
        "Verified Python version matches pip version",
        "Discovered virtual environment was not activated"
      ],
      "solution_applied": "Activated the virtual environment before running the script",
      "outcome": "Script ran successfully with all imports working",
      "project_context": "test-python-project",
      "additional_context": {
        "language": "python",
        "error_type": "import_error",
        "python_version": "3.10"
      }
    }
  }'
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "id": "test-1",
  "result": {
    "success": true,
    "session_id": "external-test-python-project-20250113-143052",
    "entries_created": 1,
    "markdown_file": "D:\\D drive\\GitHub\\Archon\\knowledge\\metacognition\\learning-20250113-143052.md",
    "archon_storage": [
      {
        "entry_id": "L001",
        "document_id": "uuid-xxxx",
        "status": "stored"
      }
    ],
    "message": "Successfully captured learning from test-python-project"
  }
}
```

#### Step 1.4: Verify Markdown File Created

Navigate to: `D:\D drive\GitHub\Archon\knowledge\metacognition\`

**Expected Result**:
- A new file named `learning-YYYYMMDD-HHMMSS.md` exists
- Opening the file shows structured learning entry with:
  - Session header with ID and timestamp
  - Learning Entry with Situation, Debug Journey, Resolution, and Knowledge Synthesis sections
  - All provided information properly formatted

#### Step 1.5: Verify Supabase Storage

Open Archon UI at http://localhost:3737 and navigate to Knowledge page.

**Expected Result**:
- New entry appears in knowledge items list
- Source type shows as "learning_capture"
- Can search for "ImportError requests" and find the entry

---

### Scenario 2: Session Learning Capture

**Objective**: Test capturing learning from a full session transcript.

#### Step 2.1: Send Session Content

```bash
curl -X POST http://localhost:8051/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\": \"2.0\", \"id\": \"test-2\", \"method\": \"capture_session_learning\", \"params\": {\"session_content\": \"User: I am getting TypeError: Cannot read property length of undefined in my React component.\\nAssistant: This error occurs when you try to access the length property of a variable that is undefined. Let me help you debug this.\\nUser: The error happens in my map function when rendering a list.\\nAssistant: The issue is likely that your data hasn't loaded yet. You should add a check before mapping.\\nUser: Adding a conditional check with data && data.map() fixed it!\\nAssistant: Great! This is a common pattern in React - always check if data exists before accessing its properties.\", \"project_name\": \"react-todo-app\", \"session_type\": \"debugging\", \"tags\": [\"react\", \"javascript\", \"type-error\"]}}"
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "id": "test-2",
  "result": {
    "success": true,
    "session_id": "session-react-todo-app-20250113-144523",
    "experiences_found": 1,
    "entries_created": 1,
    "markdown_file": "D:\\D drive\\GitHub\\Archon\\knowledge\\metacognition\\learning-20250113-144523.md",
    "archon_storage": [
      {
        "entry_id": "L001",
        "document_id": "uuid-yyyy",
        "status": "stored"
      }
    ]
  }
}
```

---

### Scenario 3: Search Learning Database

**Objective**: Verify that stored learning can be searched and retrieved.

#### Step 3.1: Search for Python Import Error

```bash
curl -X POST http://localhost:8051/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\": \"2.0\", \"id\": \"test-3\", \"method\": \"search_learning\", \"params\": {\"query\": \"ImportError module requests\", \"max_results\": 5}}"
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "id": "test-3",
  "result": {
    "success": true,
    "query": "ImportError module requests",
    "project_filter": null,
    "results_count": 1,
    "results": [
      {
        "content": "# Learning: ImportError: No module named requests...",
        "title": "Learning: ImportError: No module named requests even though requests is installed",
        "metadata": {
          "session_id": "external-test-python-project-20250113-143052",
          "project_context": "test-python-project",
          "language": "python"
        },
        "score": 0.89
      }
    ]
  }
}
```

#### Step 3.2: Search for React Type Error

```bash
curl -X POST http://localhost:8051/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\": \"2.0\", \"id\": \"test-4\", \"method\": \"search_learning\", \"params\": {\"query\": \"TypeError undefined React\", \"project_filter\": \"react-todo-app\"}}"
```

**Expected Result**:
- Returns the React debugging entry from Scenario 2
- Project filter correctly limits results to "react-todo-app"

---

### Scenario 4: Error Handling

**Objective**: Verify proper error handling for invalid inputs.

#### Step 4.1: Missing Required Parameter

```bash
curl -X POST http://localhost:8051/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\": \"2.0\", \"id\": \"test-5\", \"method\": \"capture_learning\", \"params\": {\"solution_applied\": \"Some solution\"}}"
```

**Expected Result**:
- Returns error response indicating missing "problem_description"
- Does not create any files or database entries

#### Step 4.2: Invalid Method Name

```bash
curl -X POST http://localhost:8051/mcp ^
  -H "Content-Type: application/json" ^
  -d "{\"jsonrpc\": \"2.0\", \"id\": \"test-6\", \"method\": \"invalid_method\", \"params\": {}}"
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "id": "test-6",
  "error": {
    "code": -32601,
    "message": "Method not found: invalid_method"
  }
}
```

---

## Verification Checklist

After completing all scenarios, verify:

### ✅ File System
- [ ] Markdown files created in `knowledge/metacognition/` directory
- [ ] Files contain properly formatted learning entries
- [ ] Each file has unique timestamp-based name

### ✅ Database Storage
- [ ] Entries appear in Archon UI Knowledge page
- [ ] Source type shows as "learning_capture" or "session_capture"
- [ ] Metadata includes project context and session ID

### ✅ Search Functionality
- [ ] Can search by problem description keywords
- [ ] Can filter by project name
- [ ] Results include relevant entries with scores

### ✅ MCP Server
- [ ] Server responds to health checks
- [ ] All three tools are accessible via JSON-RPC
- [ ] Proper error handling for invalid requests

### ✅ Integration
- [ ] Learning entries are searchable through Archon's main RAG system
- [ ] Entries appear alongside other knowledge sources
- [ ] No conflicts with existing Archon functionality

---

## Troubleshooting

### Issue: "Connection refused" error

**Solution**:
1. Verify MCP server is running on port 8051
2. Check Windows Firewall settings
3. Ensure no other service is using port 8051

### Issue: "Method not found" error

**Solution**:
1. Check MCP server logs for module registration
2. Verify Learning Capture module loaded successfully
3. Restart MCP server if needed

### Issue: Files created but not in database

**Solution**:
1. Check Supabase connection in `.env`
2. Verify service client is available in MCP context
3. Check MCP server logs for storage errors

### Issue: Search returns no results

**Solution**:
1. Verify entries were stored successfully
2. Try broader search terms
3. Check if filtering is too restrictive

---

## Success Criteria

The Learning Capture system is working correctly when:

1. **Capture Works**: Can send debugging experiences via HTTP/JSON-RPC
2. **Storage Works**: Creates both markdown files and database entries
3. **Search Works**: Can retrieve stored learning via search
4. **Integration Works**: Learning appears in Archon UI alongside other knowledge
5. **Error Handling Works**: Invalid inputs are handled gracefully

---

## Next Steps

After successful UAT:

1. **Create Integration**: Add `/learn` command to your Claude Code setup
2. **Automate Capture**: Set up automatic capture for debugging sessions
3. **Team Sharing**: Share Archon endpoint with team members
4. **Monitor Usage**: Track which types of problems are most common
5. **Refine Search**: Adjust search parameters based on usage patterns

---

## Test Data Cleanup (Optional)

To remove test data after UAT:

1. Delete test markdown files from `knowledge/metacognition/`
2. Remove test entries from Supabase via Archon UI
3. Clear any test session data

---

## Sign-off

- [ ] All test scenarios completed successfully
- [ ] Verification checklist fully checked
- [ ] No blocking issues identified
- [ ] System ready for production use

**Tester**: _______________________
**Date**: _______________________
**Status**: ⬜ PASS / ⬜ FAIL