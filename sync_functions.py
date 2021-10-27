from time import time
from helpers import *
from db_helpers import save_folder_state
import os
import subprocess
import logging
import json

""" Syncs 2 folders (or 2 files). Depends on python3 (with imports above), rsync and sqlite.
"""

LOGGER = logging.getLogger(__name__)

def two_way_sync(pair_id, source, target, delete, dry_run, verbose):

    start_time = time()
    
    excl_src = Excluder.create_excluder(source, pair_id)
    excl_tar = Excluder.create_excluder(target, pair_id)

    LOGGER.debug(f"Time for excluder_objects creation {round(time() - start_time, 2)}")
    time_point = time()

    source_files = create_file_dict(source, excl_src)
    target_files = create_file_dict(target, excl_tar)

    LOGGER.debug(f"Time for create_file_dicts {round(time() - time_point, 2)}")
    time_point = time()
    
    sync_obj = Syncer(pair_id, source, target, source_files, target_files)
    LOGGER.debug(f"Time to create Syncer {round(time() - time_point, 2)}")

    del source_files # No longer needed. Memory intensive.
    del target_files # No longer needed. Memory intensive.
    
    # TODO Remove only for testing
    return

    sync_obj, del_src_obj, del_tar_obj = \
        create_sync_objects(source, target, source_files, target_files, pair_id)

    time_point = time()

    # DOES THE DELETIONS
    has_deleted = False
    if not del_src_obj.is_empty() or not del_tar_obj.is_empty():
        if delete and not dry_run:
            print()
            del_src_obj.delete_items()
            has_deleted = True
            del_tar_obj.delete_items()
        elif delete and dry_run:
            print("\nTHE FOLLOWING ITEMS WOULD HAVE BEEN DELETED!: (dry run)\n")
            del_src_obj.dryrun_delete_items()
            del_tar_obj.dryrun_delete_items()
        LOGGER.debug(f"Time for deleting {round(time() - time_point)}")
    else:
        if delete and verbose:
            print("\nTHERE ARE NO ITEMS TO DELETE!")

    # RETURNS IF sync_obj IS EMPTY AND NO DELETIONS HAS OCCURED!
    if sync_obj.is_empty():
        if delete and not has_deleted:
            print("\nFOLDERS ARE COMPLETELY IN SYNC!\n")
            return
        elif not delete:
            print("\nFOLDERS ARE ALREADY IN SYNC! (at least with deletions deactivated)\n")
            return
    
    # Checks that same path doesnt exist both in lr_set and rl_set which could
    # happen if file exists on one side with same name as dir on other side.
    time_point = time()
    sync_obj.remove_intersection(verbose)
    LOGGER.debug(f"Time for intersection testing: {round(time() - time_point, 2)}")
    
    if dry_run and verbose:
        # Function ends before this if sync object is empty, see above!
        print("\nTHE FOLLOWING ITEMS WOULD HAVE BEEN UPDATED/CREATED!: (dry run)")
        
    # SYNCS AND CHECKS RETURN CODES
    return_src_to_tar, return_tar_to_src = sync_obj.sync(False, dry_run, verbose)
    ok_exit_codes = {0, 49, 50} # O = OK, 49 = aborted by user, 50 = already synced
    print() # Newline needed!
    if verbose and return_src_to_tar in ok_exit_codes and return_tar_to_src in ok_exit_codes:
        print("Two-way-syncing completed without error!")
    elif verbose:
        print("Two-way-sync encountered an error!")
        
    # Gets items that should be saved to json.file
    time_point = time()
    item_dict = get_existing_items(source, target, del_src_obj, del_tar_obj)
    LOGGER.debug(f"Time for get_existing_items: {round(time() - time_point, 2)}")

    time_point = time()
    if save_folder_state(source, target, item_dict, pair_id) == 0:
        if verbose:
            print("\nSuccesfully saved folder state!")
    else:
        if verbose:
            print(f"\nCouldn't save folder state. Folder pair will have to be reinitialized before next sync!")

    LOGGER.debug(f"Time for saving folder state: {round(time() - time_point, 2)}")
    LOGGER.debug(f"Total time elapsed: {round(time() - start_time, 2)}")
    

