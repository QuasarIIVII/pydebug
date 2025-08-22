x = 9

class C: # *_NAME
	print("class C:", x, flush=True)
	x = 123
	print("class C:", x, flush=True)

def f0(a): # *_FAST
	b = a*2
	print("func f0:", a, b, flush=True)

def f1():
	a = []
	for i in range(2):
		a.append(x)
	print("func f1:", a, flush=True)

def f2():
	x = 8
	def g():
		return x+1
	y = g()
	print("func f2:", y, flush=True)

def main():
	f0(9)
	f1()
	f2()

if __name__ == "__main__":
	main()
