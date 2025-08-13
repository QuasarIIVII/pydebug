import gdb
import re

def cuintptr_t():
	return gdb.lookup_type('uintptr_t')

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
		gdb.execute("dir cpython")
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
		a = ["_PyEval_EvalFrameDefault", "*_ZN5torch8autogradL18THPVariable_tensorEP7_objectS2_S2_"]
		a += ["*_Z16THPVariable_WrapN2at10TensorBaseE+37", "*_ZN5torch8autogradL18THPVariable_tolistEP7_objectS2_"]

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

class printers():
	# Simple Types
	@classmethod
	def PyUnicode(cls, ob):
		v = ob.cast(gdb.lookup_type("PyASCIIObject").pointer()) + 1
		v = v.cast(gdb.lookup_type("char").pointer())

		return v.string();

	@classmethod
	def PyLong(cls, ob):
		PyLongObjectPtr_t = gdb.lookup_type("PyLongObject").pointer()

		return str(ob.cast(PyLongObjectPtr_t)["long_value"]["ob_digit"].dereference())

	@classmethod
	def PyBool(cls, ob):
		return str(
			"True"
			if ob == gdb.parse_and_eval("&_Py_TrueStruct")
			else "False"
		)

	# Code Types
	@classmethod
	def PyCode(cls, ob):
		return cls.PyUnicode(ob.cast(gdb.lookup_type("PyCodeObject").pointer())["co_name"])

	@classmethod
	def PyFunction(cls, ob):
		return cls.PyUnicode(ob.cast(gdb.lookup_type("PyFunctionObject").pointer())["func_name"])

	@classmethod
	def PyModule(cls, ob):
		return cls.PyUnicode(ob.cast(gdb.lookup_type("PyModuleObject").pointer())["md_name"])

	# None Type
	@classmethod
	def PyNone(cls, ob):
		return "None"

	# Builtin Data Structure Types
	@classmethod
	def PyList(cls, ob):
		ob = ob.cast(gdb.lookup_type("PyListObject").pointer())
		sz = ob.dereference()["ob_base"]["ob_size"]

		s = f"======== PyList (size = {sz}) ========\n"

		src = ob.dereference()["ob_item"]

		for i in range(0, sz):
			if not int(src[i].cast(cuintptr_t())):
				s += "NULL\n"
				continue

			a = src[i].cast(gdb.lookup_type("PyObject").pointer())
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
		ob = ob.cast(gdb.lookup_type("PyTupleObject").pointer())
		sz = ob.dereference()["ob_base"]["ob_size"]

		s = f"======== PyTuple (size = {sz}) ========\n"

		src = ob.dereference()["ob_item"]

		for i in range(0, sz):
			if not int(src[i].cast(cuintptr_t())):
				s += "NULL\n"
				continue

			a = src[i].cast(gdb.lookup_type("PyObject").pointer())
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
		ob = (
			gdb.parse_and_eval("PyDict_Items")(ob)
			.cast(gdb.lookup_type("PyListObject").pointer())
		)

		sz = ob.dereference()["ob_base"]["ob_size"]

		s = f"======== {title} (size = {sz}) ========\n"

		PyTupleObjectPtr_t = gdb.lookup_type("PyTupleObject").pointer()
		src = ob.dereference()["ob_item"]

		for i in range(0, sz):
			ss = [["" for _ in range(4)] for _ in range(2)]

			if not int(src[i].cast(cuintptr_t())):
				s += "NULL\n"
				continue

			ob = src[i].cast(PyTupleObjectPtr_t).dereference()["ob_item"]
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
			# None Type
			ob_type2int("&_PyNone_Type")	: printers.PyNone,
		}

		s = ""
		try:
			if ptype: s += f"{ob.dereference()['ob_type']}: "
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

class cvt_thp2list(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"cvt_thp2list",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_EXPRESSION
		)

	def invoke(self, arg, is_tty):
		try:
			# Call THPVariable_tolist(PyObject*, PyObject*)
			res = gdb.parse_and_eval("_ZN5torch8autogradL18THPVariable_tolistEP7_objectS2_").cast(
				gdb.parse_and_eval("(PyObject*(*)(PyObject*, PyObject*))0").type
			).dereference()(gdb.parse_and_eval(arg), 0)
			idx = gdb.add_history(res)
			print(f"${idx} = {res}")
		except Exception as e:
			print(f"exception: {str(e)}")

cvt_thp2list()

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
			ob = gdb.parse_and_eval("stack_pointer")[-i]
			if int(ob.cast(cuintptr_t())) == 0xffffffff:
				break

			if not int(ob.cast(cuintptr_t())):
				print(f"-{i:<4}null")
				continue

			print(f"-{i:<4}{ob.dereference()['ob_refcnt_split'][0]}, {ob.dereference()['ob_refcnt_split'][1]}")
			a = ob.cast(gdb.lookup_type('PyObject').pointer())
			idx = gdb.add_history(a)
			print(' '*5 + f"${idx} = {a}")
			print(' '*5 + f"{a.dereference()['ob_type']}")
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
			gdb.parse_and_eval("frame")
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

class qargs(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qargs",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		# argv = gdb.string_to_argv(arg)

		frame = gdb.parse_and_eval("frame")
		src = frame.dereference()["localsplus"]
		n = int(frame.dereference()["f_code"].dereference()["co_nlocalsplus"])

		print("======== args [0, {n}) ========")
		if not int(src.cast(cuintptr_t())):
			print("NULL")

		for i in range(n):
			ob = src[i]
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

qargs()

class qlocals(gdb.Command):
	def __init__(self):
		gdb.Command.__init__(
			self,
			"qlocals",
			gdb.COMMAND_DATA,
			gdb.COMPLETE_NONE
		)

	def invoke(self, arg, is_tty):
		print(printers.PyDict(gdb.parse_and_eval("frame").dereference()["f_locals"], "locals"))

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
		a = gdb.parse_and_eval('frame')
		while True:
			prev = a.dereference()['previous']
			if not int(prev.cast(cuintptr_t())):
				break

			print(f"{i:<4}{pauto.f(a.dereference()['f_funcobj'])}")

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

		a = gdb.parse_and_eval("frame").dereference()["previous"]

		while gdb.parse_and_eval("frame") != a:
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
