# Expose all available commands for * imports. This is particularly useful
# when retrieving metadata for all commands.

from pathlib import Path

import dddb_local


# Get all Python files, don't recurse
paths = Path(__file__).parent.resolve().glob("*.py")

# Construct the avilable modules
__all__ = []
for path in paths:
    if not path.is_file():
        continue

    # Ignore any with leading underscores, including __init__.py
    if path.name.startswith("_"):
        continue

    __all__.append(path.stem)
