def f():
	return 1, 2

def g():
	return 0, *f()

print(g())
