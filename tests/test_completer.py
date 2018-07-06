import unittest
from prompt_toolkit.document import Document

from itask import ITaskCompleter

from base import new_task_env


class CompleterTests(unittest.TestCase):
    def test_cmds(self):
        with new_task_env() as _task:
            completer = ITaskCompleter(_task, {}, False, False)

            for cmd in ['list', 'add']:
                for prefix in [cmd[:i] for i in range(len(cmd) + 1)]:
                    assert cmd in map(lambda c: c.text,
                                      completer.get_completions(Document(prefix), None)), \
                        f"completing ''{prefix}' must yield command '{cmd}'"

    def test_expanded_tags(self):
        with new_task_env() as _task:
            completer = ITaskCompleter(_task, {}, False, False)

            _task.run('task', 'add', 'task 1', '+tag1', '+tag2')
            _task.run('task', 'add', 'task 1', '+tag3')

            completer._update_cache()

            for tag in ['+tag1', '+tag2', '+tag3']:
                for prefix in [tag[:i] for i in range(len(tag) + 1)]:
                    assert tag in map(lambda c: c.text,
                                      completer.get_completions(Document(prefix), None)), \
                        f"completing '{prefix}' must yield tag '{tag}'"

    def test_indirect_tags(self):
        with new_task_env() as _task:
            completer = ITaskCompleter(_task, {}, True, False)

            _task.run('task', 'add', 'task 1', '+tag1', '+tag2')
            _task.run('task', 'add', 'task 1', '+tag3')

            completer._update_cache()

            for tag in ['+tag1', '+tag2', '+tag3']:
                for prefix in [tag[:i] for i in range(len(tag) + 1)]:
                    compls = [c.text for c in completer.get_completions(Document(prefix), None)]
                    if len(prefix) == 0:
                        assert tag not in compls,\
                            f"completing {prefix} may not yield expanded tags, e.g. '{tag}'"
                        assert '+' in compls
                        assert '-' in compls
                    else:
                        assert tag in compls, \
                            f"completing {prefix} must yield tag {tag}"

    def test_expanded_projects(self):
        with new_task_env() as _task:
            completer = ITaskCompleter(_task, {}, False, False)

            _task.run('add', 'project:proj1', 'task 1')
            _task.run('add', 'task 2', 'proj:proj2')

            completer._update_cache()

            for proj in ['project:proj1', 'project:proj2']:
                for prefix in [proj[:i] for i in range(4, len(proj) + 1)]:
                    assert proj in map(lambda c: c.text,
                                       completer.get_completions(Document(prefix), None)), \
                        f"completing '{prefix}' must yield project '{proj}'"

    def test_indirect_projects(self):
        with new_task_env() as _task:
            completer = ITaskCompleter(_task, {}, False, True)

            _task.run('add', 'project:proj1', 'task 1')
            _task.run('add', 'task 2', 'proj:proj2')

            completer._update_cache()

            for proj in ['project:proj1', 'proj:proj2']:
                for prefix in [proj[:i] for i in range(4, len(proj) + 1)]:
                    compls = [c.text for c in completer.get_completions(Document(prefix), None)]
                    if prefix.find(':') == -1:
                        assert proj not in compls
                        assert 'project:' in compls
                    else:
                        assert proj in compls

    def test_cmd_description(self):
        with new_task_env() as _task:
            completer = ITaskCompleter(_task, {}, False, False)

            def find_completion(cmd):
                matches = [c for c in completer.get_completions(Document(''), None)
                           if c.text == cmd]
                assert len(matches) == 1
                return matches[0]

            assert find_completion('list').display_meta.find('Most details of tasks') != -1
            assert find_completion('calendar').display_meta.find('Shows a calendar,'
                                                                 ' with due tasks marked') != -1
            assert find_completion('commands').display_meta.find('Generates a list of all commands,'
                                                                 ' with behavior details') != -1


if __name__ == '__main__':
    unittest.main()
