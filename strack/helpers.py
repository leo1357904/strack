import re
import subprocess as sp
import time
import lldb
import os
from math import ceil
import json

class FileStorageHandler(object):
    def __init__(self, file_obj, file_name):
        self.file = file_obj
        self.time = str(ceil(time.time() * 1000))
        self.file_name = file_name
        self.code_file_path = self.get_local_file_path()
        self.exe_file_path = self.get_local_executable_path()
        self.state_file_path = self.get_local_state_path()
    
    def get_local_file_path(self):
        prefix = 'strack/static/file_storage/'
        suffix = '.c'
        return prefix + self.file_name + '_' + self.time + suffix
    
    def get_local_executable_path(self):
        prefix = 'strack/static/file_storage/'
        suffix = '.exe'
        return prefix + self.file_name + '_' + self.time + suffix
    
    def get_local_state_path(self):
        prefix = 'strack/static/file_storage/'
        suffix = '.json'
        return prefix + self.file_name + '_' + self.time + suffix
    
    def save_file(self):
        new_file = open(self.code_file_path, 'wb+')
        for chunk in self.file.chunks():
            new_file.write(chunk)
        new_file.close()
        return self.code_file_path
            
    def compile(self):
        error_file_name = self.exe_file_path.replace('.exe', '.err')
        compile_error_file = open(error_file_name, 'w+')
        sp.run(['gcc', '-gdwarf-2', '-o', self.exe_file_path, self.code_file_path], stdout=compile_error_file, stderr=compile_error_file)
        compile_error_file.close()
        return self.exe_file_path
    
    def save_state_to_file(self, state):
        file_obj = open(self.state_file_path, 'wb')
        json_state = json.dumps(state).encode('utf-8')
        file_obj.write(json_state)
        file_obj.close()
        return self.state_file_path


class FrameOrdering(object):
    def __init__(self):
        self.counter = [0]
        self.prev_ancestry: list = None
        self.curr_ancestry: list = None
        self.functions_seen = set()
        
    def order_instruction(self, frame: lldb.SBFrame):
        self.curr_ancestry = self.get_ancestry(frame)
        if self.is_execution_start() or self.is_step() or self.is_lateral_step():
            self.counter[-1] += 1
        elif self.is_step_into():
            self.counter.append(1)
        elif self.is_step_out():
            self.counter.pop()
            self.counter[-1] += 1
        else:
            return 'DONE'
        self.prev_ancestry = self.curr_ancestry
        curr_function = self.curr_ancestry[0][0]
        return curr_function
    
    def get_ancestry(self, frame: lldb.SBFrame):
        ancestor_list = []
        curr_frame: lldb.SBFrame = frame
        while(curr_frame):
            function_name = curr_frame.GetFunctionName()
            offset = self.get_frame_offset(curr_frame)
            ancestor_list.append((function_name, offset))
            curr_frame = curr_frame.parent
        return ancestor_list
    
    def get_frame_offset(self, frame: lldb.SBFrame):
        plus_index = str(frame).find('+')
        if (plus_index == -1):
            return 0
        offset = str(frame)[plus_index + 1:].strip()
        return int(offset)
    
    def is_execution_start(self):
        return self.prev_ancestry == None
    
    def is_step(self):
        curr_function = self.curr_ancestry[0][0]
        prev_function = self.prev_ancestry[0][0]
        return curr_function == prev_function
    
    def is_lateral_step(self):
        if len(self.curr_ancestry) == 1 or len(self.prev_ancestry) == 1:
            return False
        curr_parent = self.curr_ancestry[1][0]
        prev_parent = self.prev_ancestry[1][0]
        return curr_parent == prev_parent
        
    def is_step_into(self):
        if len(self.curr_ancestry) == 1:
            return False
        curr_parent = self.curr_ancestry[1][0]
        prev_function = self.prev_ancestry[0][0]
        return curr_parent == prev_function
    
    def is_step_out(self):
        if len(self.prev_ancestry) == 1:
            return False
        prev_parent = self.prev_ancestry[1][0]
        curr_function = self.curr_ancestry[0][0]
        return curr_function == prev_parent

    def get_counter(self):
        return self.counter
    
