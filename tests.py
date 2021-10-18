import sync_functions

def test_get_existing_items_no_delete_objects():
    source = "/home/ged/Documents/testdir/"
    target = "/home/ged/Documents/testdir_copy/"
    
    dirs, files = sync_functions.get_existing_items(source, target)
    print(f"Dirs: {dirs}")
    print(f"Files: {files}")

if __name__ == "__main__":
    test_get_existing_items_no_delete_objects()