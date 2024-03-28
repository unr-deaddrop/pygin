from pathlib import Path
import re

from src.meta.agent import PyginInfo

if __name__ == "__main__":
    target = Path("Makefile")
    
    if not target.exists():
        raise RuntimeError("Missing Makefile!")
    
    with open(target, "rt") as fp:
        data = fp.read()
        
    new = re.sub(r"docker pull unrdeaddrop/pygin:.*$", "docker pull unrdeaddrop/pygin:"+PyginInfo.get_version(), data)
    
    with open(target, "wt") as fp:
        fp.write(new)

    