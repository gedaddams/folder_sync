"""This module contains classes and function format_rsync_output"""
import os
import sys
from time import time
import pathlib
import subprocess
import logging
import json
from shutil import rmtree
from db_helpers import get_json_path

LOGGER = logging.getLogger(__name__)
SCRIPT_PATH = pathlib.Path(__file__).parent.absolute()

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


class Excluder:
    @classmethod
    def create_excluder(cls, top_dir, pair_id):
        dir_path = SCRIPT_PATH / ".folder_sync_config" / "folder_pair_excludes"
        file_path = dir_path / ("folder_pair_" + str(pair_id) + ".txt")

        excl_list = []
        try:
            with file_path.open('r') as excl_file:
                excl_list = [line.strip() for line in excl_file.readlines()]
            excl_list = list(filter(lambda row: bool(row), excl_list))
        except:
            return None

        if excl_list:
            return cls(top_dir, excl_list)
        return None

    def __init__(self, top_dir, exclude_list):
        # TODO maybe reade excludes from file instead of list.
        self.top_dir = pathlib.Path(top_dir).absolute()
        self.dirs = set()
        self.excl_dict = {}

        for item in exclude_list:
                path = pathlib.Path(item)
                if self.__add_item(path):
                    continue
                    
                self.__glob_item(item)
        
    def __bool__(self):
        return bool(self.dirs) or bool(self.excl_dict) 

    def __glob_item(self, item):
        try:
            for path in self.top_dir.glob(item):
                self.__add_item(path)
        except Exception as error:
            LOGGER.error(error)

    def __add_item(self, path):
        """
        Args: 
        item {string}: Possibly path to item.
        
        Return {boolean}: True if matching item (link, file, dir) otherwise False
        """
        try:
            if not path.is_absolute():
                # pathlib allows joining of path with / operator
                path = self.top_dir / path

            if path.is_file() or path.is_symlink():
                dir_path = str(path.parent.relative_to(self.top_dir))
                if dir_path == ".":
                    dir_path = ""
                    
                file_name = path.name
                if not dir_path in self.excl_dict:
                    self.excl_dict[dir_path] = set()
                self.excl_dict[dir_path].add(file_name)

            elif path.is_dir():
                self.dirs.add(str(path.relative_to(self.top_dir)))

            else:
                return False

            return True

        except:
            return False
                
    def __repr__(self):
        return f"\nexcl-dirs: {self.dirs}\n\nexcl_dict: {self.excl_dict}\n"
    
    def get_non_excl_file_set(self, base_dir, file_list):
        if self.excl_dict.get(base_dir, None):
            return set(file_list) - self.excl_dict.get(base_dir, set())
        return set(file_list)


class Del_item:
    """[summary]

        Properties:
        files {dictionary}: path as string is key. PosixPath is value.
        dirs {dictionary}: path as string is key. PosixPath is value.
    """
    def __init__(self, root) -> None:
        self.files = {}
        self.dirs = {}
        self.root = root
        
    def add_file(self, item):
        if isinstance(item, pathlib.Path):
            self.files[str(item)] = item
        elif isinstance(item, str):
            self.files[item] = pathlib.Path(item)
        else:
            raise NotImplementedError

    def add_dir(self, item):
        if isinstance(item, pathlib.Path):
            self.dirs[str(item)] = item
        elif isinstance(item, str):
            self.dirs[item] = pathlib.Path(item)
        else:
            raise NotImplementedError
        
    def get_file_set(self):
        return set(self.files.keys())

    def get_dir_set(self):
        return set(self.dirs.keys())
    
    def get_dir_list(self):
        try:
            dir_list = self.dir_list
        except AttributeError:
            self.dir_list = list(self.dirs.values())
            self.dir_list.sort(reverse=True)
            dir_list = self.dir_list

        return dir_list
    
    def __repr__(self):
        return f"Del_item({self.root})"


class Dir_class:
    """
    Summary:
        Each instance of a Dir_item represents a file or a dir.

    Properties:
        self.name {string} = Name of dir
        self.excl_dir {bool} = Wether dir is new or not

    Methods:
        Mostly self explanatory. 
        __lt__ is included to add sort capability when instance is in list.
    """

    __slots__ = ["name", "excl_dir"] 

    def __init__(self, name, is_new):
        self.name = name
        self.excl_dir = is_new
    
    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Dir_class):
            return self.name == obj.name
        elif isinstance(obj, str):
            return self.name == obj
        else:
            return False
    
    def __repr__(self):
        return f"Sync_item({self.name}, {self.excl_dir})"
    
    def __lt__(self, obj):
        return self.name < obj.name
    

