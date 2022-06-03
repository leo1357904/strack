"use strict";

var asm = {}
var c_code = []
var curr_instruction_key = "[1]"
var ip = ""
var prev_func = ""
var prev_ip = ""
var prev_line = ""
var prev_stack = new Object()
var init = true

function initStackTrace() {
    if (code_id < 0) {
        return
    }
    // asm = asm_state.replaceAll('\', '\\')
    // console.log(asm_state)
    // asm = asm_state.replaceAll('&quot;', '\\"')
    asm = asm_state.replaceAll('&quot;', '"')
    // asm = asm.replaceAll('&#x27;', '"')
    asm = asm.replaceAll('	', ' ')
    asm = asm.replaceAll('&lt;', '<')
    asm = asm.replaceAll('&gt;', '>')
    // console.log("asm with replaced characters")
    // console.log(asm)
    asm = JSON.parse(asm)

    c_code = code_text.replaceAll('&quot;', '"')
    c_code = c_code.replaceAll('&#x27;', '"')
    c_code = c_code.replaceAll('	', ' ')
    c_code= c_code.split('\n')

    updateIP()
    updateHTML()
}

function updateHTML() {
    updateCodeText()
    updateAssemblyCode()
    updateRegisters()
    updateStack()
    updateFlags()
    init = false
}

function updateCodeText() {
    let current_line = asm['instrucs'][curr_instruction_key]['cline']
    if (init) {
        $("#id_code_table").empty()
        let header_line = '<tr>' +
                                '<td>Line #</td>' + 
                                '<td>Line Content</code></td>' +
                            '</tr>'
        $("#id_code_table").append(header_line)
        for (var i = 0; i < c_code.length; i++) {
            let line = ''
            let index = i+1
            if (index == current_line) {
                prev_line = current_line
                line = '<tr id=code_row' + index +' class=highlight_code>' +
                            '<td>' + index + '</td>' + 
                            '<td><code>' + c_code[i].padEnd(80, ' ') + '</code></td>' +
                        '</tr>'
            } else {
                line = '<tr id=code_row' + index + '>'+
                            '<td>' + index + '</td>'+
                            '<td><code>' + c_code[i].padEnd(80, ' ') + '</code></td>'+
                        '</tr>'
            }
            $("#id_code_table").append(line)
        }
    } else {
        if (current_line != prev_line) {
            $('#code_row' + prev_line).removeClass('highlight_code')
            $('#code_row' + current_line).addClass('highlight_code')
            prev_line = current_line
        }
    }
}

function updateAssemblyCode() {
    let func = asm['instrucs'][curr_instruction_key]['func']
    let instructions = asm['disas'][func]['instrucs']
    let max_args = getMaxArgs(instructions)
    if (init | func != prev_func) {
        $("#id_assembly_instructions").empty()
        addHeader(func)
        addInstructions(instructions, max_args)
        prev_func = func
    } else {
        updateHighlightInstruction()
    }
}

function getMaxArgs(instructions) {
    let max_args = 0
    for (var i = 0; i < instructions.length; i++) {
        let args = instructions[i]["args"]
        if (args.length > max_args) {
            max_args = args.length
        }
    }
    return max_args
}

function addHeader(function_name) {
    // let addr = value["address"]
    $("#id_assembly_instructions").prepend(
        '<h2>Assembly Instructions</h2>' +
        '<table id=id_asm_table class="interp_table"></table>'
    )
    $("#id_asm_table").append(
        '<tr class=highlight_func>' +
            '<td colspan="100%" id=function_name><code>' + function_name +'</code></th>' +
        '</tr>'
    )
}

function addInstructions(instructions, max_args) {
    // let instructions = value["instructions"]
    for (var i = 0; i < instructions.length; i++) {
        let instruc = instructions[i]
        if (ip == instruc["addr"]) {
            let args = formatArgs(instruc["args"], max_args)
            $("#id_asm_table").append(
                '<tr class="highlight_asm" id='+ instruc["addr"] +'>' +
                    '<td><code>' + instruc["addr"] +'</code></td>' +
                    '<td><code>' + instruc["offset"] +'</code></td>' +
                    args +
                '</tr>'
            )
        } else {
            let args = formatArgs(instruc["args"], max_args)
            $("#id_asm_table").append(
                '<tr id='+ instruc["addr"] +'>' +
                    '<td class="grey"><code>' + instruc["addr"] +'</code></td>' +
                    '<td><code>' + instruc["offset"] +'</code></td>' +
                    args +
                '</tr>'
            )
        }
    }
}

