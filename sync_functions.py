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

def two_way_sync(pair_id, source, target, delete, dry_run, verbose, interactive=True):

    start_time = time()
    
    excl_src = Excluder.create_excluder(source, pair_id)
    excl_tar = Excluder.create_excluder(target, pair_id)

    LOGGER.debug(f"Time for excluder_objects creation {round(time() - start_time, 2)}")
    time_point = time()

    source_files = create_file_dict(source, excl_src)
    target_files = create_file_dict(target, excl_tar)

    LOGGER.debug(f"Time for create_file_dicts {round(time() - time_point, 2)}")
    time_point = time()
    
    sync_obj = Syncer(pair_id, source, target, source_files, target_files,
                delete, dry_run, verbose)
    LOGGER.debug(f"Time to create Syncer {round(time() - time_point, 2)}")
    
    if interactive:
        sync_obj.dryrun = True
        delete_and_sync(sync_obj)
        user_input = ""
        while not user_input in {"y", "yes", "n", "no"}:
            user_input = input(f"\nThis was only a trial run. Do you want to sync for real? (y/yes, n/no)\n--> ")
            user_input = user_input.lower() 
        if user_input in {"y", "yes"}:
            sync_obj.dryrun = False
            delete_and_sync(sync_obj)

    else: # If not interactive mode only delete and sync once
        delete_and_sync(sync_obj)
    
    sync_obj.remove_textfiles()
    
    if not sync_obj.dryrun:
        state_dict = sync_obj.get_new_state_dict()
        save_folder_state(source, target, state_dict, pair_id)

    return
    

def delete_and_sync(sync_obj):
    time_point = time()
    sync_obj.delete()
    LOGGER.debug(f"Time to delete: {round(time() - time_point, 2)}")

    doubles = sync_obj.remove_doubles()
    if doubles:
        # This happens if dir on one side is added, since last saved state, 
        # simultaneously as file on other side was added.
        LOGGER.critical("\nNon identified doubles exists! This most likely" +
        "depends on file on one side having the same name as dir on the other!")
        LOGGER.critical("Aborting sync manual review of the following items are necessary:\n")
        doubles[0].print_items()
        doubles[1].print_items()
        print()
        sys.exit(4)
            
    sync_obj.sync()



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


def get_existing_items(source, target, del_obj_src=None, del_obj_tar=None):
    """Function generates a list of items (files or dirs) that exist in both
    source and target dir after syncing.  
    """
    # TODO this function is now overly simplified only usable after a complete
    # rsync with delete active. Does not take failed deletions or addtions
    # into account.

    src_items = create_file_dict(source)
    tar_items = create_file_dict(target)

    # Below operation returns a set after intersection is made.
    src_dirs, tar_dirs = set(src_items.keys()), set(tar_items.keys())

    sym_diff_dirs = src_dirs ^ tar_dirs
    if sym_diff_dirs:
        return "error"
    
    mutual_dirs = src_dirs & tar_dirs
    item_dict = {}

    for dir in mutual_dirs:
        src_files = src_items.get(dir, set())
        tar_files = tar_items.get(dir, set())
        sym_diff_files = src_files ^ tar_files
        if sym_diff_files:
            return "error"
        
        item_dict[dir] = list(src_files & tar_files)

    print()
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