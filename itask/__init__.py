import argparse
import shlex
import prompt_toolkit
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.token import Token
from prompt_toolkit.styles import style_from_dict

from itask.utils import task_exec, task_get, task_get_lines, TaskError

if prompt_toolkit.__version__ >= '2.0.0':
    from prompt_toolkit import PromptSession, print_formatted_text
else:
    print_formatted_text = print


class ITaskCompleter(Completer):
    command_synopsis = {
        'add': 'add [proj:...] [due:...] [+TAGs] TEXT',
        'info': 'info [IDs]',
        'delete': 'delete [IDs]',
    }

    def __init__(self, macros, indirect_tags, indirect_projects):
        self._indirect_tags = indirect_tags
        self._indirect_projects = indirect_projects

        cmds = [line.split(':') for line in task_get_lines('_zshcommands')]
        self._cmds = [
            self._completion(cmd, display=self.command_synopsis.get(cmd), meta=f"[{category}] {description}")
            for (cmd, category, description) in cmds
        ]

        self._macros = [
            self._completion(key, meta=macro.meta, display=macro.display)
            for key, macro in macros.items()
        ]

        self._project_prefixes = [f'{prefix}:' for prefix in ['pro', 'proj', 'proje', 'projec', 'project']]
        self._projects = {}
        self._pos_tags = []
        self._neg_tags = []
        self._update_cache()

    @staticmethod
    def _completion(text, display=None, meta=None):
        if display is None:
            display = text
        return Completion(text, display=display, display_meta=meta)

    def _update_cache(self):
        # TODO async
        self._projects = {
            prefix: [self._completion(f'{prefix}{project}') for project in task_get_lines("_projects")]
            for prefix in self._project_prefixes
        }

        tags = list(filter(lambda t: not all(c.isupper() for c in t), task_get_lines("_tags")))
        self._pos_tags = [self._completion(f'+{tag}') for tag in tags]
        self._neg_tags = [self._completion(f'-{tag}') for tag in tags]

    def _completions(self, word):
        yield from self._cmds
        yield from self._macros

        for tag_prefix, label in [('+', 'positive'), ('-', 'negative')]:
            assert len(tag_prefix) == 1
            if word.startswith(tag_prefix) or not self._indirect_tags:
                yield from self._pos_tags
                yield from self._neg_tags
            elif len(word) == 0:
                yield self._completion(tag_prefix, display=f'{tag_prefix}...', meta=f'{label} tag selector')

        pref_match = [prefix for prefix in self._project_prefixes
                      if word.startswith(prefix)]
        if pref_match:
            yield from self._projects[pref_match[0]]
        elif self._indirect_projects:
            yield self._completion("project:", display="project:...", meta="assign task to project")
        else:
            yield from self._projects['project:']

    def get_completions(self, document, complete_event):
        word = document.get_word_under_cursor(WORD=True)

        for completion in self._completions(word):
            if completion.text.startswith(word):
                completion.start_position = -len(word)
                yield completion


class Macro(object):
    prefix = '%'

    def __init__(self, func, name, display, meta):
        self.func = func
        self.name = name
        self.display = display
        self.meta = meta

    def __get__(self, *args, **kwargs):
        # update func reference to method object
        self.func = self.func.__get__(*args, **kwargs)
        return self

    def __call__(self, *args, **kwargs):
        self.func(*args, **kwargs)

    @staticmethod
    def wrapper(name, display=None, meta=None):
        return lambda func: Macro(func, name, display, meta)


