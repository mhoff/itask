import subprocess

task_binary = 'task'


def task_exec(*args, output=True):
    params = [task_binary, *args]
    if output:
        subprocess.call(params)
    else:
        subprocess.check_output(params)


def task_get(*args):
    try:
        return subprocess.check_output([task_binary, *args]).decode().strip('\n')
    except IOError as e:
        print(e)


def task_get_lines(*args, filter_empty=True):
    lines = task_get(*args).split('\n')
    if filter_empty:
        lines = filter(lambda l: len(l) > 0, lines)
    return lines
