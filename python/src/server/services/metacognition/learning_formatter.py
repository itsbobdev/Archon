"""
Learning Formatter Module for Meta-Cognition Layer

Transforms raw session data into structured learning entries following the exact format
specified in the Meta-Cognition PRD. Enhanced with synopsis generation for multi-field embeddings.
"""

from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import re
import json


def create_learning_entries(session_data: Dict[str, Any], 
                           use_v2_format: bool = True) -> List[Dict[str, Any]]:
    """
    Transform raw session data into structured learning entries.
    
    Args:
        session_data: Dictionary from session_analyzer with debugging experiences
        use_v2_format: Whether to use v2 format with synopsis (default True)
        
    Returns:
        List of structured learning entries following PRD format
    """
    learning_entries = []
    debugging_experiences = session_data.get("debugging_experiences", [])
    
    # Initialize synopsis generator for v2 format
    synopsis_generator = SynopsisGenerator() if use_v2_format else None
    
    for i, experience in enumerate(debugging_experiences, 1):
        learning_entry = _create_single_learning_entry(
            experience, 
            entry_id=f"L{i:03d}",
            timestamp=session_data.get("timestamp", datetime.now().isoformat()),
            session_data=session_data,
            synopsis_generator=synopsis_generator
        )
        learning_entries.append(learning_entry)
    
    return learning_entries


def _create_single_learning_entry(experience: Dict[str, Any], 
                                 entry_id: str, 
                                 timestamp: str,
                                 session_data: Optional[Dict[str, Any]] = None,
                                 synopsis_generator: Optional['SynopsisGenerator'] = None) -> Dict[str, Any]:
    """
    Create a single structured learning entry from a debugging experience.
    
    Args:
        experience: Raw debugging experience dictionary
        entry_id: Unique learning entry ID (L001, L002, etc.)
        timestamp: ISO timestamp string
        session_data: Complete session data (for v2 format)
        synopsis_generator: SynopsisGenerator instance (for v2 format)
        
    Returns:
        Structured learning entry dictionary following PRD format
    """
    # Extract and analyze the debugging experience components
    problem_desc = experience.get("problem_description", "")
    investigation_steps = experience.get("investigation_steps", [])
    solution = experience.get("solution_applied", "")
    outcome = experience.get("outcome", "")
    
    # Determine trigger type based on problem description
    trigger = _determine_trigger_type(problem_desc)
    
    # Create situation section
    situation = _extract_situation_details(problem_desc, investigation_steps, outcome)
    
    # Create debug journey section
    debug_journey = _extract_debug_journey(investigation_steps, solution)
    
    # Create resolution section
    resolution = _extract_resolution(solution, outcome, problem_desc)
    
    # Create knowledge synthesis section
    knowledge_synthesis = _extract_knowledge_synthesis(problem_desc, solution, investigation_steps)
    
    # Base entry structure
    entry = {
        "id": entry_id,
        "timestamp": timestamp,
        "trigger": trigger,
        "situation": situation,
        "debug_journey": debug_journey,
        "resolution": resolution,
        "knowledge_synthesis": knowledge_synthesis
    }
    
    # Add v2 enhancements if synopsis generator is provided
    if synopsis_generator:
        entry["version"] = 2
        
        # Generate synopsis from session data
        if session_data:
            synopsis = synopsis_generator.create_synopsis_from_session_data(session_data)
        else:
            # Fallback: generate synopsis from current entry
            synopsis = synopsis_generator.generate_synopsis(entry)
        
        entry["synopsis"] = synopsis
        entry["title"] = synopsis["title"]
        
        # Add embedding field content for future use
        if session_data:
            entry["embedding_fields"] = synopsis_generator.extract_embedding_field_content(session_data)
    else:
        entry["version"] = 1
    
    return entry


def _determine_trigger_type(problem_description: str) -> str:
    """
    Determine the trigger type based on problem description.
    
    Args:
        problem_description: Description of the problem encountered
        
    Returns:
        Trigger type string ("error", "performance", "investigation", etc.)
    """
    problem_lower = problem_description.lower()
    
    if any(word in problem_lower for word in ["error", "exception", "failed", "crash", "bug"]):
        return "error"
    elif any(word in problem_lower for word in ["slow", "performance", "timeout", "lag"]):
        return "performance"
    elif any(word in problem_lower for word in ["unexpected", "weird", "strange", "odd"]):
        return "investigation"
    elif any(word in problem_lower for word in ["optimization", "improvement", "enhancement"]):
        return "optimization"
    else:
        return "investigation"


