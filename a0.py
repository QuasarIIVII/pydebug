import torch
from torchvision import datasets, transforms
import torch.multiprocessing as mp
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import matplotlib.pyplot as plt
import sys

activations = {}
def get_activation(name):
	def hook(model, i, o):
		activations[name] = o.detach()
	return hook

class SimpleNet(nn.Module):
	def __init__(self):
		super(SimpleNet, self).__init__()
		self.fc1 = nn.Linear(28*28, 128)
		self.fc2 = nn.Linear(128, 10)

	def forward(self, x):
		x = x.view(-1, 28*28)	   # flatten
		x = F.relu(self.fc1(x))	 # hidden layer
		x = self.fc2(x)			 # output logits
		return F.log_softmax(x, dim=1)

def train(params, epoch):
	device, model, train_loader, optimizer, criterion = params
	model.train()
	for batch_idx, (data, target) in enumerate(train_loader):
		data, target = data.to(device), target.to(device)
		optimizer.zero_grad()
		output = model(data)
		loss = criterion(output, target)
		loss.backward()
		optimizer.step()
		if batch_idx % 100 == 0:
			print(f"Train Epoch: {epoch} [{batch_idx*len(data)}/{len(train_loader.dataset)}]  Loss: {loss.item():.6f}")

def test(params):
	device, model, test_loader, criterion = params
	model.eval()
	test_loss = 0
	correct   = 0
	with torch.no_grad():
		for data, target in test_loader:
			data, target = data.to(device), target.to(device)
			output = model(data)
			test_loss += criterion(output, target).item()
			pred = output.argmax(dim=1)
			correct += pred.eq(target).sum().item()

	test_loss /= len(test_loader.dataset)
	accuracy = 100. * correct / len(test_loader.dataset)
	print(f"\nTest set: Average loss: {test_loss:.4f}, Accuracy: {correct}/{len(test_loader.dataset)} ({accuracy:.2f}%)\n")

# Model definition
class DNN(nn.Module):
	def __init__(self):
		super().__init__()
		self.fc1 = nn.Linear(28*28, 256)
		self.fc2 = nn.Linear(256, 128)
		# self.fc2 = nn.Linear(256, 10)
		self.fc3 = nn.Linear(128, 10)

	def forward(self, x):
		x = x.view(-1, 28*28)	# flatten
		x = F.relu(self.fc1(x))
		x = F.relu(self.fc2(x))
		x = F.relu(self.fc3(x))
		return F.log_softmax(x, dim=1)
		# return self.fc3(x)

def f(tensor):
	s = ">>>DATA\n"
	s += str(tensor.shape[0]) + ' ' + str(tensor.shape[1]) \
	+ ' ' + str(tensor.min().item()) + ' ' + str(tensor.mean().item()) + '\n'
	for v in tensor:
		for a in v:
			s += ' ' + str(a.item())
		s += '\n'
	return s

def main():
	# Choose cuda if available,
	# else mps, else cpu
	device = (
		torch.device("cuda")
		if torch.cuda.is_available()
		else torch.device("mps")
		if torch.backends.mps.is_available()
		else torch.device("cpu")
	)
	print(f"Using device: {device}")

	# Normalize to [0,1] then center to mean=0.1307, std=0.3081 of MNIST
	transform = transforms.Compose([
		transforms.ToTensor(),
		transforms.Normalize((0.1307,), (0.3081,))
	])

	train_dataset = datasets.MNIST(
		root="data",
		train=True,
		download=True,
		transform=transform
	)

	test_dataset = datasets.MNIST(
		root="data",
		train=False,
		download=True,
		transform=transform
	)

	train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
	test_loader  = DataLoader(test_dataset,  batch_size=1000, shuffle=False)

	model = DNN().to(device)
	optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.5)
	criterion = nn.NLLLoss()

	weight_norms = []
	for epoch in range(1, 2):
		train([device, model, train_loader, optimizer, criterion], epoch)
		test([device, model, test_loader, criterion])

		# print(model.fc3.weight.shape)
		# print(model.fc1.weight)
		norm = model.fc1.weight.norm().item()
		weight_norms.append(norm)
		print(f"Epoch {epoch}, Weight Norm: {norm:.4f}")

	""" debug """
	from torchvision.utils import make_grid

	hook_handle = [
		model.fc1.register_forward_hook(get_activation('fc1')),
		model.fc2.register_forward_hook(get_activation('fc2')),
		model.fc3.register_forward_hook(get_activation('fc3'))
	]

	revcv = [[] for _ in range(10)]
	for i in range(test_dataset.targets.shape[0]):
		revcv[test_dataset.targets[i]].append(i)

	bnum = revcv[5][2]
	model_in = next(iter(test_loader))[0]
	data = model_in.to(device)
	model_out = model(data)
	print(model_out[2].shape)

	feat = model_in[bnum].view(1,1,28,28)
	grid = make_grid(feat, nrow=4, normalize=True, scale_each=True)
	print(f(grid[0]), file=sys.stderr)

	print(activations['fc1'].shape)
	feat = activations['fc1'][bnum].view(1,1,16,16)
	grid = make_grid(feat, nrow=4, normalize=True, scale_each=True)
	print(f(grid[0]), file=sys.stderr)

	feat = activations['fc2'][bnum].view(1,1,8,16)
	grid = make_grid(feat, nrow=4, normalize=True, scale_each=True)
	print(f(grid[0]), file=sys.stderr)

	feat = activations['fc3'][bnum].view(1,1,1,10)
	grid = make_grid(feat, nrow=4, normalize=True, scale_each=True)
	print(f(grid[0]), file=sys.stderr)

	print(model_out.shape)
	feat = model_out[bnum].view(1,1,1,10)
	grid = make_grid(feat, nrow=4, normalize=True, scale_each=True)
	print(f(grid[0]), file=sys.stderr)

	for handle in hook_handle:
		handle.remove()

if __name__ == "__main__":
	mp.set_start_method("fork")
	main()
