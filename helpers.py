"""This module contains classes and helper functions"""
from time import strftime, localtime

class File:
    def __init__(self, modified, size) -> None:
        self.modified = modified
        self.size = size
        
    def compare_files(self, file):
        if not isinstance(file, File):
            return NotImplemented
        if self.modified == file.modified:
            return "equal"
        elif self.modified > file.modified:
            return "newer"
        else:
            return "older"
    
    def __repr__(self) -> str:
        return f"(Last modified: {strftime('%Y-%m-%d %H:%M:%S', localtime(self.modified))}, Size: {self.size})"