import sys

# ANSI color helper

ESC = '\033['      # or '\x1b['
RESET = ESC + '0m'

def color_for(value, vmin, vmax):
    """
    Map 'value' in [vmin, vmax] to an RGB color along the path:
    red -> yellow -> green -> cyan -> blue.
    Returns (r, g, b) each in 0–255.
    """
    # Clamp and normalize
    if value < vmin: value = vmin
    if value > vmax: value = vmax
    span = vmax - vmin if vmax != vmin else 1.0
    x = (value - vmin) / span  # normalized [0,1]

    # Four segments of equal length 0.25
    if x <= 0.25:
        # Red -> Yellow
        f = x / 0.25
        r, g, b = 255, int(255 * f), 0
    elif x <= 0.50:
        # Yellow -> Green
        f = (x - 0.25) / 0.25
        r, g, b = int(255 * (1 - f)), 255, 0
    elif x <= 0.75:
        # Green -> Cyan
        f = (x - 0.50) / 0.25
        r, g, b = 0, 255, int(255 * f)
    else:
        # Cyan -> Blue
        f = (x - 0.75) / 0.25
        r, g, b = 0, int(255 * (1 - f)), 255

    return r, g, b

def bg_color_escape(r, g, b):
    """Return ANSI escape for a 24-bit background color."""
    return f"{ESC}48;2;{r};{g};{b}m"  # 48;2;<r>;<g>;<b>

def f(it):
	#if len(data) < 4:
	#	print("Need at least 4 numbers (h w m M)")
	#	return

	# find start indicator : >>>DATA
	while True:
		line = next(it)
		if line.startswith(">>>DATA"):
			break

	h = int(next(it))
	w = int(next(it))
	m = float(next(it))
	M = float(next(it))

	matrix = []
	for _ in range(h):
		row = [float(next(it)) for _ in range(w)]
		matrix.append(row)

	# Print heatmap
	for row in matrix:
		line = ""
		for v in row:
			code = color_for(v, m, M)
			r, g, b = code
			line += f"{bg_color_escape(r, g, b)} {RESET}"
		print(line)

def main():
	data = sys.stdin.read().strip().split()
	it = iter(data)

	while True:
		try:
			f(it)
			print(flush=True)
		except StopIteration:
			break
		except Exception as e:
			print(f"Error processing input: {e}", file=sys.stderr)
			return

if __name__ == "__main__":
	main()

