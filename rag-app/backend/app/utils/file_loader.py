"""File loader utility"""
import os
from pathlib import Path
from typing import Optional


class FileLoader:
    """Utility for loading files"""
    
    @staticmethod
    def load_text_file(file_path: str, encoding: str = "utf-8") -> str:
        """Load text from a file"""
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    
    @staticmethod
    def load_json_file(file_path: str) -> dict:
        """Load JSON from a file"""
        import json
        with open(file_path, "r") as f:
            return json.load(f)
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Get file extension"""
        return Path(file_path).suffix