class RedundancyCheck(object):
    def __init__(self):
        self.functions_seen = set()
        self.stack_to_key_map = dict()
        self.reg_to_key_map = dict()
        self.stack_counter = 0
        self.reg_counter = 0
        
    def is_new_function(self, function):
        if function not in self.functions_seen:
            self.functions_seen.add(function)
            return True
        return False
    
    def is_new_stack(self, stack: dict):
        stack_immutable = str(stack)
        return stack_immutable not in self.stack_to_key_map
    
    def add_stack(self, stack: dict):
        self.stack_counter += 1
        stack_immutable = str(stack)
        self.stack_to_key_map[stack_immutable] = self.stack_counter
        return self.stack_counter
        
    def get_stack_counter(self, stack):
        stack_immutable = str(stack)
        if stack_immutable in self.stack_to_key_map:
            return self.stack_to_key_map[stack_immutable]
        return -1
    
    def is_new_reg(self, reg: int):
        return reg not in self.reg_to_key_map
    
    def add_reg(self, reg: int):
        self.reg_counter += 1
        self.reg_to_key_map[reg] = self.reg_counter
        return self.reg_counter
    
    def get_reg_counter(self, reg):
        if reg in self.reg_to_key_map:
            return self.reg_to_key_map[reg]
        return -1

