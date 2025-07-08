#!/usr/bin/env python3
"""
File Utilities for Graph Analytics

Helper functions for file operations, format detection, and validation.
"""

import os
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib

from core.logging import get_logger

logger = get_logger(__name__)

def get_supported_file_types() -> Dict[str, List[str]]:
    """Get mapping of supported file categories to extensions."""
    return {
        "text": [".txt", ".md", ".rst", ".log"],
        "documents": [".pdf", ".docx", ".doc", ".odt", ".rtf"],
        "data": [".json", ".csv", ".tsv", ".xml", ".yaml", ".yml"],
        "web": [".html", ".htm", ".xhtml"],
        "code": [".py", ".js", ".java", ".cpp", ".c", ".h", ".php", ".rb", ".go"],
        "spreadsheet": [".xlsx", ".xls", ".ods"]
    }

def is_supported_file(file_path: str) -> bool:
    """Check if a file type is supported for processing."""
    file_extension = Path(file_path).suffix.lower()
    supported_types = get_supported_file_types()
    
    all_extensions = []
    for extensions in supported_types.values():
        all_extensions.extend(extensions)
    
    return file_extension in all_extensions

def get_file_category(file_path: str) -> str:
    """Get the category of a file based on its extension."""
    file_extension = Path(file_path).suffix.lower()
    supported_types = get_supported_file_types()
    
    for category, extensions in supported_types.items():
        if file_extension in extensions:
            return category
    
    return "unknown"

def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file for deduplication."""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return ""

def find_files_by_pattern(directory: str, 
                         patterns: List[str], 
                         recursive: bool = True) -> List[str]:
    """Find files matching given patterns."""
    directory_path = Path(directory)
    found_files = []
    
    for pattern in patterns:
        if recursive:
            matches = directory_path.rglob(pattern)
        else:
            matches = directory_path.glob(pattern)
        
        for match in matches:
            if match.is_file():
                found_files.append(str(match))
    
    return found_files

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get comprehensive information about a file."""
    try:
        file_path_obj = Path(file_path)
        stat = file_path_obj.stat()
        
        return {
            "filename": file_path_obj.name,
            "file_path": str(file_path_obj.absolute()),
            "file_size": stat.st_size,
            "file_extension": file_path_obj.suffix.lower(),
            "mime_type": mimetypes.guess_type(str(file_path_obj))[0],
            "category": get_file_category(file_path),
            "is_supported": is_supported_file(file_path),
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "file_hash": calculate_file_hash(file_path)
        }
    except Exception as e:
        logger.error(f"Failed to get file info for {file_path}: {e}")
        return {
            "filename": Path(file_path).name,
            "error": str(e)
        }

def validate_file_access(file_path: str) -> Tuple[bool, str]:
    """Validate that a file can be accessed for reading."""
    try:
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return False, f"File does not exist: {file_path}"
        
        if not file_path_obj.is_file():
            return False, f"Path is not a file: {file_path}"
        
        if not os.access(file_path, os.R_OK):
            return False, f"File is not readable: {file_path}"
        
        # Try to open the file
        with open(file_path, 'rb') as f:
            f.read(1)  # Try to read one byte
        
        return True, "File is accessible"
        
    except Exception as e:
        return False, f"File access error: {str(e)}"

def estimate_processing_time(file_size: int, file_type: str = "text") -> float:
    """Estimate processing time for a file based on size and type."""
    # Base processing rates (bytes per second)
    base_rates = {
        "text": 100000,      # 100KB/s
        "documents": 50000,   # 50KB/s (requires parsing)
        "data": 200000,      # 200KB/s
        "web": 75000,        # 75KB/s
        "code": 150000,      # 150KB/s
        "unknown": 50000     # Conservative estimate
    }
    
    rate = base_rates.get(file_type, base_rates["unknown"])
    return file_size / rate

def batch_validate_files(file_paths: List[str]) -> Dict[str, Any]:
    """Validate a batch of files and return summary."""
    results = {
        "total_files": len(file_paths),
        "valid_files": [],
        "invalid_files": [],
        "supported_files": [],
        "unsupported_files": [],
        "total_size": 0,
        "estimated_processing_time": 0,
        "file_categories": {}
    }
    
    for file_path in file_paths:
        is_valid, message = validate_file_access(file_path)
        
        if is_valid:
            results["valid_files"].append(file_path)
            
            file_info = get_file_info(file_path)
            category = file_info.get("category", "unknown")
            
            # Update statistics
            results["total_size"] += file_info.get("file_size", 0)
            results["file_categories"][category] = results["file_categories"].get(category, 0) + 1
            
            # Check if supported
            if file_info.get("is_supported", False):
                results["supported_files"].append(file_path)
                
                # Add to processing time estimate
                processing_time = estimate_processing_time(
                    file_info.get("file_size", 0),
                    category
                )
                results["estimated_processing_time"] += processing_time
            else:
                results["unsupported_files"].append(file_path)
        else:
            results["invalid_files"].append({
                "file_path": file_path,
                "error": message
            })
    
    return results

def filter_files_by_size(file_paths: List[str], 
                        min_size: int = 0, 
                        max_size: int = None) -> List[str]:
    """Filter files by size constraints."""
    filtered_files = []
    
    for file_path in file_paths:
        try:
            file_size = Path(file_path).stat().st_size
            
            if file_size >= min_size:
                if max_size is None or file_size <= max_size:
                    filtered_files.append(file_path)
        except Exception as e:
            logger.warning(f"Could not get size for {file_path}: {e}")
    
    return filtered_files

def deduplicate_files(file_paths: List[str]) -> Tuple[List[str], List[str]]:
    """Remove duplicate files based on content hash."""
    unique_files = []
    duplicate_files = []
    seen_hashes = set()
    
    for file_path in file_paths:
        file_hash = calculate_file_hash(file_path)
        
        if file_hash and file_hash not in seen_hashes:
            seen_hashes.add(file_hash)
            unique_files.append(file_path)
        else:
            duplicate_files.append(file_path)
    
    return unique_files, duplicate_files

def organize_files_by_type(file_paths: List[str]) -> Dict[str, List[str]]:
    """Organize files by their category/type."""
    organized = {}
    
    for file_path in file_paths:
        category = get_file_category(file_path)
        
        if category not in organized:
            organized[category] = []
        
        organized[category].append(file_path)
    
    return organized

def create_file_manifest(file_paths: List[str]) -> Dict[str, Any]:
    """Create a manifest of files with metadata."""
    manifest = {
        "created_at": str(Path().cwd()),
        "total_files": len(file_paths),
        "files": []
    }
    
    for file_path in file_paths:
        file_info = get_file_info(file_path)
        manifest["files"].append(file_info)
    
    return manifest