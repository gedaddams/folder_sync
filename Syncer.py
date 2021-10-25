class Sync_item:
    __ACTION_DICT = {
    0: "IGNORE",
    1: "ADD",
    2: "DELETE",
    3: "UPDATE_LR",
    4: "UPDATE_RL"}

    __slots__ = ["name", "__action"] 

    def __init__(self, name, action):
        self.name = name
        assert (isinstance(action, int) and action >= 0 and action <= 4), "Action must be an integer between 0-4"
        self.__action = action
    
    def __hash__(self) -> int:
        return hash(self.name)
    
    def __eq__(self, obj: object) -> bool:
        if isinstance(obj, Sync_item):
            return self.name == obj.name
        elif isinstance(obj, str):
            return self.name == obj
        else:
            return False
    
    def __repr__(self):
        return f"Sync_item({self.name}, {self.action})"
    
    def __lt__(self, obj):
        if not self.__action == obj.__action:
            return self.__action < obj.__action
        return self.name < obj.name
    
    @property
    def action(self):
        return self.__ACTION_DICT.get(self.__action, None)
    

class Syncer:
    """Input: src_dict and tar_dict which are dictionaries containing all
    non excluded dirs (as keys) with files as values in set corresponding to parent
    dirs.

    Intermediary variables (following properties or variables are only temporary):
    mutual_items: Dict of same format as input dicts containing dirs (keys) with
    file sets (values) corresponding to files and dirs found in both input dicts.
    source_items: Items found only in source, same format as mutual items.
    target_items: Items found only in target, same format as mutual items.

    Properties: Mostly created from the intermediary variables above:
    self.source
    self.target
    self.upd_src - items that are to be updated, direction target -> source
    self.add_src - items that are to be added, direction target -> source
    self.del_src - items that are to be deleted from source
    self.upd_tar - items that are to be updated, direction source -> target
    self.add_tar - items that are to be added, direction source -> target
    self.del_tar - items that are to be deleted from target
   
    Methods:

    """

    def __init__(self, src_dict, tar_dict):
        pass
