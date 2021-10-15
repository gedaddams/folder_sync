#!/usr/bin/env python3
import argparse
import os
import logging
import sqlite3
import sys
import sync_functions
import db_helpers

# TODO Make it so folder sync can be run with and without arguments.
# If run with arguments use get_arguments func as per below. Check if folder pair
# exist in db. Otherwise offer to add it. If folder sync is run without arguments
# user should be presented with a cli menu of which folder pairs currently exists

# TODO change debug level when not in development
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format="\nLogger %(name)s - %(levelname)s:\n%(message)s")
logger = logging.getLogger(__name__)

def main():
    try:    
        con, cur = db_helpers.setup_db()

        if len(sys.argv) > 1:
            # Getting, controlling and adjusting arguments!
            source, target, delete, dry_run, verbose = get_arguments()
            check_arguments(source, target)
            source = db_helpers.adjust_dirname(source)
            target = db_helpers.adjust_dirname(target)

            if db_helpers.folder_pair_exists(cur, source, target):
                sync_functions.sync(source, target, delete, dry_run, verbose)                    
            else:
                setup_new_folder_pair(cur, source, target)
        else:
            # TODO Add cli interface
            pass
    finally:
        con.close()


def setup_new_folder_pair(cur, source, target):
    # TODO function needs testing

    user_input = ""
    while not user_input in {"y", "yes", "n", "no"}:
        print(f"\nFOLDER PAIR DOESN'T EXIST.\nTo create it you will need to perform an initial rsync\n\nfrom source: {source}\nto target: {target}")
        print(f"\nrsync is NOT a two way sync so target will be a perfect copy of source when finished!")
        user_input = normalize_input(input(f"\nDo you want to continue? (y/yes, n/no)\n--> "))
    
    if user_input == "n" or user_input == "no":
        print("Exiting program...")
        sys.exit(3)
    
    print("\nPerforming rsync dryrun!\n")
    return_value = sync_functions.rsync(source, target, True, False, True, True)
    if not return_value == 0: # 0 = correct execution.
        if return_value == 49: # 49 = User aborted interactively!
            sys.exit(1)
        elif return_value == 50: # 50 = Folders already synced!
            # Do nothing. Allow program to continue exection below.
            pass
        else:
            print("\nSomething went wrong with rsync. Exiting program!")
            sys.exit(1)

    # If program hasn't exited due to error below code runs!
    cur.execute("BEGIN")
    id = db_helpers.add_folder_pair(cur, source, target)
    if not id:
        cur.execute("ROLLBACK")
        print("Failed to add folder pair. Exiting!")
        sys.exit(1)
    else:
        if db_helpers.save_initial_folder_state(id) == 0:
            cur.execute("COMMIT")
            print("Succesfully added folder pair for future syncing!")
        else:
            cur.execute("ROLLBACK")
            print("Couldn't save folder state!")


def normalize_input(user_input):
    norm_input = user_input.strip()
    return norm_input.lower()


def check_arguments(source, target):
    if source == target:
        print(f"Source cannot equal target!")
        sys.exit(2)
    if not (os.path.isdir(source) and os.path.isdir(target)):
        print(f"Both source and target needs to be directorys (folders)!")
        sys.exit(2)


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", dest="source_dir", help="source directory", required=True)
    parser.add_argument("-t", "--target", dest="target_dir", help="target directory", required=True)
    parser.add_argument("-d", "--delete", dest="delete", default="False", help="set to true to enable deletions", required=False)
    parser.add_argument("-n", "--dry-run", dest="dry_run", default="False", help="set to false to do dryrun", required=False)
    parser.add_argument("-v", "--verbose", dest="verbose", default="True", help="set to false to sync without output", required=False)
    options = parser.parse_args()
    source_dir = options.source_dir
    target_dir = options.target_dir
    deletions_enabled = True if (options.delete.lower() == "true") else False
    dry_run = False if (options.dry_run.lower() == "false") else True
    verbose = False if (options.verbose.lower() == "false") else True
    return source_dir, target_dir, deletions_enabled, dry_run, verbose


if __name__ == "__main__":
    main()