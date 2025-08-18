# Minimal python programs for CPython debugging

## File Structure
Path: `/test_src`

| Path             | Explanation |
|------------------|-------------|
| `CMakeLists.txt` | CMake configuration file for building the test C++ programs. |
| `*.py`           | Target programs for python gdb-debugging. |
| `pipe.cpp`       | Test C++ program that spawns gdb and controls it via pipes. |

### Python Script Details

| Path                                 | Explanation |
|--------------------------------------|-------------|
| [`func_ret_complex.py`](/test_src/func_ret_complex.py)       | Python function returning two list objects. |
| [`func_ret_simple.py`](/test_src/func_ret_simple.py)         | Python function returning a single long object. |
| [`mk_tensor.py`](/test_src/mk_tensor.py)                     | Python script to create a torch tensor on a available device. |
| [`model.py`](/test_src/model.py)                             | Python script to create a simple DNN model. |
| [`model_dbg.py`](/test_src/model_dbg.py)                     | Python script to create a simple DNN model with debugging hooks. |
| [`tensor2list_complex.py`](/test_src/tensor2list_complex.py) | Python script to create a torch tensor from a 2d list and convert it back to a list. | 
| [`tensor2list_simple.py`](/test_src/tensor2list_simple.py)   | Python script to create a torch tensor from a 1d list and convert it back to a list. |
