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
	print(f"Using device: {device}", flush=True)

	a = torch.tensor([[1,2,3], [7,8,9]], dtype=torch.uint64).to(device)
	print(a, flush=True)
	li = a.tolist()
	print(li, flush=True)

if __name__ == "__main__":
	# mp.set_start_method("fork")
	main()
