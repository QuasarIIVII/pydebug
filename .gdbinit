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
	p (char*)((PyASCIIObject*)$arg0 + 1)
end

define pobj
	p *(($arg0*)$arg1)
end

define qi
	set $e = 8
	if $argc == 1
		set $e = $arg0
	end

	printf "======== instr [-1, %d) ========\n", $e

	set $i = -1
	while( $i < $e )
		printf "%d\t%-28s%d\n", _PyEval_EvalFrameDefault::next_instr[$i].op.code, q_decode_opcode[_PyEval_EvalFrameDefault::next_instr[$i].op.code], _PyEval_EvalFrameDefault::next_instr[$i].op.arg
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
		if stack_pointer[-$i] != 0
			printf "-%d\t%d, %d\n\t", $i, stack_pointer[-$i]->ob_refcnt_split[0], stack_pointer[-$i]->ob_refcnt_split[1]
			p stack_pointer[-$i]->ob_type
		else
			printf "-%d\tnull\n", $i
		end
		set $i = $i + 1
	end
end
