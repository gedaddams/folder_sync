from helpers import Hash_path

path = Hash_path("/home/ged/Documents")
print(path)
str_path = "/home/ged/Documents"
only_string = "/only/string"
only_obj = Hash_path("only/object")

set_a = set()
set_b = set()

set_a.add(path)

if str_path in set_a:
    print("it works")

set_b.add(path)
set_b.add(only_string)
set_a.add(only_obj)

set_union = set_a & set_b
print(set_union)