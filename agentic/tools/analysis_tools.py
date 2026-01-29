"""Code analysis tools for agents."""

import ast
import re
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel


class AnalysisResult(BaseModel):
    """Result of code analysis."""
    success: bool
    message: str
    data: Any = None


@tool
def analyze_code(file_path: str) -> AnalysisResult:
    """
    Analyze a Python file for structure and metrics.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        AnalysisResult with code structure information
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return AnalysisResult(
                success=False,
                message=f"File not found: {file_path}",
            )
        
        content = path.read_text()
        tree = ast.parse(content)
        
        # Extract information
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "line": node.lineno,
                })
            elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                # Top-level functions only
                if hasattr(node, 'col_offset') and node.col_offset == 0:
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "line": node.lineno,
                    })
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        # Calculate metrics
        lines = len(content.split("\n"))
        
        return AnalysisResult(
            success=True,
            message=f"Analyzed {file_path}",
            data={
                "file_path": file_path,
                "lines": lines,
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "class_count": len(classes),
                "function_count": len(functions),
            },
        )
        
    except SyntaxError as e:
        return AnalysisResult(
            success=False,
            message=f"Syntax error in {file_path}: {str(e)}",
        )
    except Exception as e:
        return AnalysisResult(
            success=False,
            message=f"Failed to analyze {file_path}: {str(e)}",
        )


@tool
def search_codebase(
    directory: str,
    pattern: str,
    file_pattern: str = "*.py",
) -> AnalysisResult:
    """
    Search for a pattern in the codebase.
    
    Args:
        directory: Directory to search in
        pattern: Regex pattern to search for
        file_pattern: Glob pattern for files to search (default: *.py)
        
    Returns:
        AnalysisResult with matching locations
    """
    try:
        path = Path(directory)
        if not path.exists():
            return AnalysisResult(
                success=False,
                message=f"Directory not found: {directory}",
            )
        
        matches = []
        regex = re.compile(pattern)
        
        for file_path in path.rglob(file_pattern):
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        matches.append({
                            "file": str(file_path.relative_to(path)),
                            "line": i,
                            "content": line.strip()[:100],
                        })
            except Exception:
                continue  # Skip files that can't be read
        
        return AnalysisResult(
            success=True,
            message=f"Found {len(matches)} matches for '{pattern}'",
            data={"pattern": pattern, "matches": matches},
        )
        
    except re.error as e:
        return AnalysisResult(
            success=False,
            message=f"Invalid regex pattern: {str(e)}",
        )
    except Exception as e:
        return AnalysisResult(
            success=False,
            message=f"Search failed: {str(e)}",
        )


@tool
def find_dependencies(file_path: str) -> AnalysisResult:
    """
    Find all imports/dependencies in a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        AnalysisResult with dependency information
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return AnalysisResult(
                success=False,
                message=f"File not found: {file_path}",
            )
        
        content = path.read_text()
        tree = ast.parse(content)
        
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'datetime', 'pathlib', 'typing',
            'collections', 'itertools', 'functools', 'operator', 'copy',
            'math', 'random', 'hashlib', 'uuid', 'base64', 'io', 'struct',
            'logging', 'warnings', 'traceback', 'inspect', 'abc',
            'contextlib', 'dataclasses', 'enum', 'types',
            'asyncio', 'concurrent', 'multiprocessing', 'threading',
            'subprocess', 'socket', 'http', 'urllib', 'email',
            'unittest', 'doctest', 'pdb', 'timeit', 'profile',
        }
        
        standard = []
        third_party = []
        local = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in stdlib_modules:
                        standard.append(alias.name)
                    else:
                        third_party.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if node.level > 0:  # Relative import
                        local.append(node.module)
                    elif module in stdlib_modules:
                        standard.append(node.module)
                    else:
                        third_party.append(node.module)
        
        return AnalysisResult(
            success=True,
            message=f"Found dependencies in {file_path}",
            data={
                "standard_library": list(set(standard)),
                "third_party": list(set(third_party)),
                "local": list(set(local)),
            },
        )
        
    except Exception as e:
        return AnalysisResult(
            success=False,
            message=f"Failed to find dependencies: {str(e)}",
        )


@tool
def check_code_style(file_path: str) -> AnalysisResult:
    """
    Check basic code style issues in a Python file.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        AnalysisResult with style issues
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return AnalysisResult(
                success=False,
                message=f"File not found: {file_path}",
            )
        
        content = path.read_text()
        lines = content.split("\n")
        
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 100:
                issues.append({
                    "line": i,
                    "type": "line-too-long",
                    "message": f"Line exceeds 100 characters ({len(line)})",
                })
            
            # Check trailing whitespace
            if line.rstrip() != line:
                issues.append({
                    "line": i,
                    "type": "trailing-whitespace",
                    "message": "Trailing whitespace",
                })
            
            # Check tabs
            if "\t" in line:
                issues.append({
                    "line": i,
                    "type": "tab-character",
                    "message": "Tab character found (use spaces)",
                })
        
        # Check for missing newline at end
        if content and not content.endswith("\n"):
            issues.append({
                "line": len(lines),
                "type": "no-newline-at-end",
                "message": "File should end with a newline",
            })
        
        return AnalysisResult(
            success=True,
            message=f"Found {len(issues)} style issues in {file_path}",
            data={"issues": issues},
        )
        
    except Exception as e:
        return AnalysisResult(
            success=False,
            message=f"Style check failed: {str(e)}",
        )