class ITask(object):

    @staticmethod
    def main():
        parser = argparse.ArgumentParser()

        def add_bool_argument(opt, default):
            dest = opt[2:].replace('-', '_')
            parser.add_argument(opt, dest=dest, action='store_true')
            parser.add_argument(f'{opt[:2]}no-{opt[2:]}', dest=dest, action='store_false')
            parser.set_defaults(**{dest: default})

        parser.add_argument("--inbox-tag", type=str, default="inbox")
        add_bool_argument('--complete-while-typing', default=True)
        add_bool_argument('--complete-indirect-tags', default=True)
        add_bool_argument('--complete-indirect-projects', default=True)
        add_bool_argument('--complete-show-meta-always', default=True)

        return ITask(parser.parse_args()).loop()

    @staticmethod
    def error(msg):
        print_formatted_text(f">>> [ERROR] {msg}")

    @staticmethod
    def print(msg):
        print_formatted_text(f">>> {msg}")

    def __init__(self, cl_args):
        self._macros = {f"{Macro.prefix}{macro.name}": macro
                        for macro in map(self.__getattribute__, dir(self)) if isinstance(macro, Macro)}

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
            self._prompt_style = style_from_dict({
                Token.RPrompt: 'bg:#ff0066 #ffffff',
            })

        self._cl_args = cl_args
        self._pos_inbox_tag = f"+{cl_args.inbox_tag}"
        self._neg_inbox_tag = f"-{cl_args.inbox_tag}"

    def prompt(self, message, default="", rmessage=None):
        if prompt_toolkit.__version__ >= '2.0.0':
            # TODO implement rmessage
            return shlex.split(self._prompt_session.prompt(message, default))
        else:
            gen_rprompt = None if rmessage is None else (lambda _: [(Token, ' '),
                                                                    (Token.RPrompt, f'macro: {rmessage}')])
            return shlex.split(prompt(message, default=default, completer=self._completer,
                                      history=self._history,
                                      get_rprompt_tokens=gen_rprompt, style=self._prompt_style,
                                      display_completions_in_columns=self._cl_args.complete_show_meta_always,
                                      complete_while_typing=self._cl_args.complete_while_typing))

    @Macro.wrapper(name='add', display=f'{Macro.prefix}add CMDs', meta='prompt `add CMDs ...` until aborted')
    def macro_add(self, name, *args, pre_report="list"):
        task_exec(*args, pre_report)
        cmds = ("add", *args)
        while True:
            inp = self.prompt(f"task {' '.join(cmds)}> ", rmessage=name)
            if len(inp) == 0:
                self.error("empty input")
                continue
            task_exec(*cmds, *inp)

    @Macro.wrapper(name='iter', display=f'{Macro.prefix}iter FILTERs', meta='prompt for each task in selection')
    def macro_iter(self, name, *args, pre_report="list", per_report="information", post_callback=None):
        tids = task_get_lines(*args, "_ids")
        if not tids:
            return
        task_exec(*args, pre_report)
        # TODO use progress bar?
        for tid in tids:
            task_exec(per_report, tid)
            cmds = [tid]
            # TODO handle keyboard interrupt properly
            inp = self.prompt(f"task {' '.join(cmds)}> ", rmessage=name)
            if len(inp) > 0:
                task_exec(*cmds, *inp)
            if post_callback:
                post_callback(tid)
            # TODO show only modifications?
            task_exec(per_report, tid)

    @Macro.wrapper(name='inbox-add', display=f'{Macro.prefix}inbox-add CMDs',
                   meta='prompt to add inbox tasks until aborted')
    def macro_inbox_add(self, name, *args, pre_report="list"):
        self.macro_add(name, self._pos_inbox_tag, *args, pre_report=pre_report)

    @Macro.wrapper(name='inbox-review', display=f'{Macro.prefix}inbox-review FILTERs',
                   meta='iterate inbox tasks, removing tag afterwards')
    def macro_inbox_review(self, name, *args, pre_report="list", per_report="information"):
        self.macro_iter(name, self._pos_inbox_tag, *args, pre_report=pre_report, per_report=per_report,
                        post_callback=lambda tid: task_exec(tid, "modify", self._neg_inbox_tag, output=False))

    @Macro.wrapper(name='edit', display=f'{Macro.prefix}edit FILTERs',
                   meta='iterate selected tasks and in-place edit description')
    def macro_edit(self, name, *args, pre_report="list"):
        tids = task_get_lines(*args, "_ids")
        if not tids:
            return
        task_exec(*args, pre_report)
        for tid in tids:
            task_exec("information", tid)
            descr = task_get("_get", f"{tid}.description")
            cmds = [tid, "modify"]
            try:
                inp = self.prompt(f"task {' '.join(cmds)}> ", rmessage=name, default=descr)
                if len(inp) > 0:
                    task_exec(tid, *cmds, *inp)
            except KeyboardInterrupt:
                # TODO not very intuitive behaviour?
                self.print("skipping edit")
            task_exec("information", tid)

    def loop(self):
        print_formatted_text("Welcome to itask, an interactive shell for task")
        try:
            while True:
                try:
                    inp = self.prompt("task> ")
                    try:
                        if inp and inp[0].startswith(Macro.prefix):
                            (macro_name, *args) = inp
                            if macro_name in self._macros:
                                try:
                                    self._macros[macro_name](macro_name, *args)
                                except EOFError:
                                    self.print(f"EOF: stopping {macro_name}")
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
            self.print("exit")


main = ITask.main