def _extract_situation_details(problem_desc: str, steps: List[str], outcome: str) -> Dict[str, str]:
    """
    Extract situation details from debugging experience.
    
    Args:
        problem_desc: Problem description
        steps: Investigation steps taken
        outcome: Final outcome
        
    Returns:
        Situation dictionary with goal, action_taken, expected_result, actual_result
    """
    # Infer goal from problem description and steps
    goal = _infer_goal_from_problem(problem_desc)
    
    # Extract action taken from first few investigation steps
    action_taken = _extract_action_taken(steps)
    
    # Infer expected vs actual results
    expected_result, actual_result = _infer_expected_vs_actual(problem_desc, outcome)
    
    return {
        "goal": goal,
        "action_taken": action_taken,
        "expected_result": expected_result,
        "actual_result": actual_result
    }


def _extract_debug_journey(steps: List[str], solution: str) -> Dict[str, Any]:
    """
    Extract debug journey details from investigation steps.
    
    Args:
        steps: List of investigation steps
        solution: Solution that was applied
        
    Returns:
        Debug journey dictionary with initial_hypothesis, investigation_path, dead_ends
    """
    # Extract initial hypothesis from first step or problem analysis
    initial_hypothesis = _extract_initial_hypothesis(steps)
    
    # Clean up investigation path
    investigation_path = _clean_investigation_steps(steps)
    
    # Identify dead ends
    dead_ends = _identify_dead_ends(steps, solution)
    
    return {
        "initial_hypothesis": initial_hypothesis,
        "investigation_path": investigation_path,
        "dead_ends": dead_ends
    }


def _extract_resolution(solution: str, outcome: str, problem_desc: str) -> Dict[str, str]:
    """
    Extract resolution details from solution and outcome.
    
    Args:
        solution: Solution that was applied
        outcome: Result of applying the solution
        problem_desc: Original problem description
        
    Returns:
        Resolution dictionary with root_cause, solution, verification
    """
    # Infer root cause from problem and solution
    root_cause = _infer_root_cause(problem_desc, solution)
    
    # Use provided solution
    solution_text = solution if solution else "Applied systematic debugging approach"
    
    # Extract verification method from outcome
    verification = _extract_verification_method(outcome)
    
    return {
        "root_cause": root_cause,
        "solution": solution_text,
        "verification": verification
    }


def _extract_knowledge_synthesis(problem_desc: str, solution: str, steps: List[str]) -> Dict[str, str]:
    """
    Extract knowledge synthesis from the debugging experience.
    
    Args:
        problem_desc: Problem description
        solution: Solution applied
        steps: Investigation steps
        
    Returns:
        Knowledge synthesis dictionary with domain/universal principles, patterns, mental models
    """
    # Determine domain-specific vs universal principles
    domain_principle = _extract_domain_principle(problem_desc, solution)
    universal_principle = _extract_universal_principle(steps, solution)
    
    # Extract pattern recognition insights
    pattern_recognition = _extract_pattern_recognition(problem_desc, solution)
    
    # Extract mental model insights
    mental_model = _extract_mental_model(problem_desc, solution, steps)
    
    return {
        "domain_principle": domain_principle,
        "universal_principle": universal_principle,
        "pattern_recognition": pattern_recognition,
        "mental_model": mental_model
    }