def create_file_dict(top_directory, excl_obj=None):
    """Uses os.walk to go through top_directory including subdirectory to
    create file_dict. 
    - file_dict uses root directory (path relative
    to top_directory) as key and has inner_dict as value. 

    Args:
        top_directory {string}: path to top directory. Can be relative or absolute.

    Returns:
        file_dict {dictionary}: see above
    """

    top_directory = os.path.abspath(top_directory)
    working_dir = os.getcwd()
    os.chdir(top_directory)
    file_dict = {}

    for basedir, dirs, files in os.walk(top_directory, topdown=True):

        basedir = os.path.relpath(basedir,top_directory)

        # Seems this part is needed to copy symlink to dirs
        # TODO Maybe delete this part? Too much overhead?
        for a_dir in dirs:
            rel_file_path = os.path.join(basedir, a_dir)
            if os.path.islink(rel_file_path):
                files.append(a_dir)

        if excl_obj and excl_obj.excl_dict:
            file_dict[basedir] = excl_obj.get_non_excl_file_set(basedir, files)
        else:
            file_dict[basedir] = set(files)

        if excl_obj and excl_obj.dirs:
            # Keeps os.walk from going into excluded dirs!
            dirs[:] = [d for d in dirs if os.path.join(basedir, d) not in excl_obj.dirs]

    os.chdir(working_dir)
    return file_dict


def create_sync_objects(source, target, src_files, tar_files, pair_id):
    dirs, files = set(), set()

    def get_saved_items():
        json_filepath = get_json_path(pair_id)
        with open(json_filepath, "r") as json_file:
            state_dict = json.load(json_file)
        for dir in state_dict["items"]:
            dirs.add(dir)
            for item in state_dict["items"][dir]:
                files.add(os.path.join(dir, item))
        
        dirs.discard("")
        return

    def dir_existed(a_dir):
        return a_dir in dirs

    def file_existed(a_file):
        return a_file in files

    def add_or_delete_item(a_file, add_set, del_obj):
        if file_existed(a_file):
            del_obj.files.add(a_file)
        else:
            add_set.add(a_file)

    def add_or_delete_folder(root_path, dict_of_files_in_root, add_set, 
        del_obj):
        # Note that function handles adding and deletions differently since
        # there is a need to seperate files and dirs for deletions but not for adding.
        # Checks if folder existed in previous sync
        if dir_existed(root_path):
            del_obj.dirs.add(root_path)
            choosen_set = del_obj.files_in_deleted_dirs
        else:
            add_set.add(root_path)
            choosen_set = add_set

        for item in dict_of_files_in_root:
            choosen_set.add(item)

    get_saved_items()
    del_src, del_tar = Deleter(source), Deleter(target) 
    sync_obj = Syncer(source, target)
    left_to_right, right_to_left = sync_obj.lr_items, sync_obj.rl_items 

    # Loop through all keys in src_files. Root corresponds to existing dirs
    for root in src_files:
        basedir_src = src_files[root]
        if root in tar_files:
            # Current root (dir) exist both in source and target!
            basedir_tar = tar_files[root]
            # Loop through all files in dir
            for item in basedir_src:
                if item in basedir_tar:
                    # File in both source and target! Compare files.
                    srcfile_path = os.path.join(source, item)
                    tarfile_path = os.path.join(target, item)
                    mod_time_srcfile = (os.lstat(srcfile_path)).st_mtime
                    mod_time_tarfile = (os.lstat(tarfile_path)).st_mtime
                    date_diff = mod_time_srcfile - mod_time_tarfile 

                    # TODO floating point arithmetics might cause errors. Rethink.
                    if date_diff > 0:
                        left_to_right.add(item)
                    elif date_diff < 0:
                        right_to_left.add(item)

                    # Delete key from target dict
                    basedir_tar.remove(item)
                else: 
                    # File only in source not in target
                    add_or_delete_item(item, left_to_right, del_src)
                    
            # Checks if there are files exclusive to target (not in source)
            for item in basedir_tar:
                add_or_delete_item(item, right_to_left, del_tar)
            # delete key corresponding to root from tar_files
            del tar_files[root]

        else:
            # root exists in source but not in target
            add_or_delete_folder(root, basedir_src, left_to_right, 
            del_src)

    # Only remaining roots in tar_files exists only in target (not in source).
    for root in tar_files:
        add_or_delete_folder(root, tar_files[root], right_to_left, 
        del_tar)

    return sync_obj, del_src, del_tar


