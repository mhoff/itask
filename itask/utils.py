import subprocess

task_binary = 'task'


class TaskError(Exception):
    pass


def task_exec(*args, output=True):
    try:
        params = [task_binary, *args]
        if output:
            subprocess.call(params)
        else:
            subprocess.check_output(params)
    except IOError as e:
        raise TaskError(f"command `{' '.join(params)}` resulted in IOError {e.errno}")
    except subprocess.CalledProcessError as e:
        raise TaskError(f"command `{' '.join(params)}` failed with code {e.returncode}")


def task_get(*args):
    try:
        params = [task_binary, *args]
        return subprocess.check_output([task_binary, *args], stderr=subprocess.STDOUT).decode().strip('\n')
    except IOError as e:
        raise TaskError(f"command `{' '.join(params)}` resulted in IOError {e.errno}")
    except subprocess.CalledProcessError as e:
        raise TaskError(f"command `{' '.join(params)}` failed with code {e.returncode}")


def task_get_lines(*args, filter_empty=True):
    lines = task_get(*args).split('\n')
    if filter_empty:
        lines = filter(lambda l: len(l) > 0, lines)
    return lines
