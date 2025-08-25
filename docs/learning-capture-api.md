# Learning Capture API for Archon

## Overview

Archon provides a Learning Capture API via MCP that allows external projects (like Claude Code, Cursor, or other AI assistants) to send debugging experiences for structured storage and retrieval. This creates a centralized knowledge base of debugging solutions searchable across all connected projects.

## How It Works

1. **External Project** encounters a debugging scenario
2. **Send to Archon** via MCP HTTP endpoint with raw debugging information
3. **Archon Structures** the data into learning entries with comprehensive format
4. **Stores in Supabase** for RAG-powered retrieval
5. **Search Later** to find solutions to similar problems

## MCP Endpoint

Archon's MCP server exposes these tools at:
- **HTTP Endpoint**: `http://localhost:8051/mcp`
- **Transport**: JSON-RPC 2.0

## Available Tools

### 1. `capture_learning` - Store Individual Debugging Experience

Send a specific debugging experience to Archon for storage.

**HTTP Request:**
```bash
curl -X POST http://localhost:8051/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "capture_learning",
    "params": {
      "problem_description": "ModuleNotFoundError: No module named utils despite file existing",
      "investigation_steps": [
        "Checked if utils.py exists in directory",
        "Verified Python path configuration",
        "Tested import from different directories",
        "Discovered working directory issue"
      ],
      "solution_applied": "Run script from project root directory instead of subdirectory",
      "outcome": "Import worked correctly when run from project root",
      "project_context": "my-python-project",
      "additional_context": {
        "language": "python",
        "error_type": "import_error",
        "framework": "fastapi"
      }
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "success": true,
    "session_id": "external-my-python-project-20250113-143052",
    "entries_created": 1,
    "markdown_file": "/knowledge/metacognition/learning-20250113-143052.md",
    "archon_storage": [
      {
        "entry_id": "L001",
        "document_id": "uuid-1234",
        "status": "stored"
      }
    ],
    "message": "Successfully captured learning from my-python-project"
  }
}
```

### 2. `capture_session_learning` - Process Full Session

Send an entire debugging session or conversation for automatic experience extraction.

**HTTP Request:**
```bash
curl -X POST http://localhost:8051/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "capture_session_learning",
    "params": {
      "session_content": "User: I am getting TypeError: Cannot read property of undefined\nAssistant: This error typically occurs when...\n[full conversation transcript]",
      "project_name": "react-app",
      "session_type": "debugging",
      "tags": ["javascript", "react", "type-error"]
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "success": true,
    "session_id": "session-react-app-20250113-144523",
    "experiences_found": 3,
    "entries_created": 3,
    "markdown_file": "/knowledge/metacognition/learning-20250113-144523.md",
    "archon_storage": [
      {
        "entry_id": "L001",
        "document_id": "uuid-5678",
        "status": "stored"
      }
    ]
  }
}
```

### 3. `search_learning` - Search Debugging Knowledge

Search the centralized debugging knowledge base.

**HTTP Request:**
```bash
curl -X POST http://localhost:8051/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "3",
    "method": "search_learning",
    "params": {
      "query": "TypeError undefined property React",
      "project_filter": null,
      "max_results": 5
    }
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "result": {
    "success": true,
    "query": "TypeError undefined property React",
    "results_count": 3,
    "results": [
      {
        "content": "Problem: TypeError: Cannot read property of undefined...",
        "title": "React State Access Error",
        "metadata": {
          "project_name": "react-app",
          "session_id": "session-react-app-20250113-144523"
        },
        "score": 0.92
      }
    ]
  }
}
```

## Integration Examples

### From Claude Code

Create a slash command that calls Archon:

```javascript
// In Claude Code extension or MCP client
async function captureDebuggingExperience(problem, steps, solution) {
  const response = await fetch('http://localhost:8051/mcp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now().toString(),
      method: 'capture_learning',
      params: {
        problem_description: problem,
        investigation_steps: steps,
        solution_applied: solution,
        outcome: 'Issue resolved',
        project_context: getCurrentProject()
      }
    })
  });
  
  return response.json();
}
```

