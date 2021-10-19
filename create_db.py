sql_createtablefolder_pairs = """
    CREATE TABLE folder_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    target TEXT NOT NULL
    );"""

sql_createindexfolder_pairs = """
    CREATE UNIQUE INDEX folder_pair_index ON folder_pairs (source, target)
    ;"""

def create_db(cur):
    cur.execute(sql_createtablefolder_pairs)
    cur.execute(sql_createindexfolder_pairs)