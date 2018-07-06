import subprocess
import os
import logging

logger = logging.getLogger('itask')


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
            logging.debug(f"shell: `{' '.join(_args)}`")
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
        lines = [line for line in self.fetch(*args).split('\n') if len(line) > 0]
        logger.debug(f"fetched: [{', '.join(map(repr, lines))}]")
        return lines

    def run(self, *args, show=True):
        def _show(call_args):
            if show:
                subprocess.call(call_args)
            else:
                subprocess.check_output(call_args)
        self._exec(_show, *args)

    def config(self, *args, confirm=None, verbose=None):
        pre_args = []
        for flag, opt in zip([confirm, verbose], ['rc.confirmation', 'rc.verbose']):
            if flag is not None:
                assert isinstance(flag, bool)
                pre_args.append(f"{opt}:{['no', 'yes'][flag]}")
        self.run(*pre_args, "config", *args)