class Syncer:
    """Input: src_dict and tar_dict which are dictionaries containing all
    non excluded dirs (as keys) with files as values in set corresponding to parent
    dirs.

    Intermediary variables:
        Created with set operations (intersection and subtraction) on dictionary
        keys and the sets in each directory:
        

    Properties: Created from input variables above upon execution of __init__:
        self.source {string} : abs path to source dir
        self.target {string} : abs path to target dir
        self.id {int} : int representing the pair_id of the folders to sync.
        self.excl_src_items {list} : Nested list [[]]
        self.excl_tar_items {list} : Nested list [[]]
        self.mutual_items {list} : Nested list [[]]
    
    These 3 properties have the same structure which is basically a nested list
    of sync items: [[Sync_item("dir1", action), Sync_item("file1_in_dir1", action), ...],
    [Sync_item("dir2", action), Sync_item("file2_in_dir2", action), ...]]    
    Note that each "inner-list" represents a directory where the directory itself
    comes first.
   
    Methods:

    """

    def __init__(self, pair_id, source, target, src_dict, tar_dict):

        self.sync_dict = {
            # Contains strings representing paths (rel to source/tar)
            "upd_lr": set(),
            "upd_rl": set(),
            "add_to_src": set(),
            "add_to_tar": set(),

            # src_deletes and tar_deletes contain path objects and are therefore lists
            "src_deletes": Del_item(source),
            "tar_deletes": Del_item(target),
        }

        # self.state_dict = {} # Created by read_saved_state()
        self.id = pair_id
        self.source = source
        self.target = target
        self.excl_src_items = []
        self.excl_tar_items = []
        self.mutual_items = []

        self.create_sync_lists(src_dict, tar_dict)
        self.read_saved_state()
        self.decide_sync_actions()
        
    def create_sync_lists(self, src_dict, tar_dict):
        def get_dir_list(dir, file_set, new_dir):
            dir_as_list = [Dir_class(dir, new_dir)]
            files_in_dir = []
            for file in file_set:
                files_in_dir.append(file)

            files_in_dir.sort()
            return (dir_as_list + files_in_dir)

        mutual_dirs = src_dict.keys() & tar_dict.keys()
        src_dirs = src_dict.keys() - mutual_dirs
        tar_dirs = tar_dict.keys() - mutual_dirs
        
        # Add src_dirs and corresponding files in scr_dict to self.excl_src_items
        for dir in src_dirs:
            dir_content = get_dir_list(dir, src_dict[dir], True)
            self.excl_src_items.append(dir_content)

        # Add tar_dirs and corresponding files in tar_dict to self.excl_tar_items
        for dir in tar_dirs:
            dir_content = get_dir_list(dir, tar_dict[dir], True)
            self.excl_tar_items.append(dir_content)
        
        # Add all dirs in mutual_dirs, including mutual files, to self.mutual_items.
        # If there are files in mutual dirs on only one side then
        # add dir with files to the corresponding side

        for dir in mutual_dirs:
            mutual_files = src_dict[dir] & tar_dict[dir]
            src_files = src_dict[dir] - mutual_files
            tar_files = tar_dict[dir] - mutual_files
            self.mutual_items.append(get_dir_list(dir, mutual_files, False))

            if src_files: # Files existing only on source side!
                self.excl_src_items.append(get_dir_list(dir, src_files, False))
            if tar_files: # Files existing only on source side!
                self.excl_tar_items.append(get_dir_list(dir, tar_files, False))
        
        return
    
    def read_saved_state(self):
        json_filepath = get_json_path(self.id)
        try:
            with json_filepath.open("r") as json_file:
                state_dict = json.load(json_file)
            self.state_dict = state_dict["items"]
        except Exception as error:
            LOGGER.critical("Couldn't read previous sync state")
            LOGGER.critical(error)
            print("\n")
            sys.exit(1)
        
        return True
    
    def decide_sync_actions(self):
        def decide_action_for_excl_items(items, add_set, del_obj):
            for dir_content in items:
                dir = dir_content[0]
                dir_rel_path = pathlib.Path(dir.name)
                if dir.excl_dir:
                    # Entire folder exists exclusively on one side
                    if str(dir_rel_path) in saved_dirs: # Previously existed on both sides
                        for item in dir_content[1:]:
                            path_obj = dir_rel_path / item
                            del_obj.add_file(path_obj)
                        del_obj.add_dir(dir_rel_path)
                    else: # Added since last sync
                        add_list = [ (str(dir_rel_path / file)) for file in dir_content[1:] ]
                        add_set.update(set(add_list))
                        add_set.add(str(dir_rel_path))
                else:
                    # Files exists exclusively but dir exists on both sides
                    saved_files = set(self.state_dict[str(dir_rel_path)])
                    for item in dir_content[1:]:
                        file_path = dir_rel_path / item
                        if item in saved_files: # Previously existed on both sides
                            del_obj.add_file(file_path)
                        else: # Added since last sync
                            add_set.add(str(file_path))
                            
        # Goes through mutual items see if they differ(modification time)
        for dir_content in self.mutual_items:
            dir_rel_path = dir_content[0].name
            for file in dir_content[1:]:
                file_rel_path = pathlib.Path(dir_rel_path) / file
                file_src = pathlib.Path(self.source) / file_rel_path
                file_tar = pathlib.Path(self.target) / file_rel_path
                src_modified = file_src.lstat().st_mtime
                tar_modified = file_tar.lstat().st_mtime
                if src_modified > tar_modified:
                    self.sync_dict["upd_lr"].add(str(file_rel_path))
                elif tar_modified > src_modified:
                    self.sync_dict["upd_rl"].add(str(file_rel_path))

        if self.excl_src_items or self.excl_tar_items:
            # OBS saved_dirs are accessed by outer scope from inner func decide_action...
            saved_dirs = set(self.state_dict.keys())
            decide_action_for_excl_items(self.excl_src_items, 
            self.sync_dict["add_to_tar"], self.sync_dict["src_deletes"])
            decide_action_for_excl_items(self.excl_tar_items,
            self.sync_dict["add_to_src"], self.sync_dict["tar_deletes"])

    def deletions_necessary(self):
        return (bool(self.sync_dict["delete_from_source"]) or 
                bool(self.sync_dict["delete_from_tar"]))

    def delete_files(self):
        del_obj1, del_obj2 = self.sync_dict["src_deletes"], self.sync_dict["tar_deletes"]
        
        # Corresponds to keys for lists in state_dict converted to sets
        converted_dict_items = []

        for del_obj in (del_obj1, del_obj2):

            if not del_obj.files:
                LOGGER.debug(f"No files to delete in {del_obj.root}")
                continue

            for item in del_obj.files:
                try:
                    rel_path = del_obj.files[item]
                    path = del_obj.root / rel_path
                    path.unlink()
                    print(f"Deleted file: {path}")
                except Exception as err:
                    LOGGER.error(f"Couldn't delete {item}")
                    LOGGER.error(err)
                else:
                    # Following lines are to alter state in state_dict
                    key = str(rel_path.parent)
                    try:
                        # I use discard here so that error is thrown if value is still list!
                        self.state_dict[key].discard(rel_path.name)
                        converted_dict_items.append(key)
                    except:
                        self.state_dict[key] = set(self.state_dict[key])
                        self.state_dict[key].discard(rel_path.name)
                        converted_dict_items.append(key)
                        
        for key in converted_dict_items:
            self.state_dict[key] = list(self.state_dict[key])
            
    def dryrun_delete_files(self):
        del_obj1, del_obj2 = self.sync_dict["src_deletes"], self.sync_dict["tar_deletes"]
        
        for del_obj in (del_obj1, del_obj2):
            
            if not del_obj.files:
                LOGGER.debug(f"No files to delete in {del_obj.root}")
                continue

            for item in del_obj.files:
                path = del_obj.root / del_obj.files[item]
                print(f"Deleting file (dryrun): {path}")
            
    def delete_dirs(self):
        del_obj1, del_obj2 = self.sync_dict["src_deletes"], self.sync_dict["tar_deletes"]
        
        for del_obj in (del_obj1, del_obj2):
            if not del_obj.dirs:
                LOGGER.debug(f"No dirs to delete in {del_obj.root}")
                continue

            dir_list = del_obj.get_dir_list()

            for item in dir_list:
                try:
                    path = del_obj.root / item
                    path.rmdir()
                    print(f"Deleted directory: {path}")
                except Exception as err:
                    LOGGER.error(f"Couldn't delete {str(item)}")
                    LOGGER.error(err)
                else:
                    print(str(item))
                    del self.state_dict[str(item)]
    
    def dryrun_delete_dirs(self):
        del_obj1, del_obj2 = self.sync_dict["src_deletes"], self.sync_dict["tar_deletes"]
        
        for del_obj in (del_obj1, del_obj2):
            if not del_obj.dirs:
                LOGGER.debug(f"No dirs to delete in {del_obj.root}")
                continue

            dir_list = del_obj.get_dir_list()

            for item in dir_list:
                path = del_obj.root / item
                print(f"Deleting directory (dryrun): {path}")
            
    def delete(self):
        self.delete_files()
        self.delete_dirs()
    
    def dryrun_delete(self):
        self.dryrun_delete_files()
        self.dryrun_delete_dirs()

    def sync_necessary(self):
        return (bool(self.sync_dict["upd_lr"]) or 
                bool(self.sync_dict["upd_rl"]) or
                bool(self.sync_dict["add_to_tar"]) or
                bool(self.sync_dict["add_to_src"]))
        pass

    def create_textfiles(self):
        # Private method to create textfiles necessary for rsync call.
        config_dir = SCRIPT_PATH / ".folder_sync_config"
        lr_items = self.sync_dict["upd_lr"] | self.sync_dict["add_to_tar"]
        rl_items = self.sync_dict["upd_rl"] | self.sync_dict["add_to_src"]
        timepoint = round(time())
        lr_filename = f"lr_sync_{timepoint}.tmp"
        rl_filename = f"rl_sync_{timepoint}.tmp"

        self.txtfile_lr_path = config_dir / lr_filename
        with self.txtfile_lr_path.open('w') as file_lr:
            file_lr.writelines([line + '\n' for line in lr_items])

        self.txtfile_rl_path = config_dir / rl_filename
        with self.txtfile_rl_path.open('w') as file_rl:
            file_rl.writelines([line + '\n' for line in rl_items])
        
    def remove_textfiles(self):
        for item in (self.txtfile_lr_path, self.txtfile_rl_path):
            try:
                item.unlink()
            except Exception:
                # No action needed
                pass

    def sync(self):
        pass

    def save_file_state(self):
        pass