def get_existing_items(source, target, del_obj_src=None, del_obj_tar=None):
    """Function generates a list of items (files or dirs) that exist in both
    source and target dir after syncing. Then it adds items existing 
    on only 1 side (either) if they coexist in delete objects.
    """
    src_items = create_file_dict(source)
    tar_items = create_file_dict(target)

    # Below operation returns a set after intersection is made.
    src_dirs, tar_dirs = set(src_items.keys()), set(tar_items.keys())
    mutual_dirs = src_dirs & tar_dirs
    all_dirs = src_dirs | tar_dirs
    mutual_files, all_files = set(), set()

    for dir in all_dirs:
        src_files = src_items.get(dir, set())
        tar_files = tar_items.get(dir, set())
        mutual_files_in_dir = src_files & tar_files
        all_files_in_dir = src_files | tar_files
        mutual_files.update(mutual_files_in_dir)
        all_files.update(all_files_in_dir)
        
    if del_obj_src and del_obj_tar:
        delete_dirs = del_obj_src.dirs | del_obj_tar.dirs
        delete_files = del_obj_src.get_all_files() | del_obj_tar.get_all_files()
        exclusive_dirs = all_dirs - mutual_dirs
        exclusive_files = all_files - mutual_files

        # extra here references that these files need to 'exist' in db to be
        # deleted when user turns on deletions. If programs work deletions=False 
        # should be the only reason for items to exist in extra_dirs and extra_files.
        extra_dirs = delete_dirs & exclusive_dirs
        extra_files = delete_files & exclusive_files
        dirs = mutual_dirs | extra_dirs
        files = mutual_files | extra_files
        
    elif del_obj_src or del_obj_tar:
        raise ValueError("Provide zero or two delete objects. Not 1!")
    else:
        files = mutual_files
        dirs = mutual_dirs

    item_dict = {}
    for dir in dirs:
        # HAVE TO USE LISTS SINCE SETS CANNOT BE SAVED TO JSON
        item_dict[dir] = []
    
    for item in files:
        file_name, dir = os.path.basename(item), os.path.dirname(item)
        # TODO: Not sure below if condition is necessary.
        if not dir in item_dict:
            LOGGER.debug(f"dir path: {dir} was no in dirs but in files!")
            item_dict[dir] = []
        item_dict[dir].append(file_name)

    return item_dict


def rsync(source, target, delete=False, dryrun=False, print_output=True, user_interaction=True):
    """Summary: Sync using rsync as subprocess. This function greatly simplifies
    rsync because of default flag behavior, see below. Use original rsync 
    if greater flexibility is needed.
    To run function interactively keep defaults except possibly set delete=True.
    To run automated (ie with chron) use print_output=False and user_interaction=False.

    Args:
        source {string}: String to source directory/file.
        target {string}: String to target directory/file.
        delete {bool}: Wether to delete files in target that doesnt exist in source.
        dryrun {bool}: If true run rsync ones with --dry-run flag. If true ignores user_interaction=True.
        prin_output {bool}: If true prints output.
        user_interaction: If true and dryrun=False --> runs 1 inital dryrun and gives user choose to continue or not.
    
    Returns:
        Most often propagates returncode from rsync call itself.
        Have the following function specified returncodes (not from rsync)
        aborted_by_user = 49
        already_synced = 50
    """
    
    def run_rsync(rsync_arglist):
        obj_return = subprocess.run(rsync_arglist, text=True, capture_output=True)

        if obj_return.stdout:
            if print_output:
                print(format_rsync_output(obj_return.stdout))
        else:
            if not obj_return.stderr:
                if print_output:
                    print("Folders are already completely synced!")

                already_synced = 50
                return already_synced

        if obj_return.stderr:
            # TODO maybe write to logfile if print_output=False
            print(obj_return.stderr)

        if not obj_return.returncode == 0:
            # TODO maybe write to logfile if print_output=False
            print("Something went wrong in rsync call!")

        return obj_return.returncode
        
    rsync_arglist = ["rsync", "-a", "--itemize-changes"]

    if delete:
        rsync_arglist.append("--delete")

    rsync_arglist.append(source)
    rsync_arglist.append(target)

    # User interaction only takes place if user_interaction=True AND dryrun=False
    if user_interaction and not dryrun: 
        return_code = run_rsync(rsync_arglist + ["--dry-run"])
        if return_code != 0:
            return return_code
        
        print("\nAbove output was only a dry run. Nothing has happended. If the result looks desirable choose yes in next step!")

        user_input = ""
        while not user_input in {"y", "yes", "n", "no"}:
            user_input = input(f"\nDo you want to continue (sync for real)? (y/yes, n/no)\n--> ")
            user_input = user_input.strip().lower()
        if user_input == "n" or user_input == "no":
            print("Exiting program...")
            aborted_by_user = 49
            return aborted_by_user        
    elif dryrun:
        rsync_arglist.append("--dry-run")

    return run_rsync(rsync_arglist)


