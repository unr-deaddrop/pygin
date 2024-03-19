@REM https://stackoverflow.com/questions/32093559/exe-file-created-by-pyinstaller-not-find-self-defined-modules-while-running
@REM In short, tasks and celery_beat 
start /min "" pyinstaller --onefile src/agent_code/celery_beat.py --additional-hooks-dir=hooks
start /min "" pyinstaller --onefile src/agent_code/celery_worker.py --additional-hooks-dir=hooks --path=src/commands --path=src/protocols
start /min "" pyinstaller --onefile src/agent_code/main.py --additional-hooks-dir=hooks