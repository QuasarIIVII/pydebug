define qinit
	dir cpython
	b *main
	run $arg0 >> log.txt
	b pyrun_file
end

define cc
	tb _PyEval_EvalFrameDefault
	c
end

define pstr
	printf "%s\n", (char*)((PyASCIIObject*)$arg0 + 1)
end

define pobj
	p *(($arg0*)$arg1)
end

define pauto
	set $ob = $arg0

	set $x = 1
	if !$ob
		p "null"
		set $x = 0
	else
		# Simple Types
		if $x && $ob->ob_type == &PyUnicode_Type
			pstr $ob
			set $x = 0
		end
		if $x && $ob->ob_type == &PyLong_Type
			printf "%d\n", ((PyLongObject*)$ob)->long_value->ob_digit
			set $x = 0
		end
		if $x && $ob->ob_type == &PyBool_Type
			printf "%s", $ob == &_Py_TrueStruct ? "True\n" : "False\n"
			set $x = 0
		end
		# Code Types
		if $x && $ob->ob_type == &PyCode_Type
			pstr ((PyCodeObject*)$ob)->co_name
			set $x = 0
		end
		if $x && $ob->ob_type == &PyFunction_Type
			pstr ((PyFunctionObject*)$ob)->func_name
			set $x = 0
		end
		if $x && $ob->ob_type == &PyModule_Type
			pstr ((PyModuleObject*)$ob)->md_name
			set $x = 0
		end
		# None Type
		if $x && $ob->ob_type == &_PyNone_Type
			printf "None\n"
			set $x = 0
		end
		if $x
			p $ob->ob_type
			set $x = 0
		end
	end
end

define qi
	set $s = -1
	set $e = 8

	if $argc == 1
		set $e = $arg0
	end

	if $argc == 2
		set $s = $arg0
		set $e = $arg1
	end

	printf "======== instr [%d, %d) ========\n", $s, $e

	set $i = $s
	while( $i < $e )
		printf "%-4d%d\t%-28s%d\n", $i, _PyEval_EvalFrameDefault::next_instr[$i].op.code, q_decode_opcode[_PyEval_EvalFrameDefault::next_instr[$i].op.code], _PyEval_EvalFrameDefault::next_instr[$i].op.arg
		set $i = $i + 1
	end
end

define qst
	set $e = 8
	if $argc == 1
		set $e = $arg0
	end

	printf "======== stack [-1, -%d] ========\n", $e

	set $i = 1
	while( $i <= $e )
		if ($ob = stack_pointer[-$i]) != 0
			printf "-%d\t%d, %d\n\t", $i, $ob->ob_refcnt_split[0], $ob->ob_refcnt_split[1]
			p (PyObject*)$ob
			printf "\t"
			p $ob->ob_type

			printf "\tval = "
			pauto $ob
		else
			printf "-%d\tnull\n", $i
		end
		set $i = $i + 1
	end
end

define qconsts
	set $e = ((PyTupleObject*)frame->f_code->co_consts)->ob_base->ob_size

	if $argc == 1
		if $arg0 < $e
			set $e = $arg0
		end
	end

	printf "======== co_consts [0, %d) ========\n", $e

	set $i = 0
	while( $i < $e )
		if ($ob = GETITEM(frame->f_code->co_consts, $i)) != 0
			printf "%d\t%d, %d\n\t", $i, $ob->ob_refcnt_split[0], $ob->ob_refcnt_split[1]
			p (PyObject*)$ob
			printf "\t"
			p $ob->ob_type

			printf "\tval = "
			pauto $ob
		else
			printf "%d\tnull\n", $i
		end

		set $i = $i + 1
	end
end
