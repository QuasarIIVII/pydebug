import gdb
import re
import json
import inspect
import atexit

import sys, os
sys.path.append(os.getcwd())

from tools.classmethodable import classmethodable

class NULL_t():
	pass

NULL = NULL_t()

def cur_line():
    frame = inspect.currentframe()
    frameinfo = inspect.getframeinfo(frame.f_back)
    return frameinfo.lineno

'const char*'; cur_filename = gdb.Value(inspect.getframeinfo(inspect.currentframe()).filename)

def cuintptr_t():
	return gdb.lookup_type('uintptr_t')

class hook_source(gdb.Command):
	f_list = []

	def __init__(self):
		gdb.Command.__init__(
			self,
			"hook-source",
			gdb.COMMAND_OBSCURE
		)

	def invoke(self, arg, from_tty):
		for f in self.__class__.f_list:
			f()

	@classmethod
	def add(cls, f):
		cls.f_list.append(f)

hook_source()

def type_addr_name(ob):
	tp = ob.dereference()['ob_type']
	return hex(tp.cast(cuintptr_t())), tp.dereference()['tp_name'].string()

class qsave_out(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qsave_out",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		# print("args:", argv)
		gdb.set_convenience_variable(
			argv[0],
			gdb.execute(argv[1], to_string=True)
		)

qsave_out()

class qinit(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qinit",
			gdb.COMMAND_RUNNING,
			gdb.COMPLETE_FILENAME
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		gdb.execute("dir cenv/cpython/Python")
		gdb.execute("b *main")
		gdb.execute(f"run {argv[0]} >> log.txt")
		gdb.execute("b pyrun_file")

qinit()

class qmm_init(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qmm_init",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		try:
			f_type = gdb.parse_and_eval("(void*(*)(size_t))0").type
			malloc = gdb.parse_and_eval("malloc").cast(f_type)
			gdb.set_convenience_variable(
				"mm",
				malloc.dereference()(1<<20)
			)
		except Exception as e:
			import traceback
			tb = traceback.extract_tb(e.__traceback__)
			print(f"exception: {str(e)} @ {tb[-1].lineno}")

qmm_init()

class cc(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"cc",
			gdb.COMMAND_RUNNING,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		0 ; a  = ["_PyEval_EvalFrameDefault", "*_ZN5torch8autogradL18THPVariable_tensorEP7_objectS2_S2_"]
		2 ; a += ["*_Z16THPVariable_WrapN2at10TensorBaseE+37", "*_ZN5torch8autogradL18THPVariable_tolistEP7_objectS2_"]
		4 ; a += ["*builtin___build_class__"]

		x = a[int(argv[0])] if len(argv) == 1 else a[0]

		gdb.execute(f"tbreak {x}")
		gdb.execute("continue")

cc()

class pstr(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"pstr",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)

	def invoke(self, arg, is_tty):
		print(printers.PyUnicode(gdb.parse_and_eval(arg)), flush=True)

pstr()

class pobj(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"pobj",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		print(gdb.parse_and_eval(argv[1]).cast(gdb.lookup_type(argv[0]).pointer()).dereference(), flush=True)

pobj()

class pyVal_getters():
	# Simple Types
	@classmethod
	def PyUnicode(cls, ob):
		v = ob.cast(gdb.lookup_type("PyASCIIObject").pointer()) + 1
		v = v.cast(gdb.lookup_type("char").pointer())
		return v.string();

	@classmethod
	def PyLong(cls, ob):
		PyLongObjectPtr_t = gdb.lookup_type("PyLongObject").pointer()
		return int(ob.cast(PyLongObjectPtr_t)["long_value"]["ob_digit"].dereference())

	@classmethod
	def PyBool(cls, ob):
		return ob == gdb.parse_and_eval("&_Py_TrueStruct")

	# Cell Type
	@classmethod
	def PyCell(cls, ob):
		return ob.cast(gdb.lookup_type("PyCellObject").pointer()).dereference()["ob_ref"]

	@classmethod
	def PyCell_r(cls, ob, lv=0): # recursive
		if not int(ob):
			return NULL, lv

		if ob.dereference()["ob_type"] == gdb.parse_and_eval("&PyCell_Type"):
			return cls.PyCell_r(
				ob.cast(gdb.lookup_type("PyCellObject").pointer()).dereference()["ob_ref"],
				lv+1
			)
		else:
			return ob, lv

	# None Type
	@classmethod
	def PyNone(cls, ob):
		return None

	# Builtin Data Structure Types
	@classmethod
	def PyList(cls, ob):
		ob = ob.cast(gdb.lookup_type("PyListObject").pointer())
		sz = ob.dereference()["ob_base"]["ob_size"]

		src = ob.dereference()["ob_item"]

		res = []
		for i in range(0, sz):
			res.append(src[i].cast(gdb.lookup_type("PyObject").pointer()))

		return res

	@classmethod
	def PyTuple(cls, ob):
		ob = ob.cast(gdb.lookup_type("PyTupleObject").pointer())
		sz = ob.dereference()["ob_base"]["ob_size"]

		src = ob.dereference()["ob_item"]

		res = []
		for i in range(0, sz):
			res.append(src[i].cast(gdb.lookup_type("PyObject").pointer()))

		return res

	@classmethod
	def PyDict(cls, ob):
		ob = (
			gdb.parse_and_eval("PyDict_Items")(ob)
			.cast(gdb.lookup_type("PyListObject").pointer())
		)
		sz = ob.dereference()["ob_base"]["ob_size"]
		src = ob.dereference()["ob_item"]

		PyTupleObjectPtr_t = gdb.lookup_type("PyTupleObject").pointer()

		res = []
		for i in range(0, sz):
			if not int(src[i]):
				res.append(None)
				continue

			ob = src[i].cast(PyTupleObjectPtr_t).dereference()["ob_item"]
			res.append((ob[0], ob[1]))

		return res

class printers():
	# Simple Types
	@classmethod
	def PyUnicode(cls, ob):
		return pyVal_getters.PyUnicode(ob)

	@classmethod
	def PyLong(cls, ob):
		return str(pyVal_getters.PyLong(ob))

	@classmethod
	def PyBool(cls, ob):
		return str(
			"True"
			if pyVal_getters.PyBool(ob)
			else "False"
		)

	# Code Types
	@classmethod
	def PyCode(cls, ob):
		return cls.PyUnicode(ob.cast(gdb.lookup_type("PyCodeObject").pointer())["co_qualname"])

	@classmethod
	def PyFunction(cls, ob):
		return cls.PyUnicode(ob.cast(gdb.lookup_type("PyFunctionObject").pointer())["func_qualname"])

	@classmethod
	def PyModule(cls, ob):
		return cls.PyUnicode(ob.cast(gdb.lookup_type("PyModuleObject").pointer())["md_name"])

	# Cell Type
	@classmethod
	def PyCell(cls, ob):
		return "Cell{ " + pauto.f(
			pyVal_getters.PyCell(ob),
			True
		) + " }"

	# None Type
	@classmethod
	def PyNone(cls, ob):
		return "None"

	# Builtin Data Structure Types
	@classmethod
	def PyList(cls, ob):
		li = pyVal_getters.PyList(ob)
		sz = len(li)

		s = f"======== PyList (size = {sz}) ========\n"

		for i, a in enumerate(li):
			if not int(a):
				s += f"{i:<4}NULL\n"
				continue

			idx = gdb.add_history(a)
			s += f"{i:<4}{a.dereference()['ob_refcnt_split'][0]}, {a.dereference()['ob_refcnt_split'][1]}\n"
			s += ' '*4 + f"${idx} = {a}\n"
			s += ' '*4 + f"{a.dereference()['ob_type']}\n"
			s += ' '*4 + "val = "
			s += pauto.f(a)

			if i+1 != sz: s+='\n'

		return s

	@classmethod
	def PyTuple(cls, ob):
		tpl = pyVal_getters.PyTuple(ob)
		sz = len(tpl)

		s = f"======== PyTuple (size = {sz}) ========\n"

		for i, a in enumerate(tpl):
			if not int(a):
				s += f"{i:<4}NULL\n"
				continue

			idx = gdb.add_history(a)
			s += f"{i:<4}{a.dereference()['ob_refcnt_split'][0]}, {a.dereference()['ob_refcnt_split'][1]}\n"
			s += ' '*4 + f"${idx} = {a}\n"
			s += ' '*4 + f"{a.dereference()['ob_type']}\n"
			s += ' '*4 + "val = "
			s += pauto.f(a)

			if i+1 != sz: s+='\n'

		return s

	@classmethod
	def PyDict(cls, ob, title="PyDict"):
		di = pyVal_getters.PyDict(ob)
		sz = len(di)

		s = f"======== {title} (size = {sz}) ========\n"

		for i, ob in enumerate(di):
			ss = [["" for _ in range(4)] for _ in range(2)]

			if ob is None:
				s += f"{i:<4}NULL\n"
				continue

			if not int(ob[0].cast(cuintptr_t())):
				ss[0][0] = "NULL"
			else:
				a = ob[0].cast(gdb.lookup_type("PyObject").pointer())
				idx = gdb.add_history(a)
				ss[0][0] = (lambda i, x:f"{i:<4}{x[0]}, {x[1]}")(i, a.dereference()['ob_refcnt_split'])
				ss[0][1] = ' '*4 + f"${idx} = {a}"
				ss[0][2] = ' '*4 + f"{a.dereference()['ob_type']}"
				ss[0][3] = ' '*4 + "key = " + pauto.f(a)

			if not int(ob[1].cast(cuintptr_t())):
				ss[1][0] = "NULL"
			else:
				a = ob[1].cast(gdb.lookup_type("PyObject").pointer())
				idx = gdb.add_history(a)
				ss[1][0] = (lambda i, x:f"{x[0]}, {x[1]}")(i, a.dereference()['ob_refcnt_split'])
				ss[1][1] = f"${idx} = {a}"
				ss[1][2] = f"{a.dereference()['ob_type']}"
				ss[1][3] = "val = " + pauto.f(a)

			w = max([len(ss[0][i]) for i in range(4)] + [48]) + 4
			s += f"{ss[0][0]:<{w}}{ss[1][0]}\n"
			s += f"{ss[0][1]:<{w}}{ss[1][1]}\n"
			s += f"{ss[0][2]:<{w}}{ss[1][2]}\n"
			s += f"{ss[0][3]:<{w}}{ss[1][3]}"

			if i+1 != sz: s+='\n'

		return s

class pauto(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"pauto",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)

	def invoke(self, arg, is_tty):
		print(self.f(gdb.parse_and_eval(arg), True), flush=True)

	@classmethod
	def f(cls, ob, ptype = False):
		if not int(ob.cast(cuintptr_t())):
			return "NULL"


		def ob_type2int(x):
			return int(gdb.parse_and_eval(x).cast(cuintptr_t()))

		m = {
			# Simple Types
			ob_type2int("&PyUnicode_Type")	: printers.PyUnicode,
			ob_type2int("&PyLong_Type")		: printers.PyLong,
			ob_type2int("&PyBool_Type")		: printers.PyBool,
			# Code Types
			ob_type2int("&PyCode_Type")		: printers.PyCode,
			ob_type2int("&PyFunction_Type")	: printers.PyFunction,
			ob_type2int("&PyModule_Type")	: printers.PyModule,
			# Cell Type
			ob_type2int("&PyCell_Type")		: printers.PyCell,
			# None Type
			ob_type2int("&_PyNone_Type")	: printers.PyNone,
		}

		s = ""
		try:
			if ptype: s += f"{ob.dereference()['ob_type'].dereference()['tp_name'].string()}: "
			s += m[int(ob.dereference()["ob_type"].cast(cuintptr_t()))](ob)
		except KeyError:
			s = f"Unknown Type: {ob.dereference()['ob_type']}"

		return s

pauto()

class pautoex(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"pautoex",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)

	def invoke(self, arg, is_tty):
		print(self.f(gdb.parse_and_eval(arg)), flush=True)

	@classmethod
	def f(cls, ob):
		if not int(ob.cast(cuintptr_t())):
			return "NULL"

		def ob_type2int(x):
			return int(gdb.parse_and_eval(x).cast(cuintptr_t()))

		m = {
			# Builtin Data Structure Types
			ob_type2int("&PyList_Type")		: printers.PyList,
			ob_type2int("&PyTuple_Type")	: printers.PyTuple,
			ob_type2int("&PyDict_Type")		: printers.PyDict,
		}

		try:
			s = m[int(ob.dereference()["ob_type"].cast(cuintptr_t()))](ob)
		except KeyError:
			s = f"Unknown type: {ob.dereference()['ob_type']}"

		return s

pautoex()

class obj_mem_mgr:
	objs = {}
	next_id = 0
	n = 0
	objset = set()

	def __init__(self):
		self.objs = {}
		self.next_id = 0
		self.n = 0
		self.objset = set()

	@classmethodable
	def add(clr, ob) -> int | None :
		ptr = int(ob.cast(cuintptr_t()))
		if ptr in clr.objset:
			return

		clr.objset.add(ptr)
		clr.objs[clr.next_id] = ob
		clr.next_id += 1
		clr.n += 1

		return clr.next_id - 1

	@classmethodable
	def remove(clr, ob_id) -> bool:
		# print(f"obj_mem_mgr.remove {clr}", flush=True)
		if ob_id not in clr.objs:
			return False

		ob = clr.objs[ob_id]
		clr.objs.pop(ob_id)
		clr.objset.remove(int(ob.cast(cuintptr_t())))

		gdb.parse_and_eval("Py_DECREF").dereference()(
			cur_filename,
			gdb.Value(cur_line()),
			ob
		)

		clr.n -= 1

		return True

	@classmethodable
	def clear(clr):
		for _, ob in clr.objs.items():
			# print(f"Py_DECREF: {hex(int(ob.cast(cuintptr_t())))}")
			gdb.parse_and_eval("Py_DECREF").dereference()(
				cur_filename,
				gdb.Value(cur_line()),
				ob
			)
		clr.objs = {}
		clr.next_id = 0
		clr.n = 0
		clr.objset = set()

	@classmethodable
	def __del__(clr):
		# print(f"obj_mem_mgr.__del__ {clr}", flush=True)
		for _, ob in clr.objs.items():
			# print(f"Py_DECREF: {hex(int(ob.cast(cuintptr_t())))}")
			gdb.parse_and_eval("Py_DECREF").dereference()(
				cur_filename,
				gdb.Value(cur_line()),
				ob
			)

	@classmethod
	def __static__del__(cls):
		cls.__del__()

hook_source.add(obj_mem_mgr.__static__del__)

class cvt_thp2list(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"cvt_thp2list",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)
		self.omm = obj_mem_mgr()

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		# Call THPVariable_tolist(PyObject*, PyObject*)

		if argv[0] == '-c':
			self.omm.clear()
			return

		if argv[0] == '-r':
			res = gdb.parse_and_eval("_ZN5torch8autogradL18THPVariable_tolistEP7_objectS2_").cast(
				gdb.parse_and_eval("(PyObject*(*)(PyObject*, PyObject*))0").type
			).dereference()(gdb.parse_and_eval(argv[1]), 0)
			idx = gdb.add_history(res)
			print(f"${idx} = {res}")
			self.omm.add(res)
			return

		res = self.g(self.f(gdb.parse_and_eval(arg)))

		print(res)

	@classmethod
	def f(cls, ob):
		li = gdb.parse_and_eval("_ZN5torch8autogradL18THPVariable_tolistEP7_objectS2_").cast(
			gdb.parse_and_eval("(PyObject*(*)(PyObject*, PyObject*))0").type
		).dereference()(ob, 0)

		res = cls._f(li)

		gdb.parse_and_eval("Py_DECREF").dereference()(
			cur_filename,
			gdb.Value(cur_line()),
			li
		)

		return res

	@classmethod
	def _f(cls, ob, PyList_Type=None):
		if PyList_Type is None:
			PyList_Type = gdb.parse_and_eval("&PyList_Type")

		if ob.dereference()["ob_type"] == PyList_Type:
			return [cls._f(x, PyList_Type) for x in pyVal_getters.PyList(ob)]
		else:
			return ob

	@classmethod
	def g(cls, ob):
		if type(ob) is list:
			return [cls.g(x) for x in ob]
		else:
			return pauto.f(ob, True)

cvt_thp2list()

class cvt_obj2str(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"cvt_obj2str",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)

	def invoke(self, arg, is_tty):
		v, t = self.f(gdb.parse_and_eval(arg))
		print(f"type = {t}\nval = {v}")

	@classmethod
	def f(cls, ob):
		raw = gdb.parse_and_eval("unicode_new_impl").dereference()(
			gdb.parse_and_eval("&PyUnicode_Type"),
			ob,
			0,
			0
		)

		res = pyVal_getters.PyUnicode(raw)

		gdb.parse_and_eval("Py_DECREF").dereference()(
			cur_filename,
			gdb.Value(cur_line()),
			raw
		)

		tp_name = ob.dereference()["ob_type"].dereference()["tp_name"].string()

		return res, tp_name

cvt_obj2str()

class qi(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qi",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		s, e = -1, 8

		if len(argv) == 1:
			e = int(argv[0])
		elif len(argv) == 2:
			s = int(argv[0])
			e = int(argv[1])

		print(f"======== instr [{s}, {e}) ========")

		frame = gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame")
		lasti = int((
			frame.dereference()["prev_instr"]
			-
			frame.dereference()["f_code"].dereference()["co_code_adaptive"]
			.cast(gdb.lookup_type("_Py_CODEUNIT").pointer())
		).cast(gdb.lookup_type("int")))

		for i in range(s, e):
			op = gdb.parse_and_eval("_PyEval_EvalFrameDefault::next_instr")[i]["op"]
			op_name = gdb.parse_and_eval("_PyOpcode_OpName")[int(op['code'])].string()
			print(f"{lasti+1+i:<6}{i:<4}{int(op['code']):<4}{op_name:<28}{int(op['arg'])}")

		print(end='',flush=True)

qi()

class qst(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qst",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)
		s, e = 1, 8

		if len(argv) == 1:
			e = int(argv[0])
		elif len(argv) == 2:
			s = int(argv[0])
			e = int(argv[1])

		print(f"======== stack [-{s}, -{e}] ========")

		for i in range(s, e):
			ob = gdb.parse_and_eval("_PyEval_EvalFrameDefault::stack_pointer")[-i]
			if int(ob.cast(cuintptr_t())) == 0xffffffff:
				break

			if not int(ob.cast(cuintptr_t())):
				print(f"-{i:<4}null")
				continue

			print(f"-{i:<4}{ob.dereference()['ob_refcnt_split'][0]}, {ob.dereference()['ob_refcnt_split'][1]}")
			a = ob.cast(gdb.lookup_type('PyObject').pointer())
			idx = gdb.add_history(a)
			print(' '*5 + f"${idx} = {a}")
			print(' '*5 + f"{type_addr_name(a)}")
			print(' '*5 + "val = ", end='')
			print(pauto.f(a))

		print(end='',flush=True)

qst()

class qconsts(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qconsts",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		# argv = gdb.string_to_argv(arg)

		src = (
			gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame")
			.dereference()['f_code']
			.dereference()['co_consts']
		)

		e = int(
			src
			.cast(gdb.lookup_type("PyTupleObject").pointer())
			.dereference()['ob_base']['ob_size']
		)

		print(f"======== co_consts [0, {e}) ========",)

		for i in range(e):
			ob = src.cast(gdb.lookup_type("PyTupleObject").pointer()) \
				.dereference()['ob_item'][i]
			if not int(ob.cast(cuintptr_t())):
				print(f"{i:<4}null")
				continue

			print(f"{i:<4}{ob.dereference()['ob_refcnt_split'][0]}, {ob.dereference()['ob_refcnt_split'][1]}")
			a = ob.cast(gdb.lookup_type('PyObject').pointer())
			idx = gdb.add_history(a)
			print(' '*4 + f"${idx} = {a}")
			print(' '*4 + f"{a.dereference()['ob_type']}")
			print(' '*4 + "val = ", end='')
			print(pauto.f(a))

		print(end='',flush=True)

qconsts()

class qflocals(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qflocals",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		# argv = gdb.string_to_argv(arg)

		frame = gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame")
		src = frame.dereference()["localsplus"]
		n = int(frame.dereference()["f_code"].dereference()["co_nlocalsplus"])

		localsplusnames = pyVal_getters.PyTuple(
			frame
			.dereference()["f_code"]
			.dereference()["co_localsplusnames"]
		)
		localsplusnames = [pyVal_getters.PyUnicode(a) for a in localsplusnames]

		print(f"======== localsplus [0, {n}) ========")
		if not int(src.cast(cuintptr_t())):
			print("NULL")

		for i in range(n):
			ob = src[i]
			if not int(ob.cast(cuintptr_t())):
				print(f"{i:<4}name = {localsplusnames[i]}")
				print(' '*4 + "null")
				continue

			print(f"{i:<4}{ob.dereference()['ob_refcnt_split'][0]}, {ob.dereference()['ob_refcnt_split'][1]}")
			a = ob.cast(gdb.lookup_type('PyObject').pointer())
			idx = gdb.add_history(a)
			print(' '*4 + f"${idx} = {a}")
			print(' '*4 + f"{a.dereference()['ob_type']}")
			print(' '*4 + f"name = {localsplusnames[i]}")
			print(' '*4 + "val = ", end='')
			print(pauto.f(a))

		print(end='',flush=True)

qflocals()

class qlocals(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qlocals",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		print(printers.PyDict(
			gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame").dereference()["f_locals"],
			"locals")
		)

qlocals()

class qbt(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qbt",
			gdb.COMMAND_STACK,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		# argv = gdb.string_to_argv(arg)

		print("======== backtrace ========")

		i = 0
		a = gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame")
		while True:
			print(f"{i:<4}{pauto.f(a.dereference()['f_code'].dereference()['co_qualname'])}")

			prev = a.dereference()['previous']
			if not int(prev.cast(cuintptr_t())):
				break

			i+=1
			a = prev

		print(end='',flush=True)

qbt()

class qn(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qn",
			gdb.COMMAND_RUNNING,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)

		n = 1
		if len(argv) == 1:
			n = int(argv[0])

		for _ in range(n):
			a = gdb.parse_and_eval("_PyEval_EvalFrameDefault::next_instr")

			while a == gdb.parse_and_eval("_PyEval_EvalFrameDefault::next_instr"):
				gdb.execute("next")

qn()

class qfin(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qfin",
			gdb.COMMAND_RUNNING,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		# argv = gdb.string_to_argv(arg)

		a = gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame").dereference()["previous"]

		while gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame") != a:
			gdb.execute("next")

qfin()

class bpoints:
	class bp:
		def __init__(self, *argv):
			if len(argv) == 0:
				self.__init__a()
			elif len(argv) == 1:
				self.__init__a(argv[0])
			elif len(argv) == 4:
				self.__init__b(*argv)
			else:
				raise TypeError

		def __init__b(self, filename, qualname, firstlineno, lasti):
			self.filename = filename
			self.qualname = qualname
			self.firstlineno = firstlineno
			self.lasti = lasti

		def __init__a(self, offset=0):
			frame = gdb.parse_and_eval(f"_PyEval_EvalFrameDefault::frame")
			f_code = frame.dereference()["f_code"]

			self.filename = printers.PyUnicode(f_code.dereference()["co_filename"])
			self.qualname = printers.PyUnicode(f_code.dereference()["co_qualname"])
			self.firstlineno = int(f_code.dereference()["co_firstlineno"])
			self.lasti = int((
				frame.dereference()["prev_instr"]
				-
				frame.dereference()["f_code"].dereference()["co_code_adaptive"]
				.cast(gdb.lookup_type("_Py_CODEUNIT").pointer())
			).cast(gdb.lookup_type("int"))) + offset

		def __str__(self):
			return f"(f=\"{self.filename}\", q={self.qualname}, l={self.firstlineno}, i={self.lasti})"

		def __eq__(self, other):
			return (
				(self.filename == other.filename)
				& (self.qualname == other.qualname)
				& (self.firstlineno == other.firstlineno)
				& (self.lasti == other.lasti)
			)

		def __hash__(self):
			return (
				hash(self.filename)
				^ hash(self.qualname)
				^ hash(self.firstlineno)
				^ hash(self.lasti)
			)

	class qb(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qb",
				gdb.COMMAND_BREAKPOINTS,
				gdb.COMPLETE_NONE
			)

		def invoke(self, arg, is_tty):
			argv = gdb.string_to_argv(arg)
			# print("args:", argv)

			x = (
				bpoints.bp(int(argv[0]))
				if len(argv) == 1
				else bpoints.bp()
			)

			if x not in self.ns.sbps:
				self.ns.sbps.add(x)
				self.ns.bps.append(x)

	class pb(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"pb",
				gdb.COMMAND_BREAKPOINTS,
				gdb.COMPLETE_NONE
			)

		def invoke(self, arg, is_tty):
			argv = gdb.string_to_argv(arg)

			s = 0
			e = len(self.ns.bps)

			if len(argv) == 1:
				e = int(argv[0])
			elif len(argv) == 2:
				s = int(argv[0])
				e = int(argv[1])

			print(f"======== pybreakpoints [{s}, {e}) ========")

			for i in range(s, e):
				a = self.ns.bps[i]
				if a is None: continue
				print(f"{i:<4}filename=\"{a.filename}\"\tfirstlineno={a.firstlineno}")
				print(f"    qualname={a.qualname}\tlasti={a.lasti}")

	class qdb(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qdb",
				gdb.COMMAND_BREAKPOINTS,
				gdb.COMPLETE_NONE
			)

		def invoke(self, arg, is_tty):
			argv = gdb.string_to_argv(arg)

			for i in range(len(argv)):
				a = int(argv[i])

				if len(self.ns.bps) <= a:
					print(f"breakpoint index {a} is out of range")
					continue

				if self.ns.bps[a] is None:
					print(f"invalid breakpoint index: {a}")
					continue

				self.ns.sbps.remove(self.ns.bps[a])
				self.ns.bps[a] = None

	class qbsave(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qbsave",
				gdb.COMMAND_BREAKPOINTS,
				gdb.COMPLETE_FILENAME
			)

		def invoke(self, arg, is_tty):
			# argv = gdb.string_to_argv(arg)
			with open(arg, "w") as f:
				for a in self.ns.bps:
					if a is None: continue
					f.write(str(a)+'\n')

	class qbload(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qbload",
				gdb.COMMAND_BREAKPOINTS,
				gdb.COMPLETE_FILENAME
			)

			self.pat = re.compile(
				r'''\(\s*
				f="(?P<f>(?:\\.|[^"\\])*)",\s*
				q=(?P<q>(?:\\.|[^,\)])+?)\s*,\s*
				l=(?P<l>\d+)\s*,\s*
				i=(?P<i>-?\d+)\s*
				\)\s*''',
				re.VERBOSE
			)

		def invoke(self, arg, is_tty):
			# argv = gdb.string_to_argv(arg)
			self.ns.bps = []
			self.ns.sbps = set()

			with open(arg, "r") as f:
				for line in f:
					m = self.pat.match(line.strip())
					if not m:
						raise ValueError(f"Wrong format: {line!r}")

					x = bpoints.bp(m.group('f'), m.group('q'), int(m.group('l')), int(m.group('i')))
					self.ns.bps.append(x)
					self.ns.sbps.add(x)

	class qc(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qc",
				gdb.COMMAND_RUNNING,
				gdb.COMPLETE_NONE
			)

		def invoke(self, arg, is_tty):
			argv = gdb.string_to_argv(arg)
			s = (
				{self.ns.bps[int(i)] for i in argv if self.ns.bps[int(i)] is not None}
				if len(argv)
				else self.ns.sbps
			)

			print({str(a) for a in s})

			t = gdb.parse_and_eval("_PyEval_EvalFrameDefault::next_instr")
			while True:
				a = t

				while True:
					t = gdb.parse_and_eval("_PyEval_EvalFrameDefault::next_instr")
					if a != t: break
					gdb.execute("next")

				if bpoints.bp() in s:
					break

	def __init__(self):
		self.bps = []
		self.sbps = set()

		self.qb(self)
		self.pb(self)
		self.qdb(self)
		self.qbsave(self)
		self.qbload(self)
		self.qc(self)

bpoints()

class qlookup(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qlookup",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

		self.pat = re.compile(r"^\-([a-z]+)$")

	def invoke(self, arg, is_tty):
		argv = gdb.string_to_argv(arg)

		target = None
		in_builtin = False
		in_global = False
		in_local = False
		in_flocal = False
		scope = 0

		for a in argv:
			m = self.pat.match(a)
			if m:
				for b in m.group(1):
					if   b == 'b': scope |= 8
					elif b == 'g': scope |= 4
					elif b == 'l': scope |= 2
					elif b == 'f': scope |= 1
			else:
				target = a

		if not scope:
			scope = 15

		if target is None:
			print("No target specified")
			return

		# print(scope&8, scope&4, scope&2, scope&1)

		res = self.f(target, scope)
		if res is None:
			print("No such name found")
			return

		scope_str = {
			0: "localsplus",
			1: "locals",
			2: "globals",
			3: "Builtin",
		}

		if res[2] is not NULL:
			v = cvt_obj2str.f(res[2])
		else:
			v = ("NULL", "*")

		frame_qualname = pyVal_getters.PyUnicode(res[0].dereference()['f_code'].dereference()['co_qualname'])
		print(f"where={frame_qualname},{scope_str[res[1]]} val={v[0]} type={v[1]} depth={res[3]}")

	@classmethod
	def f(cls, target, scope, frame_qualname=None, frame_name=None):
		'''
		return value:
			None when looking up fails
			(frame, scope, value, depth) on success
			frame: gdb.Value type. frame where the variable is founded
			scope: int type. scope where the variable is founded
				0: localsplus (fast local)
				1: locals
				2: globals
				3: builtins
			value: gdb.Value type. the value of the target variable
			depth: the number of Cells wrapping the value
		'''

		frame = gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame")

		if frame_qualname is None and frame_name is None:
			ret = cls._f(target, scope, frame)
			if ret is None:
				return None
			return frame, *ret

		if frame_qualname is not None:
			while True:
				name = pyVal_getters.PyUnicode(frame.dereference()['f_code'].dereference()['co_qualname'])
				if name == frame_qualname:
					break

				prev = frame.dereference()['previous']
				if not int(prev.cast(cuintptr_t())):
					frame = None
					break

				frame = prev

			if frame is not None:
				ret = cls._f(target, scope, frame)
				if ret is not None:
					return frame, *ret

		if frame is None:
			frame = gdb.parse_and_eval("_PyEval_EvalFrameDefault::frame")

		if frame_name is not None:
			while True:
				name = pyVal_getters.PyUnicode(frame.dereference()['f_code'].dereference()['co_qualname'])
				if name == frame_name:
					break

				prev = frame.dereference()['previous']
				if not int(prev.cast(cuintptr_t())):
					frame = None
					break

				frame = prev

			if frame is not None:
				ret = cls._f(target, scope, frame)
				if ret is not None:
					return frame, *ret

		return None

	@classmethod
	def _f(cls, target, scope, frame):
		f_code = frame.dereference()["f_code"]

		localsplus = frame.dereference()["localsplus"]
		if scope&1 and int(localsplus.cast(cuintptr_t())):
			localsplusnames = pyVal_getters.PyTuple(f_code.dereference()["co_localsplusnames"])

			localsplusnames = [pyVal_getters.PyUnicode(a) for a in localsplusnames]

			try:
				return 0, *pyVal_getters.PyCell_r(localsplus[localsplusnames.index(target)])
			except ValueError:
				pass

		A = [
			(1, scope&2, frame.dereference()["f_locals"]),
			(2, scope&4, frame.dereference()["f_globals"]),
			(3, scope&8, frame.dereference()["f_builtins"])
		]

		A = [(i, y) for i, x, y in A if x and int(y.cast(cuintptr_t()))]

		for i, f in A:
			for a in pyVal_getters.PyDict(f):
				if a is NULL:
					continue

				if pyVal_getters.PyUnicode(a[0]) != target:
					continue

				return i, *pyVal_getters.PyCell_r(a[1])

		return None

qlookup()

class qwatch:
	class qwatch_init(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qwatch_init",
				gdb.COMMAND_DATA,
				gdb.COMPLETE_FILENAME
			)

		def invoke(self, arg, is_tty):
			argv = gdb.string_to_argv(arg)
			with open(argv[0], 'r') as f:
				config = json.load(f)

			self.ns.config["path"] = config["path"]
			if self.ns.file is not None:
				self.ns.file.close()
			self.ns.file = open(self.ns.config["path"], "wb")

			config_targets = self.ns.config["targets"]

			config_targets.clear()

			for c in config["targets"]:
				a = {
					"name": None,
					"scope": 0,
					"frameq": None,
					"frame": None,
					"vz": False,
				}

				for k, v in c.items():
					if k == "name":
						a["name"] = v
					elif k == "scope":
						for b in v:
							if   b == 'b': a["scope"] |= 8
							elif b == 'g': a["scope"] |= 4
							elif b == 'l': a["scope"] |= 2
							elif b == 'f': a["scope"] |= 1
							else:
								config_targets.clear()
								print(f"Unknown scope option: {b}")
								return
					elif k == "frame":
						if v == "*":
							a["frame"] = None
						elif type(v) is str:
							a["frame"] = v
						else:
							config_targets.clear()
							print(f"Invalid frame option value type: {v}")
							return
					elif k == "frameq":
						if v == "*":
							a["frameq"] = None
						elif type(v) is str:
							a["frameq"] = v
						else:
							config_targets.clear()
							print(f"Invalid frameq option value type: {v}")
							return
					elif k == "vz": # Visualize value if True
						if type(v) is not bool:
							config_targets.clear()
							print(f"Invalid vz option value type: {v}")
							return
						a["vz"] = v
					else:
						config_targets.clear()
						print(f"Unknown option: {k}")
						return

				if a["name"] is None:
					config_targets.clear()
					print("No name specified")
					return

				if not a["scope"]:
					a["scope"] = 15

				config_targets.append(a)

			# print(config_targets)

	class qwatch(gdb.Command):
		def __init__(self, ns):
			self.ns = ns
			gdb.Command.__init__(
				self,
				"qwatch",
				gdb.COMMAND_DATA,
				gdb.COMPLETE_NONE
			)

		def invoke(self, arg, is_tty):
			try:
				THPVariableType = gdb.parse_and_eval("&THPVariableType")
			except gdb.error as e:
				THPDeviceType = None

			f = self.ns.file
			f.write(b"\\(watch\\:")
			for a in self.ns.config["targets"]:
				v = qlookup.f(a["name"], a["scope"], a["frameq"], a["frame"])
				name = a["name"].replace("\\", "\\\\")
				if v is None:
					f.write(f"\\({name}\\:\\)".encode())
					continue

				vf, vs, vv, vd = v

				if( a["vz"]
				and vv.dereference()["ob_type"].dereference()['tp_base'] == THPVariableType
				and cvt_obj2str.f(vv)[1] == "Tensor"
				):
					tp = cvt_obj2str.f(vv)[1]
					sv = cvt_thp2list.f(vv)
					shp = self.shape(sv)
					flt = [cvt_obj2str.f(x)[0] for x in self.flatten(sv)]
					data = [len(shp)] + shp + flt

					sv = "\\(vz\\:"
					for x in data:
						sv += f"{x}\\,"
					sv += "\\)"
				else:
					if vv is NULL:
						sv, tp = "NULL", "*"
					else:
						sv, tp = cvt_obj2str.f(vv)
						sv = sv.replace("\\", "\\\\")
						tp = tp.replace("\\", "\\\\")

				frame_qualname = pyVal_getters.PyUnicode(
					vf
					.dereference()['f_code']
					.dereference()['co_qualname']
				)

				frame_qualname = frame_qualname.replace("\\", "\\\\")
				f.write(f"\\({name}\\:{sv}\\,{tp}\\,{vd}\\,{frame_qualname}\\,{vs}\\)".encode())
			f.write(b"\\)")
			f.flush()

		@classmethod
		def flatten(cls, li, dest=None):
			if dest is None:
				dest = []

			if type(li) is list:
				for x in li:
					cls.flatten(x, dest)
			else:
				dest.append(li)

			return dest

		@classmethod
		def shape(cls, li, dest=None):
			if dest is None:
				dest = []

			print(li)
			if type(li) is list:
				sz = len(li)
				dest.append(sz)
				if sz:
					cls.shape(li[0], dest)
			return dest

	def __init__(self):
		self.config = {
			"path": "",
			"targets": [],
		}
		self.file = None

		self.qwatch_init(self)
		self.qwatch(self)

	def __del__(self):
		if self.file is not None:
			self.file.close()

qwatch()
