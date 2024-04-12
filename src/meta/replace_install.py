from pathlib import Path
import logging
import re
import sys

from src.meta.agent import PyginInfo

logging.basicConfig(
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
    level=logging.DEBUG,
    format="%(filename)s:%(lineno)d | %(asctime)s | [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    target = Path("Makefile")

    if not target.exists():
        raise RuntimeError("Missing Makefile!")

    with open(target, "rt") as fp:
        data = fp.read()

    image_name = "docker pull unrdeaddrop/pygin:" + PyginInfo.version
    logger.info(f"Writing {image_name=} to Makefile")
    new = re.sub(
        r"^\tdocker pull unrdeaddrop/pygin:(.*)$",
        f"\t{image_name}",
        data,
        flags=re.MULTILINE,
    )

    print(new)

    with open(target, "wt") as fp:
        fp.write(new)
