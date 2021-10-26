class Sync_item:
    """
    Summary:
        Each instance of a Sync_item represents a file or a dir.

    Properties:
        self.name {string} = Name of file or dir
        self.action {int} = Corresponds to desired sync action in __ACTION_DICT

    Methods:
        Mostly self explanatory. 
        __lt__ is included to add sort capability when instance is in list.
    """
    __ACTION_DICT = {
    0: "IGNORE",
    1: "ADD",
    2: "DELETE",
    3: "UPDATE_LR",
    4: "UPDATE_RL",
    5: "AS_PARENT_DIR"}

    __slots__ = ["name", "action"] 

    def __init__(self, name, action):
        self.name = name
        assert (isinstance(action, int) and action >= 0 and action <= 5), "Action must be an integer between 0-4"
        self.action = action
    
    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Sync_item):
            return self.name == obj.name
        elif isinstance(obj, str):
            return self.name == obj
        else:
            return False
    
    def __repr__(self):
        action = self.__ACTION_DICT[self.action]
        return f"Sync_item({self.name}, {action})"
    
    def __lt__(self, obj):
        if not self.action == obj.action:
            return self.action < obj.action
        return self.name < obj.name
    

class Syncer:
    """Input: src_dict and tar_dict which are dictionaries containing all
    non excluded dirs (as keys) with files as values in set corresponding to parent
    dirs.

    Properties: Created from input variables above upon execution of __init__:
        self.src_items {list} : Nested list [[]]
        self.tar_items {list} : Nested list [[]]
        self.mutual_items {list} : Nested list [[]]
    
    These 3 properties have the same structure which is basically a nested list
    of sync items: [[Sync_item("dir1", action), Sync_item("file1_in_dir1", action), ...],
    [Sync_item("dir2", action), Sync_item("file2_in_dir2", action), ...]]    
    Note that each "inner-list" represents a directory where the directory itself
    comes first.
   
    Methods:

    """

    def __init__(self, src_dict, tar_dict):
        pass