### From Python Project

```python
import requests
import json

def send_to_archon(problem, steps, solution, project_name):
    """Send debugging experience to Archon for storage."""
    
    response = requests.post(
        'http://localhost:8051/mcp',
        json={
            'jsonrpc': '2.0',
            'id': '1',
            'method': 'capture_learning',
            'params': {
                'problem_description': problem,
                'investigation_steps': steps,
                'solution_applied': solution,
                'outcome': 'Successfully resolved',
                'project_context': project_name
            }
        }
    )
    
    return response.json()

# Example usage
send_to_archon(
    problem="ImportError: circular import detected",
    steps=[
        "Identified circular dependency between modules",
        "Mapped import chain",
        "Refactored to break circular dependency"
    ],
    solution="Moved shared code to separate module",
    project_name="my-app"
)
```

### From Node.js/TypeScript

```typescript
import axios from 'axios';

interface LearningCapture {
  problem_description: string;
  investigation_steps: string[];
  solution_applied: string;
  outcome: string;
  project_context: string;
}

async function captureToArchon(data: LearningCapture) {
  const response = await axios.post('http://localhost:8051/mcp', {
    jsonrpc: '2.0',
    id: Date.now().toString(),
    method: 'capture_learning',
    params: data
  });
  
  return response.data;
}
```

## Structured Learning Format

Each debugging experience is automatically structured into:

### 1. **Situation**
- Goal: What was being attempted
- Action Taken: What was done
- Expected Result: What should have happened
- Actual Result: What actually happened

### 2. **Debug Journey**
- Initial Hypothesis: First assumption
- Investigation Path: Steps taken
- Dead Ends: What didn't work

### 3. **Resolution**
- Root Cause: Actual issue
- Solution: Fix applied
- Verification: How it was confirmed

### 4. **Knowledge Synthesis**
- Domain Principle: Technology-specific learning
- Universal Principle: Transferable approach
- Pattern Recognition: Reusable indicators
- Mental Model: Conceptual understanding

## Storage & Retrieval

### Storage Locations
1. **Markdown Files**: `knowledge/metacognition/learning-*.md`
2. **Supabase Database**: Full-text searchable documents

### Metadata Tags
- `source_type`: "learning_capture" or "session_capture"
- `project_context`: Source project name
- `timestamp`: When captured
- `session_id`: Unique identifier
- Custom tags from `additional_context`

## Best Practices

### 1. Be Descriptive
Provide detailed problem descriptions and investigation steps for better future searchability.

### 2. Include Context
Always include project name and relevant context (language, framework, etc.)

### 3. Document Dead Ends
Include what didn't work - this is valuable learning too.

### 4. Tag Appropriately
Use tags to categorize by technology, error type, or domain.

### 5. Regular Capture
Capture debugging experiences as they happen rather than trying to reconstruct later.

## Example Workflow

1. **During Debugging**: Encounter an issue in your project
2. **Document Steps**: Keep track of what you try
3. **Find Solution**: Resolve the issue
4. **Send to Archon**: Call `capture_learning` with the experience
5. **Future Benefit**: Next time similar issue occurs, search finds the solution

## Troubleshooting

### Connection Refused
- Verify Archon MCP server is running on port 8051
- Check firewall settings

### Tool Not Found
- Ensure Learning Capture module is registered
- Check MCP server logs for registration errors

### Storage Failed
- Verify Supabase credentials are configured
- Check service client availability

## Benefits

1. **Centralized Knowledge**: All debugging experiences in one place
2. **Cross-Project Learning**: Learn from issues in other projects
3. **Team Knowledge Sharing**: Share debugging solutions across team
4. **Pattern Recognition**: Identify recurring issues
5. **Faster Resolution**: Find solutions to similar problems quickly