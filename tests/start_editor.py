import os
import pathlib
import subprocess

# Below doesnt work
#arglist = ["vim", pathlib.Path.home() / "Documents/testfile.txt"]
#obj_return = subprocess.run(arg_string, shell=True, text=True, capture_output=True)

file_path = pathlib.Path.home() / "Documents/testfile.txt"
arg_string = f"vim {file_path}"

os.system(f"vim {file_path}")

with file_path.open("r") as f:
    text = f.readlines()
output = "".join(text)
print()
print(output)