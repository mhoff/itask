import subprocess
import os


class TaskError(Exception):
    pass


class TaskHelper:
    def __init__(self, bin_path='task', rc_path=None):
        self._task_base_args = [bin_path]
        if rc_path is not None:
            self._task_base_args.append(f'rc:{os.path.expanduser(rc_path)}')

    def _exec(self, func, *args):
        try:
            _args = [*self._task_base_args, *args]
            return func(_args)
        except IOError as e:
            raise TaskError(f"command `{' '.join(_args)}` resulted in IOError {e.errno}")
        except subprocess.CalledProcessError as e:
            raise TaskError(f"command `{' '.join(_args)}` failed with code {e.returncode}")

    def fetch(self, *args):
        def _fetch(call_args):
            return subprocess.check_output(call_args, stderr=subprocess.STDOUT).decode().strip('\n')
        return self._exec(_fetch, *args)

    def fetch_lines(self, *args):
        return filter(lambda line: len(line) > 0, self.fetch(*args).split('\n'))

    def run(self, *args, show=True):
        def _show(call_args):
            if show:
                subprocess.call(call_args)
            else:
                subprocess.check_output(call_args)
        self._exec(_show, *args)
