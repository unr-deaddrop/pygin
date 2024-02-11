"""
Centralized logging module.

This builds on Python's built-in logging module and extends it to allow providing
additional DeadDrop-specific information inline with log messages. The resulting
messages can then be converted directly into DeadDrop's message format.

TODO: For some platforms, it's not *really* feasible to just keep sending one
full messages for one full log. Making this an independent module should make
it significantly easier to bundle logs together, since we can redirect all logs
to some coherent database and regularly check to see if we have enough logs to
force an export.
"""
