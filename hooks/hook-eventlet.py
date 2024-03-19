#https://stackoverflow.com/questions/68910753/celery-and-pyinstaller
#https://stackoverflow.com/questions/67023208/run-celery-worker-with-a-compiled-python-module-compiled-using-pyinstaller
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('eventlet')