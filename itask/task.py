import subprocess
import os
import logging

logger = logging.getLogger('itask')


class TaskError(Exception):
    pass


class TaskHelper:
    def __init__(self, bin_path='task', rc_path=None, rc_overrides=None, test_mode=False):
        self._task_base_args = [bin_path]
        if rc_path is not None:
            self._task_base_args.append(f'rc:{os.path.expanduser(rc_path)}')
        if rc_overrides:
            self._task_base_args.extend([
                f'rc.{name}:{value}' for name, value in rc_overrides.items()
            ])
        self._test_mode = test_mode

    @staticmethod
    def _check_output(args):
        return subprocess.check_output(args, stderr=subprocess.STDOUT).decode().strip('\n')

    @staticmethod
    def _call(args):
        return subprocess.call(args, stderr=subprocess.STDOUT)

    def _exec(self, func, *args):
        try:
            _args = [*self._task_base_args, *args]
            logging.debug(f"shell: `{' '.join(_args)}`")
            return func(_args)
        except IOError as e:
            raise TaskError(f"command `{' '.join(_args)}` resulted in IOError {e.errno}: {e}")
        except subprocess.CalledProcessError as e:
            if e.returncode not in [1, 2]:
                raise TaskError(f"command `{' '.join(_args)}` failed with code {e.returncode}: {e}")
            return e.output.decode().strip('\n')

    def fetch(self, *args):
        return self._exec(self._check_output, *args)

    def fetch_lines(self, *args):
        lines = [line for line in self.fetch(*args).split('\n') if len(line) > 0]
        logger.debug(f"fetched: [{', '.join(map(repr, lines))}]")
        return lines

    def run(self, *args, show=True):
        _show = self._call if show and not self._test_mode else self._check_output
        return self._exec(_show, *args)

    def config(self, *args, confirm=None, verbose=None):
        pre_args = []
        for flag, opt in zip([confirm, verbose], ['rc.confirmation', 'rc.verbose']):
            if flag is not None:
                assert isinstance(flag, bool)
                pre_args.append(f"{opt}:{['no', 'yes'][flag]}")
        return self.run(*pre_args, "config", *args)