function updateHighlightInstruction() {
    $('#' + prev_ip).removeClass('highlight_asm')
    $('#' + prev_ip).addClass('grey')
    $('#' + ip).removeClass('grey')
    $('#' + ip).addClass('highlight_asm')
}

function formatArgs(args, max_args) {
    let result = ""
    if (args == undefined) {
        return result
    }
    for (var i = 0; i < max_args; i++) {
        let new_arg = ''
        if (i < args.length) {
            new_arg = '<td><code>' + args[i] +'</code></td>'
        } else {
            new_arg = '<td></td>'
        }
        result += new_arg
    }
    return result
}

function updateStack() {
    $("#id_stack_table").empty()
    $("#id_stack_table").append(
        '<tr>' +
            '<td class=>Address</td>' +
            '<td><code>+7</code></td>' +
            '<td><code>+6</code></td>' +
            '<td><code>+5</code></td>' +
            '<td><code>+4</code></td>' +
            '<td><code>+3</code></td>' +
            '<td><code>+2</code></td>' +
            '<td><code>+1</code></td>' +
            '<td><code>+0</code></td>' +
        '</tr>'
    )
    let stack_key = asm['instrucs'][curr_instruction_key]['stack'].toString()
    let stack = asm['stacks'][stack_key]
    let order = Object.keys(stack).sort().reverse()
    for (var i = 0; i < order.length; i++) {
        let values = stack[order[i]]
        let hex_addr = '0x' + parseInt(order[i]).toString(16)
        let hex_values = getHexValues(values)
        // if ($('#' + hex_addr).text() == "") {
        $("#id_stack_table").append(
            '<tr id=' + hex_addr + '>' +
                '<td class="grey">'+ hex_addr + '</td>' +
                '<td id='+ hex_addr +'_0 class=highlight><code>'+ hex_values[0] + '</code></td>' +
                '<td id='+ hex_addr +'_1 class=highlight><code>'+ hex_values[1] + '</code></td>' +
                '<td id='+ hex_addr +'_2 class=highlight><code>'+ hex_values[2] + '</code></td>' +
                '<td id='+ hex_addr +'_3 class=highlight><code>'+ hex_values[3] + '</code></td>' +
                '<td id='+ hex_addr +'_4 class=highlight><code>'+ hex_values[4] + '</code></td>' +
                '<td id='+ hex_addr +'_5 class=highlight><code>'+ hex_values[5] + '</code></td>' +
                '<td id='+ hex_addr +'_6 class=highlight><code>'+ hex_values[6] + '</code></td>' +
                '<td id='+ hex_addr +'_7 class=highlight><code>'+ hex_values[7] + '</code></td>' +
            '</tr>'
        )
        if (prev_stack[order[i]] != undefined)  {
            let old_hex_values = getHexValues(prev_stack[order[i]])
            for (var j = 0; j < old_hex_values.length; j++) {
                if ($('#' + hex_addr + '_' + j).text() == old_hex_values[j]) {
                    $('#' + hex_addr + '_' + j).removeClass('highlight')
                }
            }
        }
    }
    prev_stack = stack
}

function getHexValues(values) {
    let hex_values = []
    for (var j = 0; j < values.length; j++) {
        let hex_value = parseInt(values[j]).toString(16)
        if (hex_value.length < 2) {
            hex_value = "0" + hex_value
        }
        hex_values.push(hex_value)
    }
    return hex_values
}

