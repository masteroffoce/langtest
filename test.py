from llvmlite import ir, binding
import subprocess
import os
import json

strings_defined = {}

def add_puts(text: str, builder, module, fputs):
    if not text in strings_defined: #Damn, I feel smart
        arr = bytearray(text.encode("utf-8") + b"\0")
        str_ty = ir.ArrayType(ir.IntType(8), len(arr))
        gv = ir.GlobalVariable(module, str_ty, name="str_" + str(abs(hash(text)) % 10000))
        gv.global_constant = True
        gv.initializer = ir.Constant(str_ty, arr)
        str_ptr = builder.gep(gv, [ir.Constant(ir.IntType(64), 0),
                                  ir.Constant(ir.IntType(64), 0)])
        strings_defined[text] = str_ptr
    else: #String constant already defined
        str_ptr = strings_defined[text]

    stdout_gv = module.globals["stdout"]
    stdout_ptr = builder.load(stdout_gv)
    builder.call(fputs, [str_ptr, stdout_ptr])

def add_routine(name: str):
    func_type = ir.FunctionType(ir.VoidType(), [])
    func = ir.Function(module, func_type, name=name)
    block = func.append_basic_block(name="entry")
    builder = ir.IRBuilder(block)

    return func, builder


source_path = "source.json"
with open(source_path, "r") as file:
    program = json.load(file)
    print(program)


# --- Step 1: Build IR ---
module = ir.Module(name="printlang_module")

# main function
fnty = ir.FunctionType(ir.IntType(32), [])
main = ir.Function(module, fnty, name="main")
block = main.append_basic_block(name="entry")
builder = ir.IRBuilder(block)


#Define fputs
fputs_ty = ir.FunctionType(ir.IntType(32),
                           [ir.PointerType(ir.IntType(8)),
                            ir.PointerType(ir.IntType(8))])
fputs = ir.Function(module, fputs_ty, name="fputs")

#Define stdout
stdout_ty = ir.PointerType(ir.IntType(8))
stdout_gv = ir.GlobalVariable(module, stdout_ty, name="stdout")
stdout_gv.linkage = "external"


#Make test routine
test_routine, test_builder = add_routine("test")
add_puts("yoooooooooooo \n", test_builder, module, fputs)
test_builder.ret_void()

def fill_routine(routine_builder, actions_list):
    for action_dict in actions_list: #No person #I knew I wouldn't get it later! #Used to say program instead of actions_list in case that helps you get it.
        for action, value in action_dict.items():
            match action:
                case "print":
                    #add_print(value)
                    add_puts(value, routine_builder, module, fputs)
                case "call":
                    routine_builder.call(filled_routines[value][1], [])
                case _:
                    raise Exception(f"Unrecognised token: {action}")



'''
#Get routine with lowest index
routines = {}
for current_routine in program:
    try:
        index = current_routine["routine"]["index"]
        if index in routines:
            raise Exception("Two functions with the same index")
        routines[index] = current_routine
    except:
        print("Non-routine in highest level!")
print(f"ROUTINES:\n\n{routines}\n\n")

#Make dict of all routines
filled_routines = {}
for current_index, current_routine in routines.items():
    print("\n\n")
    body = current_routine["routine"]["body"]
    print(body)
    print("\n\n")
    this_routine, this_builder = add_routine(current_routine["routine"]["name"])
    fill_routine(this_builder, body)
    this_builder.ret_void()
    filled_routines[current_index] = this_routine
    '''

routines = {}
for current_routine in program:
    index = current_routine["routine"]["index"]
    if index in routines:
        raise Exception("Duplicate routine signature numbers")
    this_routine, this_builder = add_routine(current_routine["routine"]["name"])
    routines[index] = (current_routine, this_routine, this_builder)

filled_routines = {}
for index, routine_data in routines.items():
    print("\n\n")
    body = routine_data[0]["routine"]["body"]
    print(body)
    print("\n\n")
    fill_routine(routine_data[2], body )
    routine_data[2].ret_void()
    filled_routines[index] = routine_data
#'''
    


#Add start routine to main function, required by clang
#builder.call(compiled_routines[8], [])
builder.call(filled_routines[min(routines)][1], [])

builder.ret(ir.Constant(ir.IntType(32), 0))

print("=== Generated LLVM IR ===")
print(module)

# --- Step 2: Compile to object file ---
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

target = binding.Target.from_default_triple()
target_machine = target.create_target_machine()

llvm_mod = binding.parse_assembly(str(module))
llvm_mod.verify()

obj_path = "output.o"
exe_path = "testexec"

with open(obj_path, "wb") as f:
    f.write(target_machine.emit_object(llvm_mod))

# --- Step 3: Link to executable ---
#subprocess.check_call(["clang", obj_path, "-o", exe_path])
subprocess.check_call(["clang", obj_path, "-o", exe_path])

print(f"Executable written to {exe_path}")

