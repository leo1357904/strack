from helpers import LLDB
import sys
import json

def save_state_to_file(state_path: str, state: dict):
    file_obj = open(state_path, 'w')
    # json_state = json.dumps(state).encode('utf-8')
    # file_obj.write(json_state)
    json.dump(state, file_obj)
    file_obj.close()

def main(exe_path: str, timeout: int):
    lldb = LLDB(exe_path, timeout)
    state_info = lldb.run_lldb_process()
    if ('timeout' in state_info):
        state_path = exe_path.replace('.exe', '.to')
    else:
        state_path = exe_path.replace('.exe', '.json')
    save_state_to_file(state_path, state_info)

if __name__ == "__main__":
    print(sys.argv)
    main(sys.argv[1], int(sys.argv[2]))