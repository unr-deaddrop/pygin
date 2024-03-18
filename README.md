Pygin is the basic implementation of a DeadDrop agent. 

This includes two Windows executables:
- A modified version of [Empyrean](https://github.com/addi00000/empyrean). Please see contribs/empyrean/LICENSE for more details.
- The distributed [Windows port of Redis Server](https://github.com/zkteco-home/redis-windows). Please see contribs/redis-windows/LICENSE for more details.

To generate a new "build" of the agent that can be installed into a new DeadDrop installation, simply run `./bundle.sh`.

On Windows machines, run `all.bat` to start the agent. On Linux machines, use
`docker compose up` instead to start the agent containerized.

Note that Empyrean is Windows-only, and Redis is natively compiled for Linux,
so no elements in `contribs` are used on Linux installations of Pygin.