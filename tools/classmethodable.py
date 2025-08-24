class classmethodable:
	def __init__(self, func):
		self.func = func

	def __get__(self, obj, objtype=None):
		if obj is None:  # called from class
			def wrapper(*args, **kwargs):
				return self.func(objtype, *args, **kwargs)
		else:  # called from instance
			def wrapper(*args, **kwargs):
				return self.func(obj, *args, **kwargs)
		return wrapper


class Demo:
	x = 9
	def __init__(self):
		self.x = 2

	@classmethodable
	def both(caller, *args, **kwargs):
		if isinstance(caller, type):
			print(f"Called from class: {caller} {caller.x}")
		else:
			print(f"Called from instance: {caller} {caller.x}")

if __name__ == "__main__":
	Demo.both()
	Demo().both()
