sql_createtablefolder_pairs = """
    CREATE TABLE folder_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    target TEXT NOT NULL
    );"""

sql_createindexfolder_pairs = """
    CREATE UNIQUE INDEX folder_pair_index ON folder_pairs (source, target)
    ;"""

sql_createtablefiles = """
    CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    folder_pair_id INTEGER NOT NULL,
    file TEXT NOT NULL,
    FOREIGN KEY (folder_pair_id)
        REFERENCES folder_pairs (id)
    );"""
    
    # Previously had this in the table above. Currently do not use that field.
    # time_modified INTEGER NOT NULL,
    
sql_createindexfiles = """
    CREATE UNIQUE INDEX file_index ON files (folder_pair_id, file)
    ;"""

sql_createtablefolders = """
    CREATE TABLE folders (
    id INTEGER PRIMARY KEY,
    folder_pair_id INTEGER NOT NULL,
    folder TEXT NOT NULL,
    FOREIGN KEY (folder_pair_id)
        REFERENCES folder_pairs (id)
    );"""

sql_createindexfolders = """
    CREATE UNIQUE INDEX folder_index ON folders (folder_pair_id, folder)
    ;"""

def create_db(cur):
    cur.execute(sql_createtablefolder_pairs)
    cur.execute(sql_createtablefiles)
    cur.execute(sql_createtablefolders)
    cur.execute(sql_createindexfolder_pairs)
    cur.execute(sql_createindexfiles)
    cur.execute(sql_createindexfolders)