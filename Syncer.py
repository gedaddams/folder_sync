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