function updateRegisters() {
    if (init) {
        $("#id_regs_table").empty()
        $("#id_regs_table").append(
            '<tr>' +
                '<td class=>Register</td>' +
                '<td>8-byte</td>' +
                '<td>4-byte</td>' +
                '<td>2-byte</td>' +
                '<td>1-byte</td>' +
            '</tr>'
        )
    }

    // let regs_8 = ["rax", "rbx", "rcx", "rdx", "rdi", "rsi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rip", "rflags", "cs", "fs", "gs"]
    let regs_8 = ["rax", "rbx", "rcx", "rdx", "rdi", "rsi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rip"]
    // let regs_4 = ["eax", "ebx", "ecx", "edx", "edi", "esi", "ebp", "esp", "r8d", "r9d", "r10d", "r11d", "r12d", "r13d", "r14d", "r15d"]
    // let regs_2 = ["ax", "bx", "cx", "dx", "di", "si", "bp", "sp", "r8w", "r9w", "r10w", "r11w", "r12w", "r13w", "r14w", "r15w"]
    // let regs_1 = ["ah", "bh", "ch", "dh", "al", "bl", "cl", "dl", "dil", "sil", "bpl", "spl", "r8l", "r9l", "r10l", "r11l", "r12l", "r13l", "r14l", "r15l"]
    let reg_keys = asm['instrucs'][curr_instruction_key]['regs'].slice(0,17)
    for (var i = 0; i < reg_keys.length; i++) {
        let reg_key = reg_keys[i].toString()
        let reg_name = regs_8[i]

        let reg_values = []
        reg_values.push(asm['regs'][reg_key].toString(16))
        reg_values.push(((asm['regs'][reg_key] & 0xffffffff) >>>0).toString(16))
        reg_values.push(((asm['regs'][reg_key] & 0xffff) >>>0).toString(16))
        reg_values.push(((asm['regs'][reg_key] & 0xff) >>>0).toString(16))
        let rows = []
        rows.push('<td id='+ reg_name + '0 class=highlight><code>' + reg_values[0] + '</code></td>')
        rows.push('<td id='+ reg_name + '1 class=highlight><code>' + reg_values[1] + '</code></td>')
        rows.push('<td id='+ reg_name + '2 class=highlight><code>' + reg_values[2] + '</code></td>')
        rows.push('<td id='+ reg_name + '3 class=highlight><code>' + reg_values[3] + '</code></td>')
        if (init) {
            $("#id_regs_table").append(
                '<tr>' +
                    '<td class="grey">' + reg_name + '</td>' +
                    '<td class=highlight id='+ reg_name + '0><code>' + reg_values[0] + '</code></td>' +
                    '<td class=highlight id='+ reg_name + '1><code>' + reg_values[1] + '</code></td>' +
                    '<td class=highlight id='+ reg_name + '2><code>' + reg_values[2] + '</code></td>' +
                    '<td class=highlight id='+ reg_name + '3><code>' + reg_values[3] + '</code></td>' +
                '</tr>'
            )
        } else {
            for (var j = 0; j < 4; j++) {
                let old_value = $('#'+ reg_name + j).text()
                if (reg_values[j] == old_value) {
                    $('#'+ reg_name + j).removeClass('highlight')
                } else {
                    $('#'+ reg_name + j).addClass('highlight')
                    $('#'+ reg_name + j).text(reg_values[j])
                }
            }
        }
    }
}

function updateFlags() {
    let flags = ["CF", "PF", "AF", "ZF", "SF", "TF", "IF", "DF", "OF"]
    let flag_key = asm['instrucs'][curr_instruction_key]['regs'][17].toString()
    let flag_value = asm['regs'][flag_key]
    let flag_values = []
    flag_values.push(flag_value & 0x1)
    flag_values.push((flag_value & 0x4) >>> 2)
    flag_values.push((flag_value & 0x10) >>> 4)
    flag_values.push((flag_value & 0x40) >>> 6)
    flag_values.push((flag_value & 0x80) >>> 7)
    flag_values.push((flag_value & 0x100) >>> 8)
    flag_values.push((flag_value & 0x200) >>> 9)
    flag_values.push((flag_value & 0x400) >>> 10)
    flag_values.push((flag_value & 0x800) >>> 11)
    if (init) {
        $("#id_flags_table").empty()
        $("#id_flags_table").append(
            '<tr>' +
                '<td><code>CF</code></td>' +'<td><code>PF</code></td>' +
                '<td><code>AF</code></td>' +'<td><code>ZF</code></td>' +
                '<td><code>SF</code></td>' +'<td><code>TF</code></td>' +
                '<td><code>IF</code></td>' +'<td><code>DF</code></td>' +
                '<td><code>OF</code></td>' +
            '</tr>'
        )
        $("#id_flags_table").append(
            '<tr>' +
                '<td id=CF class=highlight><code>'+ flag_values[0] + '</code></td>' +
                '<td id=PF class=highlight><code>'+ flag_values[1] + '</code></td>' +
                '<td id=AF class=highlight><code>'+ flag_values[2] + '</code></td>' +
                '<td id=ZF class=highlight><code>'+ flag_values[3] + '</code></td>' +
                '<td id=SF class=highlight><code>'+ flag_values[4] + '</code></td>' +
                '<td id=TF class=highlight><code>'+ flag_values[5] + '</code></td>' +
                '<td id=IF class=highlight><code>'+ flag_values[6] + '</code></td>' +
                '<td id=DF class=highlight><code>'+ flag_values[7] + '</code></td>' +
                '<td id=OF class=highlight><code>'+ flag_values[8] + '</code></td>' +
            '</tr>'
        )
    } else {
        for (var i = 0; i < flags.length; i++) {
            let old_value = $('#'+ flags[i]).text()
            if (flag_values[i] == old_value) {
                $('#'+ flags[i]).removeClass('highlight')
            } else {
                $('#'+ flags[i]).addClass('highlight')
                $('#'+ flags[i]).text(flag_values[i])
            }
        }
    }
}
/*
asm = {
    "disas": {
        "main": {
            "header": "main",
            "instrucs": [
                {"addr": "0x1035d0ef0", "offset": "<+0>:", "args": ["pushq", "%rbp"]},
            ]
        }
    },
    "regs": {
        "1": 4462284816
    },
    "stacks": {
        "1": {
            "140701997411296": [0, 0, 0, 1, 3, 93, 208, 96],
            "140701997411304": [0, 0, 0, 1, 9, 250, 83, 160],
            "140701997411312": [0, 0, 0, 1, 3, 93, 14, 240],
            "140701997411320": [0, 0, 0, 1, 9, 249, 16, 16],
            "140701997411328": [0, 0, 127, 247, 188, 147, 44, 32],
            "140701997411336": [0, 0, 0, 1, 9, 242, 247, 51],
            "140701997411344": [0, 0, 0, 0, 0, 0, 0, 21],
            "140701997411352": [0, 0, 0, 1, 3, 93, 208, 96],
            "140701997411360": [0, 0, 127, 247, 188, 147, 45, 48],
            "140701997411368": [0, 0, 0, 1, 9, 242, 164, 254]
        }
    },
    "instrucs": {
        "[1]": {
            "func": "main",
            "cline": 1,
            "regs": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 1, 15, 12, 16, 11, 11],
            "stack": 1
        }
    }
}
*/

