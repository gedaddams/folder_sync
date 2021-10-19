import sqlite3
import os
import sys
import logging
import json

"""
Module saves most of its data in json files in folder:
./folder_sync_config/folder_pair_states

Folder pairs and configuration data is saved in sqlite database file.
"""

logger = logging.getLogger(__name__)

file_path = os.path.realpath(__file__)
dir_path = os.path.dirname(file_path)
db_relpath = os.path.join(".folder_sync_config", "folder_sync.db")
db_filepath = os.path.join(dir_path, db_relpath)

def setup_db():
    if not os.path.isfile(db_filepath):
        from create_db import create_db
        con = sqlite3.connect(db_filepath, isolation_level=None) 
        cur = con.cursor()
        create_db(cur)
    else: 
        # Duplicate is necessarry since sqlite3.connect creates file if it doesnt exist
        con = sqlite3.connect(db_filepath, isolation_level=None)
        cur = con.cursor()
    return con, cur


def save_folder_state(folder_pair_id: int, files: list, dirs: list) -> None:

    json_file_name = "folder_pair_" + str(folder_pair_id) + ".json"
    json_file_path = os.path.join(dir_path, ".folder_sync_config", 
    "folder_pair_states", json_file_name)
    state_dict = {"id": folder_pair_id, "files": files, "dirs": dirs}

    try:
        with open(json_file_path, "w") as outfile:
            json.dump(state_dict, outfile)
            return 0
    except Exception as error:
        logger.warning(error)
        return 1
        

def adjust_dirname(dirname):
    """adjust dirname to always end with separator (in linux = /)"""
    return os.path.abspath(dirname) + os.path.sep


def get_folder_pair_id(cur, source, target):
    """Checks wether input folder pair already exists in database.
    
    Args:
        cur {object}: Object of active cursor
        source {string}: string of source dir.
        target {string}: string of target dir.

    Return:
        {integer}: id (column in folder_pairs) if match found. If no match returns 0. 
    """
    
    sql = """
    SELECT id, source, target 
    FROM folder_pairs 
    WHERE source = ? 
    AND target = ?;
    """

    cur.execute(sql, (source, target))
    folder_pairs = cur.fetchall()
    len_rows = len(folder_pairs)
    
    assert (len_rows < 2), (f"\nfolder_pair_exists returned to many folder pairs: {folder_pairs}\n")
    if len_rows == 1:
        id_folder_pair = folder_pairs[0][0]
        return id_folder_pair

    return 0


def add_folder_pair(cur, source, target):
    """
    Creates folder pair in db table folder_pairs. If not already there a
    trailing slash for dirpaths is added via adjust_dirname function. This is
    to avoid creating duplicate folder pairs in underlying database.
    
    Args:
        cur {object}: Cursor of db.
        source {string}: string of source dir.
        target {string}: string of target dir.

    Return: 
        {integer}: id of inserted row. 0 if fail.
    """
    
    if not (os.path.isdir(source) and os.path.isdir(target)):
        print(f"Source: {source}")
        print(f"Target: {target}")
        error_message = "Both source and target arguments to add_folder_pair need to be directories"
        raise Exception(error_message)
    
    sql_insertfolderpair = """INSERT INTO folder_pairs 
    (source, target) VALUES (?, ?);"""

    try:
        cur.execute(sql_insertfolderpair, (source, target))
        return cur.lastrowid
    except:
        print("Couldn't add folder pair")
        return 0 # Evaluates to false in boolean expression


def remove_folder_pair(con, cur, source, target):
    # TODO finish function
    pass