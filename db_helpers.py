import sqlite3
import os
import sys
import logging

logger = logging.getLogger(__name__)

file_path = os.path.realpath(__file__)
dir_path = os.path.dirname(file_path)
db_name = ".folder_sync.db"
db_filepath = os.path.join(dir_path, db_name)


sql_createtablefolder_pairs = """
    CREATE TABLE folder_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    target TEXT NOT NULL
    );"""

sql_createindexfolder_pairs = """
    CREATE UNIQUE INDEX folder_index ON folder_pairs (source, target)
    ;"""

sql_createtablefiles = """
    CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    folder_pair_id INTEGER NOT NULL,
    file TEXT NOT NULL,
    time_modified INTEGER NOT NULL,
    FOREIGN KEY (folder_pair_id)
        REFERENCES folder_pairs (id)
    );"""
    
sql_createindexfiles = """
    CREATE UNIQUE INDEX file_index ON files (folder_pair_id, file)
    ;"""

def setup_db():
    if not os.path.isfile(db_filepath):
        con = sqlite3.connect(db_filepath, isolation_level=None)
        cur = con.cursor()
        cur.execute(sql_createtablefolder_pairs)
        cur.execute(sql_createindexfolder_pairs)
        cur.execute(sql_createtablefiles)
        cur.execute(sql_createindexfiles)
    else: 
        # Duplicate is necessarry since sqlite3.connect creates file if it doesnt exist
        con = sqlite3.connect(db_filepath, isolation_level=None)
        cur = con.cursor()
        
    return con, cur


def save_initial_folder_state(folder_pair_id):
    """ TODO create function. 
    This function will save folderstate after first folder pair sync
    Function should return 0 upon succesful completion otherwise value > 0"""
    pass


def save_folder_state():
    # TODO Function will save folder state after sync.
    pass


def adjust_dirname(dirname):
    """adjust dirname to always end with separator (in linux = /)"""
    return os.path.abspath(dirname) + os.path.sep


def folder_pair_exists(cur, source, target):
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