import sync_functions
import json
import os
import sys
from helpers import Excluder
from time import time


def exclude_dir_from_os_walk(top_dir, exclude_set=None):
    excl_inner = set()
    if exclude_set and isinstance(exclude_set, set):
        excl_inner = set() | exclude_set
    
    print(f"Excl_inner: {excl_inner}")
    print(f"Exclude_set: {exclude_set}")

    for root, dirs, files in os.walk(top_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in excl_inner]
        print(root)
        print(files)


def excluder_test(excl_list):
    excl_obj = Excluder(excl_list)
    print(excl_obj)


def test_get_existing_items_no_delete_objects():
    source = "/home/ged/Documents/testdir/"
    target = "/home/ged/Documents/testdir_copy/"
    
    _, _ = sync_functions.get_existing_items(source, target)

def test_json(top_dir):
    time_point = time()
    file_dict = sync_functions.create_file_dict(top_dir)
    big_test = {}
    for base_dir in file_dict:
        big_test[base_dir] = list(file_dict[base_dir])
        
    print(f"Time to create file dict and convert values to lists: {round(time() - time_point, 1)}")

    # To write json to file use below construct
    time_point = time()
    with open("tests/test.json", "w") as outfile:
        json.dump(big_test, outfile)
    print(f"Time to write jason file {round(time() - time_point, 1)}")
        
    time_point = time()
    with open("tests/test.json", "r") as readfile:
        test_from_file = json.load(readfile)
    print(f"Time read jason file {round(time() - time_point, 1)}")
    
    print(type(test_from_file)) # --> <class 'dict'>
    #print(test_from_file)

def test_and():
    def its_true():
        print("its true")
        return True
    def its_false():
        print("its false")
        return False
    
    if its_false() and its_true():
        pass

def test_old_create_file_dict_no_excludes(top_dir):
    time_point = time()
    file_dict2 = sync_functions.create_file_dict(top_dir)
    print()
    print(f"Items in file dict: {len(file_dict2)}")
    print()
    print(f"Time to complete old file dict without excl: {round(time() - time_point, 1)}")
    print()
    print(f"Size of old file_dict: {sys.getsizeof(file_dict2)}")

def test_new_create_file_dict_with_excludes(top_dir):
    time_point = time()
    excl_list = ["Lightroom/", "_SYNCAPP/", "Egna bilder/Kamerabilder/_SYNCAPP", "*.txt"]
    #excl_list = ["bogusdir", "bogus*.txt"]
    excl_obj = Excluder(top_dir, excl_list)
    file_dict = sync_functions.create_file_dict_new(top_dir, excl_obj)
    print()
    print(f"Items in file dict: {len(file_dict)}")
    print()
    print(f"Time to complete new incl excludes: {round(time() - time_point, 1)}")
    print()
    print(f"Size of new file_dict: {sys.getsizeof(file_dict)}")
    print()

if __name__ == "__main__":
    test_new_create_file_dict_with_excludes("/mnt/d/mina bilder")
    test_old_create_file_dict_no_excludes("/mnt/d/mina bilder")