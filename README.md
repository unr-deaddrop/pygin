Pygin is the basic implementation of a DeadDrop agent. 

Much of the architecture of an agent is derived from Mythic's [example container for agent/payload development](https://github.com/MythicMeta/ExampleContainers) and [documentation](https://docs.mythic-c2.net/customizing/payload-type-development). These resources have been used to provide the foresight needed to figure out what an agent *needs* and a general idea of how to structure it, but the actual implementation has been done from scratch (naturally, with the side effect of reduced code quality).

At the absolute highest level, Pygin is a collection of five things required to build unique payloads:
- A Dockerfile, which builds an instance of the agent suitable for execution on Linux
- A set of commands, including their (Python) code and the metadata associated with each command
- If provided, a result renderer for certain commands (equivalent to Mythic's browser scripting) that takes in a command result and produces a valid HTML element
- The main codebase
- Any additional metadata required for the agent to function after bundling

Agents can be run "as-is" from this codebase with a fair degree of manual effort, but they can also be bundled using a Docker container if needed.

When an agent is installed, you can run `insert-thing-here` to automatically generate human-readable metadata from all the avilable 