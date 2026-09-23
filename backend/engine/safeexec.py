"""Restricted-but-real Python environment for untrusted strategy code.

Real quant strategies use classes, dataclasses, math and numpy, so a bare-whitelist
namespace cannot run them. This module instead starts from the full builtins, removes the
names that reach the filesystem, the process table or the interpreter, and installs an
importer limited to computation-only modules.

Honest threat model: this stops accidents and casual misuse, not a determined attacker.
Restricted-exec escapes through attribute traversal are well known. The controls that
actually contain a hostile strategy are the separate process, the import allowlist and the
parent's wall-clock timeout. Production needs container or seccomp isolation.
"""

import builtins

BLOCKED_BUILTINS = {
    "open", "exec", "eval", "compile", "input", "breakpoint", "help",
    "exit", "quit", "globals", "locals", "vars", "dir", "memoryview",
    "__import__", "copyright", "credits", "license",
}

ALLOWED_MODULES = {
    "math", "cmath", "statistics", "random", "decimal", "fractions", "numbers",
    "dataclasses", "typing", "typing_extensions", "enum", "abc",
    "collections", "collections.abc", "itertools", "functools", "operator",
    "heapq", "bisect", "array", "copy", "string", "re", "json", "textwrap",
    "datetime", "time", "uuid", "warnings", "contextlib", "logging",
    "numpy", "numpy.linalg", "numpy.random",
}


def _root(name: str) -> str:
    return name.split(".")[0]


def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0:
        raise ImportError("relative imports are not available to strategies")
    if name not in ALLOWED_MODULES and _root(name) not in ALLOWED_MODULES:
        raise ImportError(
            f"module '{name}' is not available in the strategy sandbox. "
            f"Available: {', '.join(sorted(ALLOWED_MODULES))}"
        )
    return builtins.__import__(name, globals, locals, fromlist, level)


def build_namespace() -> dict:
    safe = {
        name: value
        for name, value in vars(builtins).items()
        if name not in BLOCKED_BUILTINS
    }
    safe["__import__"] = safe_import
    return {"__builtins__": safe, "__name__": "strategy"}
