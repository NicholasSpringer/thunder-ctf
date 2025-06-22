import warnings
import sys
import os
import string

def help(*args):
    print("""Available commands:
    python3 thunder.py create [level]
    python3 thunder.py destroy
    python3 thunder.py list_available_levels
    python3 thunder.py get_active_level
    python3 thunder.py activate_project [project-id]
    python3 thunder.py help

Developer commands:
    python3 thunder.py add_levels [level-path] [level-path]...
    python3 thunder.py generate_level_docs
    """)
    exit()


if __name__ == '__main__':
    warnings.filterwarnings("ignore", module="google.auth")
    if sys.version_info[0] == 2:
        print("Must be using Python 3")
        exit()

    ctf_path = None
    if sys.version_info[1] < 9:
        ctf_path = os.getcwd()+'/'+os.path.dirname(__file__)
    else: 
        ctf_path = os.path.dirname(__file__)
    
    os.chdir(ctf_path)
    
    # python3 thunder.py action [args]
    args = sys.argv[1:]
    if len(args) == 0:
        action = 'help'
    else:
        action = args[0]

    try:
        func = locals()[action]
        if not callable(func):
            raise KeyError
    except KeyError:
        func = help
    func(*args[1:])