function executeStepIn() {
    let instruc_key = getKeyForStepIn()
    if (instruction_exists(instruc_key)) {
        curr_instruction_key = instruc_key
        updateIP()
        updateHTML()
        return
    }
    executeStep()
}

function executeStep() {
    let instruc_key = getKeyForStep()
    if (instruction_exists(instruc_key)) {
        curr_instruction_key = instruc_key
        updateIP()
        updateHTML()
        return
    }
    executeStepOut()
}

function executeStepOut() {
    let instruc_key = getKeyForStepOut()
    if (instruction_exists(instruc_key)) {
        curr_instruction_key = instruc_key
        updateIP()
        updateHTML()
        return
    }
    // execution finished, go back to start
    updateGlobalsForStart()
    updateIP()
    updateHTML()
}

function executeStepBack() {
    let instruc_key = getKeyForStepBack()
    if (instruction_exists(instruc_key)) {
        curr_instruction_key = instruc_key
        updateIP()
        updateHTML()
        return
    }
    instruc_key = getKeyForStepBackOut()
    if (instruction_exists(instruc_key)) {
        curr_instruction_key = instruc_key
        updateIP()
        updateHTML()
        return
    }
    updateGlobalsForStart()
    updateIP()
    updateHTML()
}

function executeRestart() {
    updateGlobalsForStart()
    updateIP()
    updateHTML()
}

function getKeyForStep() {
    let curr_instruc = get_instruction_array()
    let next_instruc = curr_instruc
    next_instruc[next_instruc.length - 1] += 1
    return get_instruction_key(next_instruc)
}

function getKeyForStepOut() {
    let curr_instruc = get_instruction_array()
    let next_instruc = curr_instruc
    next_instruc.pop()
    next_instruc[next_instruc.length - 1] += 1
    return get_instruction_key(next_instruc)
}

function getKeyForStepIn() {
    let curr_instruc = get_instruction_array()
    let next_instruc = curr_instruc
    next_instruc.push(1)
    return get_instruction_key(next_instruc)
}

function getKeyForStepBack() {
    let curr_instruc = get_instruction_array()
    let next_instruc = curr_instruc
    next_instruc[next_instruc.length - 1] -= 1
    return get_instruction_key(next_instruc)
}

function getKeyForStepBackOut() {
    let curr_instruc = get_instruction_array()
    let next_instruc = curr_instruc
    next_instruc.pop()
    return get_instruction_key(next_instruc)
}

function updateGlobalsForStart() {
    curr_instruction_key = "[1]"
    prev_stack = new Object()
    init = true
    updateIP()
}

function updateIP() {
    prev_ip = ip
    let rip_key = asm['instrucs'][curr_instruction_key]['regs'][16].toString()
    ip = '0x' + asm['regs'][rip_key].toString(16)
}

function get_instruction_array() {
    let instruc_key = curr_instruction_key
    let instruc_arr = instruc_key.replace("[", "").replace("]", "").replace(" ", "").split(",").map(Number)
    return instruc_arr
}

function get_instruction_key(instruc_arr) {
    let key_string = instruc_arr.toString().replace(',', ', ')
    return '[' + key_string + ']'
}

function instruction_exists(key) {
    return (asm["instrucs"][key] != undefined)
}
