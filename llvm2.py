from llvmlite import ir, binding
import subprocess
import os

# --- Step 1: Build IR ---
module = ir.Module(name="printlang_module")

# declare printf
printf_ty = ir.FunctionType(ir.IntType(32), [ir.IntType(8).as_pointer()], var_arg=True)
printf = ir.Function(module, printf_ty, name="printf")

# format string "%s\n"
fmt_str = ir.GlobalVariable(module, ir.ArrayType(ir.IntType(8), 4), name="fmt")
fmt_str.global_constant = True
fmt_str.initializer = ir.Constant(ir.ArrayType(ir.IntType(8), 4), bytearray(b"%s\n\0"))

# main function
fnty = ir.FunctionType(ir.IntType(32), [])
main = ir.Function(module, fnty, name="main")
block = main.append_basic_block(name="entry")
builder = ir.IRBuilder(block)

# get pointer to "%s\n"
fmt_ptr = builder.gep(fmt_str, [ir.Constant(ir.IntType(64), 0),
                                ir.Constant(ir.IntType(64), 0)])

# read printlang file, emit IR calls
with open("test.printlang") as f:
    for line in f:
        text = line.strip()
        if not text:
            continue
        # make a global constant for this string
        arr = bytearray(text.encode("utf-8") + b"\0")
        c = ir.Constant(ir.ArrayType(ir.IntType(8), len(arr)), arr)
        gv = ir.GlobalVariable(module, c.type, name="str_" + str(abs(hash(text)) % 10000))
        gv.global_constant = True
        gv.initializer = c
        ptr = builder.gep(gv, [ir.Constant(ir.IntType(64), 0),
                               ir.Constant(ir.IntType(64), 0)])
        builder.call(printf, [fmt_ptr, ptr])

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
exe_path = "printlang_exe"

with open(obj_path, "wb") as f:
    f.write(target_machine.emit_object(llvm_mod))

# --- Step 3: Link to executable ---
subprocess.check_call(["clang", obj_path, "-o", exe_path])

print(f"Executable written to {exe_path}")

