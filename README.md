# What is PyDebug?
PyDebug is a hands-on playground for debugging **CPython** and **PyTorch** with GDB.  
It ships:

- A Conda recipe that builds a **debug-friendly CPython** (symbols, assertions, no optimizations).
- A rich **GDB extension** (`.gdbinit.py`) with commands to inspect Python objects, frames, bytecode, and PyTorch tensors.
- Minimal **test programs** (Python + C++20) you can run under GDB.
- Small **CLI helpers** (color/highlight/visualize outputs).

# Prerequisite
- Linux x64 system
- Python [build dependencies](https://devguide.python.org/getting-started/setup-building/#build-dependencies)
- Mamba - [Installation guide](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html)
  - You may also use [Micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html#) instead.
  - Conda environment have not been tested.

# Quick Start
## Install conda-build

You'll need `conda-build` to install custom-built python to your Mamba environment.<br>
You can install it by running the following commands:
```bash
mamba activate base
mamba install conda-build -y
```
> **Note**<br>
> If you are using Micromamba, replace `mamba` with `micromamba` throughout the instructions.

> **Warning**<br>
> Make sure you are in the `base` environment or you will get an error when creating a new environment later.

## Clone the Repository
```bash
git clone https://github.com/QuasarIIVII/pydebug
cd pydebug
git submodule update --init --recursive
```

## Build a Custom Python with Debugging Information
You can adjust the compilation flags (e.g., `CFLAGS`) in `cenv/meta.yaml` as needed.
```bash
cd cenv
conda build .
cd ..
```
> **Note**<br>
> You may change the python version by running `git switch <version>` in the `cenv/cpython` directory.

> **Note**<br>
> The Built package will be located at:<br>
> `$MAMBA_ROOT_PREFIX/conda-bld/linux-64/python-3.12-o0_0.conda`.

## Create a fresh environment with your custom Python
Deactivate your current environment, then create and activate a new one using the custom Python build.<br>
Replace `<env_name>` with your desired environment name.
```bash
mamba deactivate
mamba create -n <env_name> python=3.12=o0_0 -c local -y
mamba activate <env_name>
```

# File Structure
Path: `/` (repo root)

| Path                                      | Explanation |
|-------------------------------------------|-------------|
| [`bps/`](/docs/bps/README.md)             | Saved Python bytecode breakpoints. |
| [`cenv/`](/docs/cenv/README.md)           | Conda recipe to build a debug-friendly CPython. |
| [`docs/`](/docs/docs/README.md)           | Detailed documentation. |
| [`nvcc_test/`](/docs/nvcc_test/README.md) | CUDA smoke tests & a tiny output highlighter. |
| [`test_src/`](/docs/test_src/README.md)   | Minimal programs used during CPython/PyTorch debugging. |
| [`tools/`](/docs/tools/README.md)         | Debugging helpers. |
| `.gdbinit`                                | Loads the Python GDB extensions from `.gdbinit.py`. |
| `.gdbinit.py`                             | Main GDB extension module. |
| `README.md`                               | This file. |
