"""
Lightweight shell tool. No external deps.
Runs a command with a timeout and a basic blocklist for catastrophic patterns.
This is NOT a sandbox -- it runs as your user. It just stops the obvious own-goals.
"""

import subprocess

BLOCKLIST_SUBSTRINGS = [
    "rm -rf /",
    "rm -rf /*",
    ":(){:|:&};:",
    "mkfs",
    "dd if=",
    "> /dev/sd",
    "chmod -R 777 /",
]

DEFAULT_TIMEOUT = 30


def _check_command(command):
    lowered = command.lower()
    for pattern in BLOCKLIST_SUBSTRINGS:
        if pattern in lowered:
            raise ValueError(f"Command blocked: contains disallowed pattern '{pattern}'")


def run(command, cwd=None, timeout=DEFAULT_TIMEOUT, **params):
    _check_command(command)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout}s: {command}")

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
