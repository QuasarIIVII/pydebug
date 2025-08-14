def f(x, y):
	return [x, y], [y, x, 2]

a, b = 3, 8
a, b = f(a, b)
print(a, b)
