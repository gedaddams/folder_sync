import sync_functions
import json
import os
import sys
import pathlib
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

def pathlib_create_file_dict(top_dir):
    wd = pathlib.Path.cwd()
    os.chdir(top_dir)
    try:
        path = pathlib.Path()
        #item_list = list(path.glob("**/*"))
        item_dict = {}
        for item in path.glob("**/*"):
            if item.is_dir() and not item.is_symlink():
                item_path = str(item)
                # TODO unsure wether this if is needed. TEST IT.
                if item_path.endswith(os.sep):
                    item_path = item_path[:-1]
                if not item_path in item_dict:
                    item_dict[item_path] = set() 
            else:
                basedir = str(item.parent)
                if basedir == ".":
                    basedir = ""
                name = item.name
                if not basedir in item_dict:
                    item_dict[basedir] = set()
                item_dict[basedir].add(name)
    finally:
        os.chdir(wd)
        return item_dict

def test_old_create_file_dict_no_excludes(top_dir):
    return sync_functions.create_file_dict(top_dir)

def test_new_create_file_dict_with_excludes(top_dir):
    time_point = time()
    excl_list = ["Lightroom/", "_SYNCAPP/", "Egna bilder/Kamerabilder/_SYNCAPP", "*.txt"]
    excl_obj = Excluder(top_dir, excl_list)
    file_dict = sync_functions.create_file_dict_new(top_dir, excl_obj)

def compare_create_dict_funcs():
    test_dir = "/share/media/Mina bilder"
    #test_dir = "/mnt/d/mina bilder"
    #test_dir = "/home/ged/Documents/"
    time_point = time()
    dict1 = pathlib_create_file_dict(test_dir)
    print(f"Time for pathlib create dict: {round(time() - time_point, 1)}")
    print(len(dict1))
    time_point = time()
    dict2 = sync_functions.create_file_dict_new(test_dir)
    print(f"Time for old create dict: {round(time() - time_point, 1)}")
    print(len(dict2))
    
    diff_set = dict1.keys() ^ dict2.keys()
    common_set = dict1.keys() & dict2.keys()
    for key_value in diff_set:
        print(f"Diff key value: {key_value}")
        
    for key_value in common_set:
        dict1_set = set() if dict1[key_value] == None else dict1[key_value]
        dict2_set = set() if dict2[key_value] == None else dict2[key_value]
        dict1_only = dict1_set - dict2_set
        dict2_only = dict2_set - dict1_set
        for item in dict1_only:
            print(f"Only in pathlib_dict {key_value}: {item}")
        for item in dict2_only:
            print(f"Only in old_dict {key_value}: {item}")

if __name__ == "__main__":
    compare_create_dict_funcs()