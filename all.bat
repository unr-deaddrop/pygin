@REM Note that 127.0.0.1 must be used for Redis connections, *not* localhost.
@REM https://stackoverflow.com/questions/11010834/how-to-run-multiple-dos-commands-in-parallel

@REM These are opened minimized so we can still kill them, but they're not
@REM immediately visible. Of course, they'd be visible to a real user, but
@REM that's not *really* the concern here
start /min "" celery -A src.agent_code.tasks worker --loglevel=debug --pool=threads --concurrency=16
start /min "" celery -A src.agent_code.tasks beat --loglevel=debug
start /min "" python -m src.agent_code.main
start /min "" contribs/redis-windows/redis-server.exe