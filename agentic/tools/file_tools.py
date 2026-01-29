"""File system tools for agents."""

from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FileOperationResult(BaseModel):
    """Result of a file operation."""
    success: bool
    message: str
    data: Any = None


@tool
def create_file(file_path: str, content: str) -> FileOperationResult:
    """
    Create a new file with the given content.
    
    Args:
        file_path: Path where the file should be created
        content: Content to write to the file
        
    Returns:
        FileOperationResult with success status
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return FileOperationResult(
            success=True,
            message=f"File created: {file_path}",
            data={"path": file_path, "size": len(content)},
        )
    except Exception as e:
        return FileOperationResult(
            success=False,
            message=f"Failed to create file: {str(e)}",
        )


@tool
def read_file(file_path: str) -> FileOperationResult:
    """
    Read the contents of a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        FileOperationResult with file contents
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return FileOperationResult(
                success=False,
                message=f"File not found: {file_path}",
            )
        
        content = path.read_text()
        return FileOperationResult(
            success=True,
            message=f"File read: {file_path}",
            data={"path": file_path, "content": content, "size": len(content)},
        )
    except Exception as e:
        return FileOperationResult(
            success=False,
            message=f"Failed to read file: {str(e)}",
        )


@tool
def list_directory(dir_path: str, pattern: str = "*") -> FileOperationResult:
    """
    List files in a directory.
    
    Args:
        dir_path: Path to the directory
        pattern: Glob pattern to filter files (default: "*")
        
    Returns:
        FileOperationResult with list of files
    """
    try:
        path = Path(dir_path)
        if not path.exists():
            return FileOperationResult(
                success=False,
                message=f"Directory not found: {dir_path}",
            )
        
        files = [str(f.relative_to(path)) for f in path.glob(pattern)]
        return FileOperationResult(
            success=True,
            message=f"Listed {len(files)} files in {dir_path}",
            data={"path": dir_path, "files": files},
        )
    except Exception as e:
        return FileOperationResult(
            success=False,
            message=f"Failed to list directory: {str(e)}",
        )


@tool
def delete_file(file_path: str) -> FileOperationResult:
    """
    Delete a file.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        FileOperationResult with success status
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return FileOperationResult(
                success=False,
                message=f"File not found: {file_path}",
            )
        
        path.unlink()
        return FileOperationResult(
            success=True,
            message=f"File deleted: {file_path}",
        )
    except Exception as e:
        return FileOperationResult(
            success=False,
            message=f"Failed to delete file: {str(e)}",
        )


@tool
def append_to_file(file_path: str, content: str) -> FileOperationResult:
    """
    Append content to an existing file.
    
    Args:
        file_path: Path to the file
        content: Content to append
        
    Returns:
        FileOperationResult with success status
    """
    try:
        path = Path(file_path)
        with path.open("a") as f:
            f.write(content)
        return FileOperationResult(
            success=True,
            message=f"Content appended to: {file_path}",
        )
    except Exception as e:
        return FileOperationResult(
            success=False,
            message=f"Failed to append to file: {str(e)}",
        )
