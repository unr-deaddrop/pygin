#https://stackoverflow.com/questions/41317653/how-to-create-a-single-file-executable-with-celery-tasks
from src.agent_code.tasks import app
import src.agent_code.tasks

# Pyinstaller-friendly imports (boo)
import src.protocols.dddb_local
import src.protocols.plaintext_local
import src.protocols.plaintext_tcp

import src.commands.shell
import src.commands.ping
import src.commands.download_file

# Note that app.worker_main has a helpful error messages that tells you to use
# app.start for anything that isn't the Celery worker.

if __name__ == "__main__":
    # For some reason, neither gevents nor eventlet will work when run 
    # programmatically. From observation, the tasks won't *start* even though
    # they're received by the worker... unless Redis is inaccessible. Then,
    # the tasks will start, and then the worker pool can post the result to Redis.
    #
    # It's an absolute mystery to me why this is, considering the fact that you
    # can run Celery from the command line and it'll work just fine. But so it is.
    # I dug into the Worker implementation at 
    # https://github.com/celery/celery/blob/main/celery/bin/worker.py#L108
    # with no success, so the best we're getting is this thing that basically works.
    #
    # In turn, we're using threads here, which works when compiled to an executable.
    # See https://celery.school/celery-on-windows. In all other cases, continue using
    # the standard prefook pool.
    app.start(argv=['-A', 'src.agent_code.tasks', 'worker', '--loglevel=debug', '--pool=threads', '--concurrency=8'])