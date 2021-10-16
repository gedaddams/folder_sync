from time import time
from helpers import File
import os
import subprocess
import logging

""" Syncs 2 folders (or 2 files). Depends on python3 (with imports above), rsync and sqlite.
"""

logger = logging.getLogger(__name__)
    
def sync(source, target, delete, dry_run, verbose):
    # TODO Add some kind of ignore list. ex .tmp files should be ignored.

    start_time = time()
    source, target = os.path.abspath(source), os.path.abspath(target)
    time_point = time()
    logger.debug(f"Time for setup {round(time_point-start_time, 2)}")
    source_files = create_file_dict(source)
    logger.debug(f"Time for create_file_dict 1 {round(time() - time_point, 2)}")
    time_point = time()
    target_files = create_file_dict(target)
    logger.debug(f"Time for create_file_dict 2 {round(time() - time_point, 2)}")
    time_point = time()
    lr_list, rl_list, del_src, del_tar = create_sync_lists(source, target, source_files, target_files)
    logger.debug(f"Time for create_sync_lists {round(time() - time_point, 2)}")
    time_point = time()
    #logger.debug(f"lr list: {lr_list}\nrl list: {rl_list}\ndel src list: {del_src}\ndel tar list: {del_tar}")

    # Returns if all relevant lists are empty!
    if not lr_list and not rl_list:
        if delete:
            if not del_src and not del_tar:
                return
        else:
            return
    
    script_dir = os.path.dirname(os.path.realpath(__file__))
    lr_filepath = os.path.join(script_dir, "lr_sync.tmp")
    rl_filepath = os.path.join(script_dir, "rl_sync.tmp")
    
    with open(lr_filepath, 'w') as file_lr:
        file_lr.writelines([line + '\n' for line in lr_list])
    with open(rl_filepath, 'w') as file_rl:
        file_rl.writelines([line + '\n' for line in rl_list])
        
    # TODO. Here happens the actual syncing.
    #return_lr = rsync(source, target, delete, dry_run, verbose, False, True, lr_filepath)
    #return_rl = rsync(source, target, delete, dry_run, verbose, False, True, rl_filepath)

#    TODO DO THE DELETIONS
    logging.debug(f"Total time elapsed: {round(time() - start_time, 2)}")

    # TODO Delete the files after syncing


def create_file_dict(top_directory):
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

    for basedir, _, files in os.walk(top_directory):
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

    os.chdir(working_dir)
    return file_dict


def item_existed(a_file):
    # TODO check wether file/folder existed in previous sync --> return true/false
    # Will need to check vs sqlite database
    return False


def create_sync_lists(source, target, src_files, tar_files):
    # TODO Figure out how to handle if there exist dir on one side with same
    # path as file on other side. Maybe always append dir even if have files
    # and do some kind of set union?
    def add_or_delete_item(a_file, add_list, del_list):
        if item_existed(a_file):
            del_list.append(a_file)
        else:
            add_list.append(a_file)

    def add_or_delete_folder(root_path, dict_of_files_in_root, add_list, del_list):
        # Checks if folder existed in previous sync
        if item_existed(root_path):
            choosen_list = del_list
        else:
            choosen_list = add_list

        # If no files in dir append dir itself.
        if not dict_of_files_in_root:
            choosen_list.append(root_path)
        else:
            # If there are files in dir append the files.
            for item in dict_of_files_in_root:
                choosen_list.append(item)

    left_to_right, right_to_left, delete_list_src, delete_list_tar = [], [], [], []
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
                        left_to_right.append(item)
                    elif date_diff < 0:
                        right_to_left.append(item)

                    # Delete key from target dict
                    basedir_tar.remove(item)
                else: 
                    # File only in source not in target
                    add_or_delete_item(item, left_to_right, delete_list_src)
                    
            # Checks if there are files exclusive to target (not in source)
            for item in basedir_tar:
                add_or_delete_item(item, right_to_left, delete_list_tar)
            # delete key corresponding to root from tar_files
            del tar_files[root]

        else:
            # root exists in source but not in target
            add_or_delete_folder(root, basedir_src, left_to_right, delete_list_src)

    # Only remaining roots in tar_files exists only in target (not in source).
    for root in tar_files:
        add_or_delete_folder(root, tar_files[root], right_to_left, delete_list_tar)

    return left_to_right, right_to_left, delete_list_src, delete_list_tar
    

def format_rsync_output(st_ouput):
    # This formating function will only work reliable if not using -v or -P for rsync call.
    # You also have to use --itemize-changes flag.
    output_list = st_ouput.split(os.linesep)
    if output_list[-1] == "":
        output_list.pop()

    msg_list, created, modified = [], [], []
    file_types = {
        "f": "file: ", 
        "d": "directory: ", 
        "L": "symlink: ",
        "D": "DEVICE: ",
        "S": "SPECIAL FILE: "}
    
    for line in output_list:
        words = line.split()

        len_words = len(words)
        if len_words == 2:
            prefix, file = words[0], words[1]
        elif len_words > 2:
            # Below join is needed for filenames with whitespace in them
            prefix, file = words[0], " ".join(words[1:])
        else:
            # This shouldnt happen!
            msg_list.append(line)
            continue

        change = prefix[0]
        if change == "*": # Message (often deletion)
            msg_list.append(line)
            continue
        elif change == "<" or change == ">":
            if prefix[2:] == "+++++++++":
                new_prefix = "Created "
                choosen_list = created
            else:
                new_prefix = "Updated "
                choosen_list = modified
        elif change == "c":
            new_prefix = "Created "
            choosen_list = created
        elif change == ".":
            # File not updated. Skip.
            continue
        else:
            # Cannot cleanup.
            msg_list.append(line)
            continue
        
        filetype = ""
        type_of_file = prefix[1]
        if type_of_file in file_types:
            filetype = file_types[type_of_file]

        lacking_whitespace = 30 - (len(new_prefix) + len(filetype))
        if lacking_whitespace > 0:
            spaces = ' ' * lacking_whitespace
        else:
            spaces = ""
        choosen_list.append((new_prefix + filetype + spaces + file))

    msg_list.sort()
    created.sort()
    modified.sort()
    return_list = msg_list + [""] + created + [""] + modified
    return (os.linesep).join(return_list)


def rsync(source, target, delete=False, dryrun=False, print_output=True, user_interaction=True, from_file=False, file_path=None):
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
        from_file_without_valid_filepath = 51
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

    if from_file:
        from_file_without_valid_filepath = 51
        if file_path:
            if os.path.isfile(file_path):
                files_from_arg = "--files-from=" + file_path
                rsync_arglist.append(files_from_arg)
            else:
                return from_file_without_valid_filepath
        else:
            return from_file_without_valid_filepath
        
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