class LLDB(object):
    def __init__(self, exe: str, timeout: int):
        self.exe_file_path = exe
        self.ordering = FrameOrdering()
        self.redundancy = RedundancyCheck()
        self.starting_rsp: str = None
        self.prev_c_line = 0
        self.asm_state = {'disas': {}, 'stacks': {}, 'regs': {}, 'instrucs': {}}
        self.timeout = timeout * 1000
            
    def run_lldb_process(self):
        start_time = time.time() * 1000
        debugger: lldb.SBDebugger = lldb.SBDebugger.Create()
        debugger.SetAsync(False)
        target: lldb.SBTarget = debugger.CreateTargetWithFileAndArch(self.exe_file_path, 'x86_64')
        target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
        process: lldb.SBProcess = target.LaunchSimple(None, None, os.getcwd())
        thread: lldb.SBThread = process.GetThreadAtIndex(0)
        while True:
            state = self.process_instruction(target, process, thread)
            curr_time = time.time() * 1000
            if (curr_time - start_time) > self.timeout:
                process.Kill()
                return {'timeout': True}
            if state == {}:
                process.Kill()
                return self.asm_state
            self.asm_state['instrucs'][str(self.ordering.get_counter())] = state
            thread.StepInstruction(False)
            
    def process_instruction(self, target: lldb.SBTarget, process: lldb.SBProcess, thread: lldb.SBThread):
        state_info = dict()
        state = process.GetState()
        if state != lldb.eStateStopped:
            print("state not stopped")
            print("exited?", state == lldb.eStateExited)
            return state_info
        frame: lldb.SBFrame = thread.GetFrameAtIndex(0)
        function = self.ordering.order_instruction(frame)
        if function == 'DONE':
            return state_info
        full_function_name = self.get_full_name(frame)
        if self.redundancy.is_new_function(full_function_name):
            self.asm_state['disas'][full_function_name] = self.disassemble_frame(frame)
        state_info['func'] = full_function_name
        state_info['cline'] = self.get_c_line(frame)
        
        registers = self.get_register_values(frame)
        state_info['regs'] = registers
        
        stack = self.get_stack(process, registers)
        stack_key = self.redundancy.get_stack_counter(stack)
        if self.redundancy.is_new_stack(stack):
            stack_key = self.redundancy.add_stack(stack)
            self.asm_state['stacks'][stack_key] = stack
        state_info['stack'] = stack_key
        return state_info
    
    def get_full_name(self, frame: lldb.SBFrame):
        disas: str = frame.Disassemble()
        header_end = disas.find('\n')
        return disas[:header_end].strip()
    
    def get_c_line(self, frame: lldb.SBFrame):
        format_chars_1 = '\x1b[33m'
        format_chars_2 = '\x1b[0m'
        line: str = str(frame)
        line = line.split(':')
        if len(line) > 2:
            if line[2].startswith(format_chars_1):
                    self.prev_c_line = int(line[2].replace(format_chars_1, '').replace(format_chars_2, ''))
        return self.prev_c_line
    
    def disassemble_frame(self, frame: lldb.SBFrame):
        result_disas = {'header': '', 'instrucs': []}
        disassembled_frame: str = frame.Disassemble()
        lines = disassembled_frame.split('\n')
        for i in range(len(lines)):
            line: str = lines[i].strip()
            if i == 0:
                result_disas['header'] = line
                continue
            instruc = self.get_instruction(line)
            if instruc != {}:
                result_disas['instrucs'].append(instruc)
            if ('retq' in line):
                break
        return result_disas
    
    def get_instruction(self, line: str):
        instruc = {}
        if ';' in line:
            comment = line[line.find(';') + 1:].strip().strip('"').strip('\n')
            instruc['comment'] = comment
            line = line[:line.find(';')]
        content_chunks = self.format_line(line, instruc)
        for i in range(len(content_chunks)):
            chunk = content_chunks[i]
            if i == 0:
                instruc['addr'] = chunk
            elif i == 1:
                instruc['offset'] = chunk
            elif i > 1:
                if 'args' not in instruc:
                    instruc['args'] = []
                instruc['args'].append(chunk)
        return instruc
    
    def format_line(self, line: str, instruc: dict):
        content_chunks = []
        chunks = line.split(' ')
        for i in range(len(chunks)):
            chunk = chunks[i]
            if chunk != '' and chunk != '->':
                content_chunks.append(chunk)
        return content_chunks
    
    def get_register_values(self, frame: lldb.SBFrame):
        registers = []
        reg_types: lldb.SBValueList = frame.GetRegisters()
        general_registers = reg_types[0]
        count = 0
        for reg in general_registers:
            if count > 20:
                break
            value: int = int(reg.GetValue(), 16)
            if self.redundancy.is_new_reg(value):
                reg_key = self.redundancy.add_reg(value)
                self.asm_state['regs'][reg_key] = value
            reg_key = self.redundancy.get_reg_counter(value)
            registers.append(reg_key)
            count += 1
        return registers
    
    def get_stack(self, process: lldb.SBProcess, registers: list):
        rbp_index = 6
        rsp_index = 7
        rbp_value: int = self.asm_state['regs'][registers[rbp_index]]
        rsp_value: int = self.asm_state['regs'][registers[rsp_index]]
        # if self.starting_rsp == None:
        #     self.starting_rsp = rsp_value
        # read_from: int = min(rsp_value, self.starting_rsp - 80)
        read_from: int = min(rsp_value, rbp_value)
        # offset = self.starting_rsp - read_from
        offset = abs(rsp_value - rbp_value) + 8
        error = lldb.SBError()
        bytes_read: str = process.ReadMemory(read_from, offset, error)
        return self.format_bytes_read(bytes_read, read_from)
    
    def format_bytes_read(self, bytes_read: str, read_from: int):
        stack_result = {}
        word_length = 8
        stack_bytes = bytearray(bytes_read)
        for word_start in range(0, len(stack_bytes), 8):
            curr_word = []
            curr_addr = read_from + word_start
            for word_offset in range(word_length):
                curr_byte: int = stack_bytes[word_start + word_offset]
                curr_word.insert(0, curr_byte)
            stack_result[curr_addr] = curr_word
        return stack_result

    def get_final_state(self):
        return self.asm_state
    
    
class LLDBSubprocess(object):
    def __init__(self, executable_path: str, timeout: int):
        self.exe_path = executable_path 
        self.timeout = timeout
        
    def start(self):
        args = 'python3 strack/lldb_subprocess.py ' + self.exe_path + ' ' + str(self.timeout)
        p1 = sp.Popen(args, shell=True)
        p1.wait()
        
        