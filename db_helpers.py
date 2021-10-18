import sqlite3
import os
import sys
import logging

logger = logging.getLogger(__name__)

file_path = os.path.realpath(__file__)
dir_path = os.path.dirname(file_path)
db_name = ".folder_sync.db"
db_filepath = os.path.join(dir_path, db_name)

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


def save_folder_state(cur, folder_pair_id, files, dirs):

    sql_delete_files = """DELETE FROM files 
    WHERE id = ?;"""
    sql_delete_folders= """DELETE FROM folders 
    WHERE id = ?;"""
    sql_delete_folder_pair = """DELETE FROM folder_pairs 
    WHERE id = ?;"""
    sql_insert_files = """INSERT INTO files (folder_pair_id, file) 
    VALUES (?, ?);"""
    sql_insert_folders = """INSERT INTO folders (folder_pair_id, folder) 
    VALUES (?, ?);"""
    
    # file_list and dir_list will be list of tuples where the first item in
    # each tuple will be the folder_pair id.
    file_list = []
    dir_list = []

#    try:
    for item in files:
        file_list.append((folder_pair_id, item))
        
    for item in dirs:
        dir_list.append((folder_pair_id, item))

    print(f"\n{dir_list}")
    print(f"\n{file_list}\n")
    cur.execute(sql_delete_folders, (folder_pair_id,))
    cur.execute(sql_delete_files, (folder_pair_id,))
    cur.executemany(sql_insert_folders, dir_list)
    cur.executemany(sql_insert_files, file_list)
    return 0
#    except Exception:
#        try:
#            cur.execute(sql_delete_folder_pair, (folder_pair_id,))
#            cur.execute(sql_delete_folders)
#            cur.execute(sql_delete_files)
#            return 1
#        except Exception:
#            logger.critical("Critical error while saving folder state. Use extreme cautions syncing this folder pair next time. Do dry run first!")
#            return 2
    

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
    
    source, target = adjust_dirname(source), adjust_dirname(target)

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