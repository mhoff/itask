import argparse
import shlex
import prompt_toolkit
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.completion import Completer, Completion

from itask.utils import task_exec, task_get, task_get_lines, TaskError

if prompt_toolkit.__version__ >= '2.0.0':
    from prompt_toolkit import PromptSession, print_formatted_text
else:
    print_formatted_text = print


class ITaskCompleter(Completer):
    def __init__(self, macros, indirect_tags, indirect_projects):
        self._macros = macros
        self._indirect_tags = indirect_tags
        self._indirect_projects = indirect_projects

    def get_completions(self, document, complete_event):
        word = document.get_word_under_cursor(WORD=True)

        def make_completion(text, display=None, display_meta=None, append_whitespace=False):
            if display is None:
                display = text
            if append_whitespace:
                text = f'{text} '
            return Completion(text, display=display, display_meta=display_meta, start_position=-len(word))

        def match(completion):
            return completion.text.startswith(word)

        yield from filter(match, [
            make_completion('add', display_meta='add task'),
            make_completion('list', display_meta='list tasks'),
            make_completion('info', display='info [ID...]', display_meta='show tasks\' details'),
            make_completion('delete', display='delete [ID...]', display_meta='delete tasks')
        ])

        yield from filter(match, (make_completion(k) for k in self._macros.keys()))

        tags = filter(lambda t: not all(c.isupper() for c in t), task_get_lines("_tags"))
        for tag_prefix, label in [('+', 'positive'), ('-', 'negative')]:
            assert len(tag_prefix) == 1
            if word.startswith(tag_prefix) or not self._indirect_tags:
                yield from filter(match, (make_completion(f"{tag_prefix}{tag}") for tag in tags))
            elif len(word) == 0:
                yield from filter(match, ([make_completion(tag_prefix, display=f'{tag_prefix}...',
                                                           display_meta=f'{label} tag selector')]))

        projects = task_get_lines("_projects")

        pref_match = [f'{keyword}' for keyword in [f'{pref}:' for pref in ['pro', 'proj', 'proje', 'projec', 'project']]
                      if word.startswith(keyword)]
        if pref_match:
            yield from filter(match, (make_completion(f"{pref_match[0]}{project}") for project in projects))
        elif self._indirect_projects:
            yield from filter(match, [make_completion("project:", display="project:...",
                                                      display_meta="assign task to project")])
        else:
            yield from filter(match, (make_completion(f"project:{project}") for project in projects))


