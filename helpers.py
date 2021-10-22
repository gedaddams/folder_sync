"""This module contains classes and function format_rsync_output"""
import os
import subprocess
import glob
from shutil import rmtree


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

    def __init__(self, top_dir, exclude_list, exclude_patterns):
        # TODO maybe reade excludes from file instead of list.
        # TODO init function needs to add files from list relative to both source
        # and target. Maybe run twice. Both source and target as parameter?
        self.top_dir = top_dir
        self.dirs = set()
        self.temp_dirs = set()
        self.patterns = {}
        self.excl_dict = {}
        self.temp_dict = {}
        # __files is only  used temporarily. excl_dict and dirs is used after setup.
        self.__files = set()

        for item in exclude_list:
            self.__add_item(item)
        
        for pattern in exclude_patterns:
            self.__add_pattern(pattern)
            
            # TODO do not expand here. Add to self.patterns instead and try expanding in each dir.
            for path in glob.iglob(item):
                if os.path.isdir(path):
                    if os.path.islink(path):
                        self.__files.add(path)
                        continue
                    self.dirs.add(path)
                    continue
                self.__files.add(path)
        
        self.__dirs_to_relpath()
        self.__convert__files_to_excl_dict_items()

    def __add_pattern(self, pattern):
        """Adds pattern either for a directory (and all subdirs) or for all dirs.
        Patterns are added to the patterns property. This is later used by the
        method expand_pattern.

        Args:
            pattern {string}: pattern representing a glob patterns.
        """
        dir_path, file_pattern = os.path.dirname(pattern), os.path.basename(pattern)
        if dir_path:
            abs_dir = os.path.join(self.top_dir, dir_path)
            if os.path.isdir(abs_dir):
                dir_path = os.path.relpath(abs_dir, self.top_dir)
                self.patterns[dir_path] = file_pattern
        else:
            self.patterns["all"] = file_pattern

    def expand_pattern(self, basedir):
        # TODO
        pass

    def __add_item(self, item):
        """
        Args: 
        item {string}: Possibly path to item.
        """

        item = os.path.join(self.top_dir, item)
        if os.path.isfile(item) or os.path.islink(item):
            self.__files.add(item)
        elif item.endswith(os.sep) and os.path.isdir(item):
            if os.path.islink(item[:-1]):
                self.__files.add(item[:-1])
            else:
                rel_dir_path = self.__get_dir_relpath(item[:-1])
                self.__add_all_exclude_dir_to_excl_dict(rel_dir_path)
        elif os.path.isdir(item):
            self.dirs.add(item)

    def __get_dir_relpath(self, dir_path):
        if os.path.isabs(dir_path):
            return os.path.relpath(dir_path, self.top_dir)
        return dir_path
    
    def __dirs_to_relpath(self):
        rel_dirs = set()
        for item in self.dirs:
            rel_dirs.add(self.__get_dir_relpath(item))
        self.dirs = rel_dirs

    def __add_all_exclude_dir_to_excl_dict(self, dir_path):
        self.excl_dict[dir_path] = "exclude-all"

    def __add_excl_dict_item_from_filepath(self, file_path):
        dir_path, file_name = os.path.dirname(file_path), os.path.basename(file_path)
        dir_path = self.__get_dir_relpath(dir_path)
        if not dir_path in self.excl_dict:
            self.excl_dict[dir_path] = set()
        self.excl_dict[dir_path].add(file_name)
        
    def __convert__files_to_excl_dict_items(self):
        for file_path in self.__files:
            self.__add_excl_dict_item_from_filepath(file_path)
        self.__files = set()
                
    def __repr__(self):
        return f"\nexcl-dirs: {self.dirs}\n\nexcl-files: {self.__files}\n\n excl_dict: {self.excl_dict}\n"
    
    def get_non_excl_file_set(self, base_dir, file_list):
        if not base_dir in self.excl_dict:
            return set(file_list)
        elif not self.excl_dict[base_dir]:
            return set(file_list)
        elif isinstance(self.excl_dict[base_dir], set):
            return set(file_list) - self.excl_dict[base_dir]
        else:
            return None
        

class Syncer:
    
    def __init__(self, src_root, tar_root) -> None:
        # lr = left-to-right rl = right-to-left
        # src = source, tar = target
        self.src_root = src_root
        self.tar_root = tar_root
        self.lr_items = set()
        self.rl_items = set()
        self.duplicates = set()
        self.__txtfile_lr_path = ""
        self.__txtfile_rl_path = ""
        
    def __create_textfiles(self):
        # Private method to create textfiles necessary for rsync call.
        script_dir = os.path.dirname(os.path.realpath(__file__))
        config_dir = os.path.join("./folder_sync_config", script_dir)

        self.__txtfile_lr_path = os.path.join(config_dir, "lr_sync.tmp")
        with open(self.__txtfile_lr_path, 'w') as file_lr:
            file_lr.writelines([line + '\n' for line in self.lr_items])

        self.__txtfile_rl_path = os.path.join(script_dir, "rl_sync.tmp")
        with open(self.__txtfile_rl_path, 'w') as file_rl:
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
