import contextlib
import os


@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull):
            yield

