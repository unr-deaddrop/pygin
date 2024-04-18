"""
Small script to generate many different name-version combinations from Pygin's codebase.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar, Type
from random import randint, choice
import re
import shutil
import subprocess
import zipfile

from src.meta.agent import PyginInfo

# Names taken from Docker's generator at
# https://github.com/moby/moby/blob/master/pkg/namesgenerator/names-generator.go.
#
# The list is no longer maintained, and therefore there may be names in here
# that shouldn't be, but this makes reasonable-sounding packages.
NAMES = [
    "agnesi",
    "albattani",
    "allen",
    "almeida",
    "antonelli",
    "archimedes",
    "ardinghelli",
    "aryabhata",
    "austin",
    "babbage",
    "banach",
    "banzai",
    "bardeen",
    "bartik",
    "bassi",
    "beaver",
    "bell",
    "benz",
    "bhabha",
    "bhaskara",
    "black",
    "blackburn",
    "blackwell",
    "bohr",
    "booth",
    "borg",
    "bose",
    "bouman",
    "boyd",
    "brahmagupta",
    "brattain",
    "brown",
    "buck",
    "burnell",
    "cannon",
    "carson",
    "cartwright",
    "carver",
    "cerf",
    "chandrasekhar",
    "chaplygin",
    "chatelet",
    "chatterjee",
    "chaum",
    "chebyshev",
    "clarke",
    "cohen",
    "colden",
    "cori",
    "cray",
    "curie",
    "curran",
    "darwin",
    "davinci",
    "dewdney",
    "dhawan",
    "diffie",
    "dijkstra",
    "dirac",
    "driscoll",
    "dubinsky",
    "easley",
    "edison",
    "einstein",
    "elbakyan",
    "elgamal",
    "elion",
    "ellis",
    "engelbart",
    "euclid",
    "euler",
    "faraday",
    "feistel",
    "fermat",
    "fermi",
    "feynman",
    "franklin",
    "gagarin",
    "galileo",
    "galois",
    "ganguly",
    "gates",
    "gauss",
    "germain",
    "goldberg",
    "goldstine",
    "goldwasser",
    "golick",
    "goodall",
    "gould",
    "greider",
    "grothendieck",
    "haibt",
    "hamilton",
    "haslett",
    "hawking",
    "heisenberg",
    "hellman",
    "hermann",
    "herschel",
    "hertz",
    "heyrovsky",
    "hodgkin",
    "hofstadter",
    "hoover",
    "hopper",
    "hugle",
    "hypatia",
    "ishizaka",
    "jackson",
    "jang",
    "jemison",
    "jennings",
    "jepsen",
    "johnson",
    "joliot",
    "jones",
    "kalam",
    "kapitsa",
    "kare",
    "keldysh",
    "keller",
    "kepler",
    "khayyam",
    "khorana",
    "kilby",
    "kirch",
    "knuth",
    "kowalevski",
    "lalande",
    "lamarr",
    "lamport",
    "leakey",
    "leavitt",
    "lederberg",
    "lehmann",
    "lewin",
    "lichterman",
    "liskov",
    "lovelace",
    "lumiere",
    "mahavira",
    "margulis",
    "matsumoto",
    "maxwell",
    "mayer",
    "mccarthy",
    "mcclintock",
    "mclaren",
    "mclean",
    "mcnulty",
    "meitner",
    "mendel",
    "mendeleev",
    "meninsky",
    "merkle",
    "mestorf",
    "mirzakhani",
    "montalcini",
    "moore",
    "morse",
    "moser",
    "murdock",
    "napier",
    "nash",
    "neumann",
    "newton",
    "nightingale",
    "nobel",
    "noether",
    "northcutt",
    "noyce",
    "panini",
    "pare",
    "pascal",
    "pasteur",
    "payne",
    "perlman",
    "pike",
    "poincare",
    "poitras",
    "proskuriakova",
    "ptolemy",
    "raman",
    "ramanujan",
    "rhodes",
    "ride",
    "ritchie",
    "robinson",
    "roentgen",
    "rosalind",
    "rubin",
    "saha",
    "sammet",
    "sanderson",
    "satoshi",
    "shamir",
    "shannon",
    "shaw",
    "shirley",
    "shockley",
    "shtern",
    "sinoussi",
    "snyder",
    "solomon",
    "spence",
    "stonebraker",
    "sutherland",
    "swanson",
    "swartz",
    "swirles",
    "taussig",
    "tesla",
    "tharp",
    "thompson",
    "torvalds",
    "tu",
    "turing",
    "varahamihira",
    "vaughan",
    "villani",
    "visvesvaraya",
    "volhard",
    "wescoff",
    "wilbur",
    "wiles",
    "williams",
    "williamson",
    "wilson",
    "wing",
    "wozniak",
    "wright",
    "wu",
    "yalow",
    "yonath",
    "zhukovsky",
]


# Tuples defining the inclusive ranges for the major-minor-patch version numbering.
class VersionRange:
    major: ClassVar[tuple[int, int]] = (0, 3)
    minor: ClassVar[tuple[int, int]] = (0, 9)
    patch: ClassVar[tuple[int, int]] = (0, 14)

    @classmethod
    def get_random_version(cls) -> str:
        return f"{randint(cls.major[0], cls.major[1])}.{randint(cls.minor[0], cls.minor[1])}.{randint(cls.patch[0], cls.patch[1])}"


# The number of packages to generate.
PACKAGES = 10

# Where to generate these packages.
OUTPUT_DIR = Path("./fake-builds")


def make_random_build_name(range: Type[VersionRange], nameset: list[str]) -> str:
    return f"{choice(nameset)}-{range.get_random_version()}"


if __name__ == "__main__":
    # Invoke the bundle script to generate the /build directory and
    # pygin-build.zip in this directory.
    subprocess.run(["./bundle.sh"])

    # Unzip pygin-build.zip to a temporary directory.
    pygin_build_name = f"pygin-build-{PyginInfo.version}.zip"
    if not Path(pygin_build_name).exists():
        raise RuntimeError("Pygin build missing!")
    temp_dir = TemporaryDirectory()
    temp_dir_path = Path(temp_dir.name).resolve()

    with zipfile.ZipFile(pygin_build_name, "r") as zip_ref:
        zip_ref.extractall(temp_dir_path)

    # Create our output directory
    out_dir = OUTPUT_DIR.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Rinse and repeat until done.
    for _ in range(PACKAGES):
        # Generate our new package name/version number.
        package_name = choice(NAMES)
        version = VersionRange.get_random_version()

        # Open the agent definition file and look for the name and version string,
        # then use regex replace.
        with open(temp_dir_path / Path("src/meta/agent.py"), "rt") as fp:
            data = fp.read()

        data = re.sub(
            r"name: str = \"(.*)\"$",
            f'name: str = "{package_name}"',
            data,
            flags=re.MULTILINE,
        )
        data = re.sub(
            r"version: str = \"(.*)\"$",
            f'version: str = "{version}"',
            data,
            flags=re.MULTILINE,
        )

        # Write agent.py back.
        with open(temp_dir_path / Path("src/meta/agent.py"), "wt+") as fp:
            fp.write(data)

        # Rezip that folder, copy out.
        shutil.make_archive(
            str(OUTPUT_DIR / Path(f"{package_name}-{version}")), "zip", temp_dir_path
        )

    # Blow up the temporary directory
    temp_dir.cleanup()
