"""
Various routines for generating the agent's metadata.

This covers:
- commands.json, which serves as a reference for the commands this agent
  supports and their arguments
- protocols.json, which exposes the protocols this agent supports and 
  the configuration keys specific to those protocols for this agent
- agent.json, which exposes core agent metadata and configurable
  options for the agent itself
  
These three files are placed in the same folder relative to execution.
It is intended to be executed as `python3 -m src.meta.generate_metadata`
as a standalone script.
"""

from pathlib import Path

COMMAND_FILE = Path("./commands.json")
PROTOCOL_FILE = Path("./protocols.json")
AGENT_FILE = Path("./agent.json")

def generate_command_metadata(filepath_out: Path) -> None:
    raise NotImplementedError

def generate_protocol_metadata(filepath_out: Path) -> None:
    raise NotImplementedError

def generate_agent_metadata(filepath_out: Path) -> None:
    raise NotImplementedError

if __name__ == "__main__":
    pass