class SynopsisGenerator:
    """
    Generates structured synopsis for knowledge entries following PRD format.
    
    Produces 120-200 word synopsis with bullet format:
    - symptoms: What went wrong
    - context: Environment/situation  
    - root_cause: Why it happened
    - fix: What solved it
    - applies_when: When to use this knowledge
    """
    
    def __init__(self):
        # Controlled vocabulary for tag mapping (simplified)
        self.vocabulary = {"coding": {"problems": [], "contexts": []}}
    
    def generate_synopsis(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate structured synopsis from learning entry.
        
        Args:
            entry: Learning entry dictionary
            
        Returns:
            Synopsis dictionary with title and bullets
        """
        # Generate title (max 120 chars)
        title = self._generate_title(entry)
        
        # Generate structured bullets
        bullets = self._generate_bullets(entry)
        
        # Ensure word count is within range (120-200 words)
        bullets = self._adjust_word_count(bullets)
        
        return {
            "title": title,
            "bullets": bullets
        }
    
    def create_synopsis_from_session_data(self, session_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate structured synopsis directly from session data.
        
        Args:
            session_data: Raw session data from session analyzer
            
        Returns:
            Synopsis dictionary for multi-field embeddings
        """
        # Extract key information from session data
        debugging_experiences = session_data.get("debugging_experiences", [])
        if not debugging_experiences:
            return self._create_default_synopsis()
        
        # Use first experience for now (can be enhanced later for multiple)
        experience = debugging_experiences[0]
        
        # Generate title from problem description
        problem_desc = experience.get("problem_description", "")
        title = self._generate_title_from_problem(problem_desc)
        
        # Create bullets from experience data
        bullets = {
            "symptoms": self._extract_symptoms(experience),
            "context": self._extract_context(experience, session_data),
            "root_cause": self._extract_root_cause_from_experience(experience),
            "fix": self._extract_fix(experience),
            "applies_when": self._extract_applicability(experience)
        }
        
        # Ensure proper word count
        bullets = self._adjust_word_count(bullets)
        
        return {
            "title": title,
            "bullets": bullets
        }
    
    def extract_embedding_field_content(self, session_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract content optimized for each of the 6 embedding fields.
        
        Args:
            session_data: Enhanced session data
            
        Returns:
            Dictionary with content for each embedding field
        """
        debugging_experiences = session_data.get("debugging_experiences", [])
        if not debugging_experiences:
            return self._create_default_embedding_content()
        
        experience = debugging_experiences[0]
        synopsis = self.create_synopsis_from_session_data(session_data)
        
        return {
            "title": synopsis["title"],
            "synopsis": self._format_synopsis_for_embedding(synopsis),
            "debug_journey": self._format_debug_journey_for_embedding(experience),
            "root_cause": experience.get("solution_applied", "Root cause analysis needed"),
            "solution": experience.get("solution_applied", "Solution implementation needed"),
            "pattern_recognition": self._extract_pattern_for_embedding(experience)
        }
    
    def _generate_title(self, entry: Dict[str, Any]) -> str:
        """Generate title from learning entry (max 120 chars)."""
        # Extract key elements
        goal = entry.get("situation", {}).get("goal", "")
        actual_result = entry.get("situation", {}).get("actual_result", "")
        
        # Create descriptive title
        if "error" in actual_result.lower() or "failed" in actual_result.lower():
            # Error-based title
            domain = self._infer_domain_from_entry(entry)
            title = f"{domain.title()} Error: {actual_result[:60]}"
        else:
            # Goal-based title
            title = f"Resolve: {goal[:70]}"
        
        # Ensure max length
        if len(title) > 120:
            title = title[:117] + "..."
        
        return title
    
    def _generate_title_from_problem(self, problem_desc: str) -> str:
        """Generate title from problem description."""
        if not problem_desc:
            return "Debugging Session Learning"
        
        # Clean and truncate
        clean_desc = re.sub(r'[^\w\s-]', '', problem_desc)
        if len(clean_desc) <= 120:
            return clean_desc
        
        # Truncate intelligently at word boundary
        words = clean_desc.split()
        title = ""
        for word in words:
            if len(title + " " + word) <= 117:
                title += " " + word if title else word
            else:
                break
        
        return title + "..." if len(clean_desc) > 120 else title
    
    def _generate_bullets(self, entry: Dict[str, Any]) -> Dict[str, str]:
        """Generate bullet points from learning entry."""
        situation = entry.get("situation", {})
        debug_journey = entry.get("debug_journey", {})
        resolution = entry.get("resolution", {})
        knowledge_synthesis = entry.get("knowledge_synthesis", {})
        
        return {
            "symptoms": situation.get("actual_result", "Issue encountered"),
            "context": self._format_context_bullet(situation, debug_journey),
            "root_cause": resolution.get("root_cause", "Root cause analysis needed"),
            "fix": resolution.get("solution", "Solution implementation needed"),
            "applies_when": self._format_applicability_bullet(knowledge_synthesis)
        }
    
    def _format_context_bullet(self, situation: Dict[str, Any], debug_journey: Dict[str, Any]) -> str:
        """Format context bullet from situation and debug journey."""
        context_parts = []
        
        if situation.get("action_taken"):
            context_parts.append(f"While {situation['action_taken'].lower()}")
        
        # Add environment context if inferrable
        goal = situation.get("goal", "").lower()
        if "python" in goal or "import" in goal:
            context_parts.append("in Python development environment")
        elif "javascript" in goal or "node" in goal:
            context_parts.append("in JavaScript/Node.js environment")
        elif "database" in goal or "sql" in goal:
            context_parts.append("in database environment")
        else:
            context_parts.append("in development environment")
        
        return " ".join(context_parts) if context_parts else "Development environment context"
    
    def _format_applicability_bullet(self, knowledge_synthesis: Dict[str, Any]) -> str:
        """Format applicability bullet from knowledge synthesis."""
        pattern = knowledge_synthesis.get("pattern_recognition", "")
        if pattern and "when" in pattern.lower():
            return pattern
        
        # Generate generic applicability
        domain_principle = knowledge_synthesis.get("domain_principle", "")
        if domain_principle:
            return f"When encountering similar {domain_principle.lower()}"
        
        return "When facing similar debugging challenges"
    
    def _adjust_word_count(self, bullets: Dict[str, str]) -> Dict[str, str]:
        """Ensure synopsis is within 120-200 word range."""
        # Count current words (rough estimate)
        total_text = " ".join(bullets.values())
        word_count = len(total_text.split())
        
        if word_count < 120:
            # Expand bullets to reach minimum
            return self._expand_bullets(bullets, 120 - word_count)
        elif word_count > 200:
            # Compress bullets to meet maximum
            return self._compress_bullets(bullets, word_count - 200)
        
        return bullets
    
    def _expand_bullets(self, bullets: Dict[str, str], words_needed: int) -> Dict[str, str]:
        """Expand bullets to meet minimum word count."""
        expanded = bullets.copy()
        
        # Add detail to each bullet proportionally
        keys = list(expanded.keys())
        words_per_bullet = words_needed // len(keys) if keys else 0
        
        for key in keys:
            if words_per_bullet > 0:
                if key == "symptoms":
                    expanded[key] += " with detailed error context"
                elif key == "context":
                    expanded[key] += " during development workflow"
                elif key == "root_cause":
                    expanded[key] += " through systematic analysis"
                elif key == "fix":
                    expanded[key] += " with verification steps"
                elif key == "applies_when":
                    expanded[key] += " in similar scenarios"
        
        return expanded
    
    def _compress_bullets(self, bullets: Dict[str, str], words_to_remove: int) -> Dict[str, str]:
        """Compress bullets to meet maximum word count."""
        compressed = bullets.copy()
        
        # Remove words from longest bullets first
        while words_to_remove > 0:
            longest_key = max(compressed.keys(), key=lambda k: len(compressed[k].split()))
            words = compressed[longest_key].split()
            
            if len(words) > 5:  # Don't make bullets too short
                compressed[longest_key] = " ".join(words[:-1])
                words_to_remove -= 1
            else:
                break
        
        return compressed
    
    def _extract_symptoms(self, experience: Dict[str, Any]) -> str:
        """Extract symptoms from debugging experience."""
        problem_desc = experience.get("problem_description", "")
        if "error" in problem_desc.lower():
            return f"Encountered {problem_desc.lower()}"
        return problem_desc or "Issue encountered during operation"
    
    def _extract_context(self, experience: Dict[str, Any], session_data: Dict[str, Any]) -> str:
        """Extract context from experience and session data."""
        # Use project context if available
        project_context = session_data.get("project_context", "")
        if project_context:
            return f"Working in {project_context} environment"
        
        # Infer from problem description
        problem_desc = experience.get("problem_description", "").lower()
        if "python" in problem_desc or "import" in problem_desc:
            return "Python development environment"
        elif "javascript" in problem_desc or "node" in problem_desc:
            return "JavaScript/Node.js environment"
        
        return "Development environment"
    
    def _extract_root_cause_from_experience(self, experience: Dict[str, Any]) -> str:
        """Extract root cause from debugging experience."""
        # Look for solution clues to infer root cause
        solution = experience.get("solution_applied", "")
        if "directory" in solution.lower():
            return "Working directory or path configuration issue"
        elif "install" in solution.lower():
            return "Missing or incorrect dependency installation"
        elif "permission" in solution.lower():
            return "File or directory permission restriction"
        
        return "Root cause identified through systematic debugging"
    
    def _extract_fix(self, experience: Dict[str, Any]) -> str:
        """Extract fix from debugging experience."""
        solution = experience.get("solution_applied", "")
        if solution:
            # Ensure it starts with action verb
            action_verbs = ["use", "run", "install", "set", "configure", "change", "add", "remove"]
            if not any(solution.lower().startswith(verb) for verb in action_verbs):
                return f"Apply {solution.lower()}"
            return solution
        
        return "Apply systematic debugging approach"
    
    def _extract_applicability(self, experience: Dict[str, Any]) -> str:
        """Extract applicability pattern from experience."""
        problem_desc = experience.get("problem_description", "").lower()
        
        if "not found" in problem_desc:
            return "When files exist but are not found by the system"
        elif "error" in problem_desc and "import" in problem_desc:
            return "When import statements fail despite proper installation"
        elif "permission" in problem_desc:
            return "When encountering file or directory access restrictions"
        
        return "When facing similar configuration or environment issues"
    
    def _format_synopsis_for_embedding(self, synopsis: Dict[str, Any]) -> str:
        """Format synopsis for embedding generation."""
        bullets = synopsis.get("bullets", {})
        return f"Problem: {bullets.get('symptoms', '')} Context: {bullets.get('context', '')} Cause: {bullets.get('root_cause', '')} Solution: {bullets.get('fix', '')} Use: {bullets.get('applies_when', '')}"
    
    def _format_debug_journey_for_embedding(self, experience: Dict[str, Any]) -> str:
        """Format debug journey for embedding generation."""
        steps = experience.get("investigation_steps", [])
        if isinstance(steps, list):
            return " → ".join(steps)
        return str(steps) if steps else "Systematic investigation approach"
    
    def _extract_pattern_for_embedding(self, experience: Dict[str, Any]) -> str:
        """Extract pattern recognition for embedding generation."""
        problem_desc = experience.get("problem_description", "")
        solution = experience.get("solution_applied", "")
        
        # Create pattern statement
        if "file" in problem_desc.lower() and "directory" in solution.lower():
            return "File accessibility issues often relate to working directory context"
        elif "import" in problem_desc.lower():
            return "Import errors typically indicate path or environment configuration problems"
        
        return "Debugging requires systematic hypothesis testing and validation"
    
    def _infer_domain_from_entry(self, entry: Dict[str, Any]) -> str:
        """Infer domain from entry content."""
        content_text = str(entry).lower()
        
        if "python" in content_text or "import" in content_text:
            return "Python"
        elif "javascript" in content_text or "node" in content_text:
            return "JavaScript"
        elif "sql" in content_text or "database" in content_text:
            return "Database"
        
        return "System"
    
    def _create_default_synopsis(self) -> Dict[str, Any]:
        """Create default synopsis when no session data available."""
        return {
            "title": "Learning Session Analysis",
            "bullets": {
                "symptoms": "Issue encountered during session",
                "context": "Development environment",
                "root_cause": "Root cause analysis needed",
                "fix": "Solution implementation needed",
                "applies_when": "When facing similar challenges"
            }
        }
    
    def _create_default_embedding_content(self) -> Dict[str, str]:
        """Create default embedding content when no session data available."""
        return {
            "title": "Learning Session Analysis",
            "synopsis": "Problem: Issue encountered Context: Development environment Cause: Analysis needed Solution: Implementation needed Use: Similar challenges",
            "debug_journey": "Systematic investigation approach",
            "root_cause": "Root cause analysis needed",
            "solution": "Solution implementation needed",
            "pattern_recognition": "Debugging requires systematic approach"
        }


# Helper functions for extracting specific details

def _infer_goal_from_problem(problem_desc: str) -> str:
    """Infer the goal from problem description."""
    if "project" in problem_desc.lower():
        return "Set up and configure project environment properly"
    elif "install" in problem_desc.lower() or "dependencies" in problem_desc.lower():
        return "Install and manage project dependencies correctly"
    elif "import" in problem_desc.lower() or "module" in problem_desc.lower():
        return "Import and use modules correctly in the application"
    else:
        return "Resolve the identified issue and restore expected functionality"


def _extract_action_taken(steps: List[str]) -> str:
    """Extract action taken from investigation steps."""
    if steps:
        first_step = steps[0]
        if "check" in first_step.lower():
            return f"Investigated the issue by {first_step.lower()}"
        else:
            return f"Began debugging by {first_step.lower()}"
    return "Initiated systematic debugging process"


def _infer_expected_vs_actual(problem_desc: str, outcome: str) -> Tuple[str, str]:
    """Infer expected vs actual results."""
    if "missing" in problem_desc.lower() or "not found" in problem_desc.lower():
        expected = "Required files/modules should be accessible and functional"
        actual = "Files/modules were not found or not accessible from current context"
    elif "dependencies" in problem_desc.lower():
        expected = "All dependencies should be installed and available"
        actual = "Dependencies were not installed or not available"
    else:
        expected = "System should function as intended without errors"
        actual = problem_desc if problem_desc else "Encountered unexpected behavior"
    
    return expected, actual


def _extract_initial_hypothesis(steps: List[str]) -> str:
    """Extract initial hypothesis from steps."""
    if steps:
        first_step = steps[0]
        if "check" in first_step.lower():
            return f"Initial assumption was related to {first_step.lower()}"
        else:
            return f"First hypothesis: {first_step}"
    return "Initial hypothesis based on error symptoms and common patterns"


def _clean_investigation_steps(steps: List[str]) -> List[str]:
    """Clean up investigation steps for better readability."""
    cleaned_steps = []
    for step in steps:
        # Remove redundant phrases and clean up
        cleaned = re.sub(r'^(step \d+:?|then|next)\s*', '', step, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        if cleaned:
            cleaned_steps.append(cleaned.capitalize())
    
    return cleaned_steps if cleaned_steps else ["Analyzed the problem systematically"]


def _identify_dead_ends(steps: List[str], solution: str) -> List[str]:
    """Identify potential dead ends from investigation steps."""
    dead_ends = []
    
    # Look for steps that didn't lead to the solution
    solution_keywords = solution.lower().split() if solution else []
    
    for step in steps[:-1]:  # Exclude the last step which likely led to solution
        step_lower = step.lower()
        if not any(keyword in step_lower for keyword in solution_keywords):
            if any(word in step_lower for word in ["tried", "attempted", "checked", "tested"]):
                dead_ends.append(f"Investigated {step.lower()} but this wasn't the root cause")
    
    return dead_ends if dead_ends else ["Initial troubleshooting approaches required refinement"]


def _infer_root_cause(problem_desc: str, solution: str) -> str:
    """Infer root cause from problem and solution."""
    if "virtual environment" in solution.lower():
        return "Missing or incorrectly configured virtual environment"
    elif "install" in solution.lower():
        return "Missing dependencies or incorrect installation"
    elif "path" in solution.lower() or "directory" in solution.lower():
        return "Incorrect working directory or path configuration"
    elif "permissions" in solution.lower():
        return "File or directory permission issues"
    else:
        return f"Root cause addressed by: {solution}"


def _extract_verification_method(outcome: str) -> str:
    """Extract verification method from outcome."""
    if "successfully" in outcome.lower():
        return "Confirmed resolution by testing the previously failing scenario"
    elif "resolved" in outcome.lower():
        return "Verified fix by reproducing original conditions"
    else:
        return f"Validation method: {outcome}"


def _extract_domain_principle(problem_desc: str, solution: str) -> str:
    """Extract domain-specific learning principle."""
    combined = f"{problem_desc} {solution}".lower()
    
    if ("python" in combined or "pip" in combined or "venv" in combined or 
        "import" in combined or "module" in combined or ".py" in combined):
        return "Python import system requires proper working directory and module path configuration"
    elif "javascript" in combined or "node" in combined or "npm" in combined:
        return "JavaScript projects require proper dependency installation via npm/yarn"
    elif "git" in combined:
        return "Version control operations require understanding of Git workflow and commands"
    else:
        return "Technology-specific configuration and setup patterns are crucial for success"


def _extract_universal_principle(steps: List[str], solution: str) -> str:
    """Extract universal debugging principle."""
    steps_text = " ".join(steps).lower()
    
    # If the steps involve context or working directory, include "context" in the principle
    if "working directory" in steps_text or "context" in steps_text or "path" in steps_text:
        return "Understanding the execution context is essential when resolving import or path-related issues"
    
    if "systematic" in steps_text or len(steps) > 3:
        return "Systematic investigation yields better debugging outcomes than ad hoc troubleshooting"
    
    if "check" in steps_text:
        return "Verify assumptions before proceeding with complex solutions"
    
    return "Understanding the problem context is essential before applying solutions"


def _extract_pattern_recognition(problem_desc: str, solution: str) -> str:
    """Extract pattern recognition insights."""
    if "not found" in problem_desc.lower():
        return "'Not found' errors often indicate path, environment, or dependency issues"
    elif "missing" in problem_desc.lower():
        return "Missing component errors suggest setup or configuration problems"
    else:
        return "Error patterns provide clues about the category and likely solutions"


def _extract_mental_model(problem_desc: str, solution: str, steps: List[str]) -> str:
    """Extract mental model insights."""
    if "environment" in solution.lower():
        return "Development environments are isolated contexts with their own dependencies"
    elif "path" in solution.lower():
        return "File system navigation and context matter for resource accessibility"
    else:
        return "Debugging is a systematic process of hypothesis testing and validation"