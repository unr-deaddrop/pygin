start /min "" ./bin/celery_beat.exe
start /min "" ./bin/celery_worker.exe
start /min "" ./bin/main.exe
start /min "" contribs/redis-windows/redis-server.exe