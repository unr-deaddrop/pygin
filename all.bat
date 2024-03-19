@REM Note that 127.0.0.1 must be used for Redis connections, *not* localhost.
@REM https://stackoverflow.com/questions/11010834/how-to-run-multiple-dos-commands-in-parallel

@REM These are opened minimized so we can still kill them, but they're not
@REM immediately visible. Of course, they'd be visible to a real user, but
@REM that's not *really* the concern here.

@REM Finally, note that this is the preferred way to run the agent when
@REM not bundled using PyInstaller. In short, eventlet doesn't seem
@REM to work when the Celery worker is started programatically, so threading
@REM is used instead. Obviously, this nerfs the efficacy of the program a bit
@REM (the GIL will be gone soon:tm:) but it still works as expected.
start /min "" celery -A src.agent_code.tasks worker -l debug -P eventlet
start /min "" celery -A src.agent_code.tasks beat -l debug
start /min "" python -m src.agent_code.main
start /min "" contribs/redis-windows/redis-server.exe