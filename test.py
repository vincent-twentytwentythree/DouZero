import torch

# Sample tensor
x = torch.tensor([1, 3, 2])

# Get top-2 values and indices along dim=1 (row-wise)
values, indices = torch.topk(x, k=2, dim=0)
print("Values:\n", values)
print("Indices:\n", indices)
