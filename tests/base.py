import os
import tempfile
import contextlib

from itask import task


@contextlib.contextmanager
def new_task_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        rc_overrides = {
            'data.location': os.path.abspath(tmp_dir),
            'confirmation': 'no',
        }

        task_helper = task.TaskHelper('task', rc_path=os.path.join(tmp_dir, 'taskrc'),
                                      rc_overrides=rc_overrides, test_mode=True)

        task_helper.run()

        yield task_helper
