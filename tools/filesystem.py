"""
Lightweight filesystem tool. No external deps.
All paths are resolved and must fall under one of ALLOWED_ROOTS.
"""

import os
import shutil

ALLOWED_ROOTS = [
    os.path.expanduser("~/agent"),
    "/mnt/agentdata",
]


def _check_path(path):
    resolved = os.path.realpath(os.path.expanduser(path))
    for root in ALLOWED_ROOTS:
        root_resolved = os.path.realpath(root)
        if resolved == root_resolved or resolved.startswith(root_resolved + os.sep):
            return resolved
    raise ValueError("Path resolves outside allowed roots: " + path)


def read_file(path, **params):
    resolved = _check_path(path)
    with open(resolved, "r") as f:
        return f.read()


def write_file(path, content, **params):
    resolved = _check_path(path)
    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    tmp = resolved + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, resolved)
    return "wrote " + str(len(content)) + " bytes to " + path


def append_file(path, content, **params):
    resolved = _check_path(path)
    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    with open(resolved, "a") as f:
        f.write(content)
    return "appended " + str(len(content)) + " bytes to " + path


def list_dir(path=".", **params):
    resolved = _check_path(path)
    return sorted(os.listdir(resolved))


def delete_file(path, **params):
    resolved = _check_path(path)
    if os.path.isdir(resolved):
        shutil.rmtree(resolved)
    else:
        os.remove(resolved)
    return "deleted " + path


def make_dir(path, **params):
    resolved = _check_path(path)
    os.makedirs(resolved, exist_ok=True)
    return "created " + path


def file_exists(path, **params):
    try:
        resolved = _check_path(path)
    except ValueError:
        return False
    return os.path.exists(resolved)