class Syncer_old:
    
    def __init__(self, src_root, tar_root) -> None:
        # lr = left-to-right
        # rl = right-to-left
        # src = source
        # tar = target
        
        self.src_root = src_root
        self.tar_root = tar_root
        self.lr_items = set()
        self.rl_items = set()
        self.duplicates = set()
        self.__txtfile_lr_path = ""
        self.__txtfile_rl_path = ""
        
    def __create_textfiles(self):
        # Private method to create textfiles necessary for rsync call.
        config_dir = SCRIPT_PATH / "./folder_sync_config"

        self.__txtfile_lr_path = config_dir / "lr_sync.tmp"
        with self.__txtfile_lr_path.open('w') as file_lr:
            file_lr.writelines([line + '\n' for line in self.lr_items])

        self.__txtfile_rl_path = config_dir / "rl_sync.tmp"
        with self.__txtfile_rl_path.open('w') as file_rl:
            file_rl.writelines([line + '\n' for line in self.rl_items])
        
    def __delete_textfiles(self):
        for item in [self.__txtfile_lr_path, self.__txtfile_rl_path]:
            try:
                os.unlink(item)
            except Exception:
                # No action needed
                pass
        
    def is_empty(self):
        return not self.lr_items and not self.rl_items
        
    def remove_intersection(self, verbose=False):
        # TODO
        intersection_set = self.lr_items.intersection(self.rl_items)
        if intersection_set:
            for item in intersection_set:
                self.lr_items.remove(item)
                self.rl_items.remove(item)
                self.duplicates.add(item)
        if verbose and intersection_set:    
            print(f"Intersection of sync sets {intersection_set}")

    def __run_rsync(self, rsync_arglist, print_output):
        """Used by sync method to call rsync with rsync_arglist. Will always use
        --from-file and --itemize-changes.

        Args:
            rsync_arglist {list}: list of args for rsync call
            print_output {boolean}: Wether to print any output or not

        Returns:
            [type]: [description]
        """
        obj_return = subprocess.run(rsync_arglist, text=True, capture_output=True)

        if obj_return.stdout:
            if print_output:
                print(format_rsync_output(obj_return.stdout), end="")
        else:
            if not obj_return.stderr:
                already_synced = 50
                return already_synced

        if obj_return.stderr:
            # TODO maybe write to logfile if print_output=False
            print(obj_return.stderr)

        if not obj_return.returncode == 0:
            # TODO maybe write to logfile if print_output=False
            print("Something went wrong in rsync call!")

        return obj_return.returncode

    def sync(self, delete=False, dryrun=False, print_output=True):
        """Summary: Sync files in lr_items and rl_items using rsync as subprocess.
        Requires internal variables

        Args:
            delete {bool}: Wether to delete files in target that doesnt exist in source.
            dryrun {bool}: If true run rsync ones with --dry-run flag. If true ignores user_interaction=True.
            prin_output {bool}: If true prints output.
        
        Returns:
            Most often propagates returncode from rsync call itself.
            Below are implementations specific return codes:
            already_synced = 50
            textfiles_not_set = 52
            from_file_without_valid_filepath = 51
        """
        
        self.__create_textfiles()

        # ERROR CHECKING START
        if not self.__txtfile_lr_path and self.__txtfile_rl_path:
            textfiles_not_set = 52
            return textfiles_not_set
        
        if not os.path.isfile(self.__txtfile_lr_path) and not os.path.isfile(self.__txtfile_rl_path):
            from_file_without_valid_filepath = 51
            return from_file_without_valid_filepath
        # ERROR CHECKING FINISHED
            
        # ARGUMENT BUILDING START
        arglist = ["rsync", "-a", "--itemize-changes"]
        if delete:
            arglist.append("--delete")
        if dryrun:
            arglist.append("--dry-run")

        if self.__txtfile_lr_path:
            if not os.path.isfile(self.__txtfile_lr_path):
                from_file_without_valid_filepath = 51
                return from_file_without_valid_filepath
            arglist_lr = arglist[:]
            fromfile_lr_arg = "--files-from=" + self.__txtfile_lr_path
            arglist_lr.append(fromfile_lr_arg)
            arglist_lr.append(self.src_root)
            arglist_lr.append(self.tar_root)

        if self.__txtfile_rl_path:
            if not os.path.isfile(self.__txtfile_rl_path):
                from_file_without_valid_filepath = 51
                return from_file_without_valid_filepath
            arglist_rl = arglist[:]
            fromfile_rl_arg = "--files-from=" + self.__txtfile_rl_path
            arglist_rl.append(fromfile_rl_arg)
            arglist_rl.append(self.tar_root)
            arglist_rl.append(self.src_root)

        return_lr = self.__run_rsync(arglist_lr, print_output)
        return_rl = self.__run_rsync(arglist_rl, print_output)
        if print_output and return_lr == 50 and return_rl == 50:
            print("\nFOLDERS ARE ALREADY COMPLETELY SYNCED!")
        self.__delete_textfiles()
        return return_lr, return_rl
    

class Deleter:
    
    def __init__(self, root_dir) -> None:
        self.files = set()
        self.dirs = set()
        self.files_in_deleted_dirs = set()
        self.root_dir = root_dir
        
    def get_all_files(self):
        return self.files.union(self.files_in_deleted_dirs)

    def is_empty(self):
        return not self.files and not self.dirs and not self.files_in_deleted_dirs
    
    def delete_items(self):
        for item in self.files:
            path = os.path.join(self.root_dir, item)
            print(f"DELETING FILE: {path}")
            os.unlink(path)
        
        for item in self.dirs:
            path = os.path.join(self.root_dir, item)
            print(f"DELETING DIRECTORY: {path}")
            rmtree(path)
            
    def dryrun_delete_items(self):
        [print(f"DELETING FILE (dry run): {item}") for item in self.files]
        [print(f"DELETING DIRECTORY (dry run): {item}") for item in self.dirs]
