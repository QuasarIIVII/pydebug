# Conda recipe for debug-friendly CPython
This directory contains a Conda recipe for building a debug-friendly version of CPython, which contains additional debugging symbols and macro definitions. This is useful for debugging CPython itself or for debugging Python applications with enhanced visibility into the Python runtime.

## File Structure
Path: `/cenv`

| Path        | Explanation |
|-------------|-------------|
| `cpython/`  | [CPython](https://github.com/python/cpython) Git submodule. |
| `build.sh`  | Configures and installs CPython into `${PREFIX}`. |
| `meta.yaml` | Conda recipe with build dependencies. Source is the `cenv/cpython` submodule. |

### Details
- **`build.sh`**
This script configures the CPython build with debug flags and installs it into the Conda environment's prefix directory `${PREFIX}`. It sets the `CFLAGS` and `LDFLAGS` to include debug symbols and disables optimizations for easier debugging.<br>
Default debug flags are:<br>
`CFLAGS="-g3 -O0 -gdwarf-2"`<br>
`LDFLAGS="-g -rdynamic"`

- **`meta.yaml`**
This file defines the Conda package metadata, including the build requirements and dependencies.

## See Also
- [Quick Start Guide](/docs/cenv/README.md)