class ITask(object):
    @staticmethod
    def main():
        parser = argparse.ArgumentParser()

        def add_bool_argument(parser, opt, default):
            dest = opt[2:].replace('-', '_')
            parser.add_argument(opt, dest=dest, action='store_true')
            parser.add_argument(f'{opt[:2]}no-{opt[2:]}', dest=dest, action='store_false')
            parser.set_defaults(**{dest: default})

        parser.add_argument("--inbox-tag", type=str, default="inbox")
        parser.add_argument("--macro-prefix", type=str, default="%")
        add_bool_argument(parser, '--complete-while-typing', default=True)
        add_bool_argument(parser, '--complete-indirect-tags', default=True)
        add_bool_argument(parser, '--complete-indirect-projects', default=True)
        add_bool_argument(parser, '--complete-show-meta-always', default=True)

        return ITask(parser.parse_args()).loop()

    @staticmethod
    def error(msg):
        print_formatted_text(f">>> [ERROR] {msg}")

    def __init__(self, cl_args):
        self._macros = {f"{cl_args.macro_prefix}{k}": v for k, v in {
            'inbox-add': self.macro_inbox_add,
            'inbox-review': self.macro_inbox_review,
            'add': self.macro_add,
            'iter': self.macro_iter,
            'edit': self.macro_edit,
        }.items()}

        self._completer = ITaskCompleter(self._macros,
                                         indirect_tags=cl_args.complete_indirect_tags,
                                         indirect_projects=cl_args.complete_indirect_projects)

        # TODO persist history
        if prompt_toolkit.__version__ >= '2.0.0':
            # TODO verify display_completions_in_columns does work
            self._prompt_session = PromptSession(completer=self._completer,
                                                 display_completions_in_columns=self._cl_args.complete_show_meta_always,
                                                 complete_while_typing=cl_args.complete_while_typing)
        else:
            self._history = InMemoryHistory()

        self._cl_args = cl_args
        self._pos_inbox_tag = f"+{cl_args.inbox_tag}"
        self._neg_inbox_tag = f"-{cl_args.inbox_tag}"

    def prompt(self, message, default=""):
        if prompt_toolkit.__version__ >= '2.0.0':
            return shlex.split(self._prompt_session.prompt(message, default))
        else:
            return shlex.split(prompt(message, default=default, completer=self._completer,
                                      history=self._history,
                                      display_completions_in_columns=self._cl_args.complete_show_meta_always,
                                      complete_while_typing=self._cl_args.complete_while_typing))

    def macro_add(self, *args, pre_report="list"):
        task_exec(*args, pre_report)
        cmds = ("add", *args)
        try:
            while True:
                inp = self.prompt("%add task {}> ".format(' '.join(cmds)))
                if len(inp) == 0:
                    self.error("empty input")
                    continue
                task_exec(*cmds, *inp)
        except EOFError:
            print("--- closing inbox ---")

    def macro_iter(self, *args, pre_report="list", per_report="information", post_callback=None):
        tids = task_get_lines(*args, "_ids")
        if not tids:
            return
        task_exec(*args, pre_report)
        try:
            # TODO use progress bar?
            for tid in tids:
                task_exec(per_report, tid)
                cmds = [tid]
                inp = self.prompt("%iter task {}> ".format(' '.join(cmds)))
                if len(inp) > 0:
                    task_exec(*cmds, *inp)
                if post_callback:
                    post_callback(tid)
                # TODO show only modifications?
                task_exec(per_report, tid)
        except EOFError:
            print("--- stopping review ---")

    def macro_inbox_add(self, *args, pre_report="list"):
        self.macro_add(self._pos_inbox_tag, *args, pre_report=pre_report)

    def macro_inbox_review(self, *args, pre_report="list", per_report="information"):
        self.macro_iter(self._pos_inbox_tag, *args, pre_report=pre_report, per_report=per_report,
                        post_callback=lambda tid: task_exec(tid, "modify", self._neg_inbox_tag, output=False))

    def macro_edit(self, *args, pre_report="list"):
        tids = task_get_lines(*args, "_ids")
        if not tids:
            return
        task_exec(*args, pre_report)
        try:
            for tid in tids:
                task_exec("information", tid)
                descr = task_get("_get", f"{tid}.description")
                cmds = [tid, "modify"]
                try:
                    inp = self.prompt(f"%edit task {' '.join(cmds)}> ", default=descr)
                    if len(inp) > 0:
                        task_exec(tid, *cmds, *inp)
                except KeyboardInterrupt:
                    # TODO not very intuitive behaviour?
                    print("--- skipping edit ---")
                task_exec("information", tid)
        except EOFError:
            print("--- stopping edit ---")

    def loop(self):
        print_formatted_text("Welcome to itask, an interactive shell for task")
        try:
            while True:
                try:
                    inp = self.prompt("task> ")
                    if len(inp) == 0:
                        self.error("empty input")
                        continue
                    try:
                        if inp[0].startswith(self._cl_args.macro_prefix):
                            (macro, *args) = inp
                            if macro in self._macros:
                                self._macros[macro](*args)
                            else:
                                self.error("unknown macro")
                                continue
                        else:
                            task_exec(*inp)
                    except TaskError as e:
                        self.error(str(e))
                except KeyboardInterrupt:
                    pass
        except EOFError:
            print("--- exit ---")


main = ITask.main