def create_file_dict_old(top_directory):
    """Uses os.walk to go through top_directory including subdirectory to
    create file_dict. 
    - file_dict uses root directory (path relative
    to top_directory) as key and has inner_dict as value. 

    Args:
        top_directory {string}: path to top directory. Can be relative or absolute.

    Returns:
        file_dict {dictionary}: see above
    """

    top_directory = os.path.abspath(top_directory)
    working_dir = os.getcwd()
    os.chdir(top_directory)
    file_dict = {}
    first_dir = True

    for basedir, folders, files in os.walk(top_directory):
        if not first_dir:
            basedir = os.path.relpath(basedir,top_directory)
        else:
            basedir = ""
            first_dir = False

        file_dict[basedir] = set()
        files_in_basedir = file_dict[basedir]
        for a_file in files:
            rel_file_path = os.path.join(basedir, a_file)
            files_in_basedir.add(rel_file_path)
        
        for a_dir in folders:
            rel_file_path = os.path.join(basedir, a_dir)
            if os.path.islink(rel_file_path):
                files_in_basedir.add(rel_file_path)

    os.chdir(working_dir)
    return file_dict


def two_way_sync_old(pair_id, source, target, delete, dry_run, verbose):
    # TODO Add some kind of ignore list. ex .tmp files should be ignored.

    start_time = time()
    source_files = create_file_dict(source)
    LOGGER.debug(f"Time for create_file_dict 1 {round(time() - start_time, 2)}")
    time_point = time()
    target_files = create_file_dict(target)
    LOGGER.debug(f"Time for create_file_dict 2 {round(time() - time_point, 2)}")
    time_point = time()
    sync_obj, del_src_obj, del_tar_obj = \
        create_sync_objects(source, target, source_files, target_files, pair_id)
    LOGGER.debug(f"Time for create_sync_sets {round(time() - time_point, 2)}")
    #LOGGER.debug(f"lr list: {lr_set}\nrl list: {rl_set}\ndel src list: {del_src_obj}\ndel tar list: {del_tar_obj}")

    # DOES THE DELETIONS
    has_deleted = False
    if not del_src_obj.is_empty() or not del_tar_obj.is_empty():
        time_point = time()
        if delete and not dry_run:
            print()
            del_src_obj.delete_items()
            has_deleted = True
            del_tar_obj.delete_items()
        elif delete and dry_run:
            print("\nTHE FOLLOWING ITEMS WOULD HAVE BEEN DELETED!: (dry run)\n")
            del_src_obj.dryrun_delete_items()
            del_tar_obj.dryrun_delete_items()
        LOGGER.debug(f"Time for deleting {round(time() - time_point)}")
    else:
        if delete and verbose:
            print("\nTHERE ARE NO ITEMS TO DELETE!")

    # RETURNS IF sync_obj IS EMPTY AND NO DELETIONS HAS OCCURED!
    if sync_obj.is_empty():
        if delete and not has_deleted:
            print("\nFOLDERS ARE COMPLETELY IN SYNC!\n")
            return
        elif not delete:
            print("\nFOLDERS ARE ALREADY IN SYNC! (at least with deletions deactivated)\n")
            return
    
    # Checks that same path doesnt exist both in lr_set and rl_set which could
    # happen if file exists on one side with same name as dir on other side.
    time_point = time()
    sync_obj.remove_intersection(verbose)
    LOGGER.debug(f"Time for intersection testing: {round(time() - time_point, 2)}")
    
    if dry_run and verbose:
        # Function ends before this if sync object is empty, see above!
        print("\nTHE FOLLOWING ITEMS WOULD HAVE BEEN UPDATED/CREATED!: (dry run)")
        
    # SYNCS AND CHECKS RETURN CODES
    return_src_to_tar, return_tar_to_src = sync_obj.sync(False, dry_run, verbose)
    ok_exit_codes = {0, 49, 50} # O = OK, 49 = aborted by user, 50 = already synced
    print() # Newline needed!
    if verbose and return_src_to_tar in ok_exit_codes and return_tar_to_src in ok_exit_codes:
        print("Two-way-syncing completed without error!")
    elif verbose:
        print("Two-way-sync encountered an error!")
        
    # Gets items that should be saved to json.file
    time_point = time()
    item_dict = get_existing_items(source, target, del_src_obj, del_tar_obj)
    LOGGER.debug(f"Time for get_existing_items: {round(time() - time_point, 2)}")

    time_point = time()
    if save_folder_state(source, target, item_dict, pair_id) == 0:
        if verbose:
            print("\nSuccesfully saved folder state!")
    else:
        if verbose:
            print(f"\nCouldn't save folder state. Folder pair will have to be reinitialized before next sync!")

    LOGGER.debug(f"Time for saving folder state: {round(time() - time_point, 2)}")
    LOGGER.debug(f"Total time elapsed: {round(time() - start_time, 2)}")