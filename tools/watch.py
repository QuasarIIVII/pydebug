import sys, io
import parser
from parser import Parser, ByteStream

'''
{'data': [{'data': [b'9', b'int', b'0', b'f0', b'0'], 'name': b'a'},
		  {'data': [b'18', b'int', b'0', b'f0', b'0'], 'name': b'b'},
		  {'data': [b'9', b'int', b'0', b'main', b'2'], 'name': b'x'},
		  {'data': [b'9', b'int', b'0', b'f0', b'2'], 'name': b'x'},
		  {'data': [], 'name': b'x'}],
 'name': b'watch'}
 '''

def show_vars(data):
	scope_str = {
		0: "localsplus",
		1: "locals",
		2: "globals",
		3: "Builtin",
	}

	print(f"======== vars ({len(data)}) ========")
	for a in data:
		v = a['data']
		name = a['name'].decode()
		name_len = max(len(name), 8)

		if not v:
			print(f"{name:<{name_len}}: type= depth= frame= scope=")
			print(' '*name_len + f"  val=N/A", flush=True)
			continue

		# value, type, depth, frame_qualname, scope
		v = [x.decode() for x in v]
		vv, vt, vd, vf, vs = v

		print(f"{name:<{name_len}}: type={vt} depth={vd} frame={vf} scope={scope_str[int(vs)]}")
		print(' '*name_len + f"  val={vv}", flush=True)
	pass

def main():
	bs = ByteStream(sys.stdin.buffer)
	p = Parser(bs)

	while True:
		try:
			while True:
				pair = bs.peek(2)
				if not pair:
					b = bs.read1()  # will raise EOFError if closed
					continue

				if pair == parser.TOK_LP:
					p._consume_token(parser.TOK_LP)
					break
				else:
					b = bs.read1()

			data = p.parse_group()
			if data["name"] == b"watch":
				show_vars(data["data"])
				sys.stdout.flush()

		except EOFError:
			break

if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		pass
