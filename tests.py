import sync_functions
import json
from time import time

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

if __name__ == "__main__":
    #test_get_existing_items_no_delete_objects()
    test_json("/home/ged/")