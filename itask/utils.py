import contextlib
import os


@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull):
            yield


class ObjectDecorator(object):
    def __init__(self):
        self._func = None

    def __call__(self, *args, **kwargs):
        if self._func is None:
            assert len(args) == 1 and len(kwargs) == 0
            self._func = args[0]
            return self
        else:
            return self._func(*args, **kwargs)

    def __get__(self, *args, **kwargs):
        # update func reference to method object
        self._func = self._func.__get__(*args, **kwargs)
        return self
