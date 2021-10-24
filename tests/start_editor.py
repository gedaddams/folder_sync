import os
import pathlib
import subprocess

file_path = pathlib.Path.home() / "Documents/testfile.txt"

arglist = ["vim", file_path]
obj_return = subprocess.run(arglist)
print(obj_return.returncode)

with file_path.open("r") as f:
    text = [line.split(maxsplit=1) for line in f.readlines()]

for item in text:
    print(f"Column 1: {item[0]}")
    print(f"Column 2: {item[1]}")
