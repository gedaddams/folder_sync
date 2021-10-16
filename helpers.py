"""This module contains classes and helper functions"""
from time import strftime, localtime

class Deleted_items:
    __slots__ = ["files", "dirs", "files_in_deleted_dirs"]
    
    def __init__(self) -> None:
        self.files = set()
        self.dirs = set()
        self.files_in_deleted_dirs = set()
        
    def get_all_items(self):
        return self.files.union(self.dirs, self.files_in_deleted_dirs)


class File:
    # Since there are so many instances of the File class when syncing large
    # folders. __slots__ makes properties go inside fixed sized list instead of __dict__
    # resulting in non trivial memory and speed gains.
    __slots__=["modified", "size"]

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