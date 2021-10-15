import os

dir1 = "/home/ged/Documents"
dir2 = "/home/ged/Documents/"

def adjust_dirname(dirname):
    return os.path.abspath(dirname) + os.path.sep

print(f"dir1 before function is {dir1}")
print(f"dir2 before function is {dir2}")

print(f"dir1 passed through function is {adjust_dirname(dir1)}")
print(f"dir2 passed through function is {adjust_dirname(dir2)}")
