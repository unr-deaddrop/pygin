#https://stackoverflow.com/questions/41317653/how-to-create-a-single-file-executable-with-celery-tasks
from src.agent_code.tasks import app

# Pyinstaller-friendly imports (boo)
import src.protocols.dddb_local
import src.protocols.plaintext_local
import src.protocols.plaintext_tcp

# Note that app.worker_main has a helpful error messages that tells you to use
# app.start for anything that isn't the Celery worker.

if __name__ == "__main__":
    app.start(argv=['beat', '--loglevel=debug'])