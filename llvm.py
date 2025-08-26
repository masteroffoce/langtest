from llvmlite import ir, binding

module = ir.Module(name="my_module")
func_type = ir.FunctionType(ir.IntType(32), [ir.IntType(32), ir.IntType(32)])
func = ir.Function(module, func_type, name="add")
block = func.append_basic_block(name="entry")
builder = ir.IRBuilder(block)

a, b = func.args
result = builder.add(a, b, name="res")
builder.ret(result)

print("IR")
print(module)

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

target = binding.Target.from_default_triple()
target_machine = target.create_target_machine()
backing_mod = binding.parse_assembly("")
engine = binding.create_mcjit_compiler(backing_mod, target_machine)

mod = binding.parse_assembly(str(module))
mod.verify()
engine.add_module(mod)
engine.finalize_object()

func_ptr = engine.get_function_address("add")

import ctypes
cfunc = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_int32, ctypes.c_int32)(func_ptr)

print("EXEC")
print(cfunc(1, 2))
