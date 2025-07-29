import torch
import torch.multiprocessing as mp

def main():
	device = (
		torch.device("cuda")
		if torch.cuda.is_available()
		else torch.device("mps")
		if torch.backends.mps.is_available()
		else torch.device("cpu")
	)
	print(f"Using device: {device}")

	a = torch.tensor([1,2,3], dtype=torch.uint64)
	print(a)

if __name__ == "__main__":
	# mp.set_start_method("fork")
	main()
