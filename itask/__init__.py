import shlex
import logging

import prompt_toolkit
from prompt_toolkit.history import InMemoryHistory

from itask.completer import ITaskCompleter
from itask.config import Config
from itask.task import TaskError, TaskHelper
from itask.utils import ObjectDecorator

if prompt_toolkit.__version__ >= '2.0.0':
    from prompt_toolkit import PromptSession, print_formatted_text
    from prompt_toolkit.styles import Style
    from prompt_toolkit.shortcuts import CompleteStyle, prompt
else:
    print_formatted_text = print
    from prompt_toolkit.shortcuts import prompt
    from prompt_toolkit.token import Token
    from prompt_toolkit.styles import style_from_dict

logger = logging.getLogger('itask')


class Macro(ObjectDecorator):
    prefix = '%'

    def __init__(self, name, signature, meta, gtd=False):
        super(Macro, self).__init__()
        self.name = name
        self.display = f'{Macro.prefix}{name} {signature}'
        self.meta = meta
        self.gtd = gtd


class ITask(object):
    @staticmethod
    def error(msg):
        print_formatted_text(f">>> [ERROR] {msg}")

    @staticmethod
    def print(msg):
        print_formatted_text(f">>> {msg}")

    @staticmethod
    def main():
        cfg = Config()

        verbosity = max(0, cfg.args.verbose * 1, cfg.args.debug * 2)
        logging.basicConfig(format='>>> [%(levelname)s] %(message)s',
                            level=[logging.WARNING, logging.INFO, logging.DEBUG][verbosity])

        logger.info(f"configuration: {cfg.args.__dict__}")

        if not cfg.has_config_file():
            ITask.print(f"no config file present;"
                        f" writing current configuration to {cfg.config_path}")
            cfg.write_config_file()

        return ITask(cfg.args).loop()

    def __init__(self, _cfg):
        self._cfg = _cfg
        self._task = TaskHelper(bin_path=_cfg.task_bin, rc_path=_cfg.task_rc)
        self._use_gtd = True

        if self._cfg.gtd_review_uda not in self._task.fetch_lines('_udas'):
            if self.ask_bool(f"review UDA '{self._cfg.gtd_review_uda}' does not exist."
                             f" Create?", default=True):
                self._task.config("uda.reviewed.type", "date", confirm=False)
                self._task.config("uda.reviewed.label", "Reviewed", confirm=False)
            else:
                self.print("review UDA not present. Respective macros will be disabled")
                self._use_gtd = False

        self._macros = {f"{Macro.prefix}{macro.name}": macro
                        for macro in map(self.__getattribute__, dir(self))
                        if isinstance(macro, Macro) and (self._use_gtd or not macro.gtd)}

        self._completer = ITaskCompleter(self._task, self._macros,
                                         indirect_tags=_cfg.complete_expand_tags,
                                         indirect_projects=_cfg.complete_expand_projects)

        # TODO persist history
        if prompt_toolkit.__version__ >= '2.0.0':
            # TODO verify display_completions_in_columns does work
            complete_style = None if _cfg.complete_display == '2col' else CompleteStyle.MULTI_COLUMN
            self._prompt_session = PromptSession(completer=self._completer,
                                                 complete_while_typing=_cfg.complete_while_typing,
                                                 complete_style=complete_style,
                                                 style=Style.from_dict({
                                                     'rprompt': 'bg:#ff0066 #ffffff',
                                                 }))
        else:
            self._history = InMemoryHistory()
            self._prompt_style = style_from_dict({
                Token.RPrompt: 'bg:#ff0066 #ffffff',
            })

        self._pos_inbox_tags = [f"+{tag}" for tag in _cfg.gtd_capture_tags]
        self._neg_inbox_tags = [f"-{tag}" for tag in _cfg.gtd_capture_tags]

        return

    def ask_bool(self, message, default=None):
        options = ['no', 'yes']
        default_info = f'({"/".join(options)})' if default is None else f'[{options[default]}]'
        while True:
            inp = prompt(f'{message} {default_info} > ')
            if len(inp) == 0:
                if default is not None:
                    return default
                else:
                    self.error("empty input")
            else:
                if inp in options:
                    return bool(options.index(inp))
                else:
                    self.error(f"unrecognized input '{inp}'")

    def prompt(self, message, default="", rmessage=None):
        if prompt_toolkit.__version__ >= '2.0.0':
            gen_rprompt = None if rmessage is None else (lambda: f'macro: {rmessage}')
            # TODO https://github.com/jonathanslenders/python-prompt-toolkit/issues/665
            inp = self._prompt_session.prompt(message, default=default, rprompt=gen_rprompt)
        else:
            gen_rprompt = None if rmessage is None else (lambda _: [(Token, ' '),
                                                                    (Token.RPrompt,
                                                                     f'macro: {rmessage}')])
            inp = prompt(message, default=default, completer=self._completer,
                         history=self._history,
                         get_rprompt_tokens=gen_rprompt, style=self._prompt_style,
                         display_completions_in_columns=self._cfg.complete_display == 'multi',
                         complete_while_typing=self._cfg.complete_while_typing)
        return shlex.split(inp)

    def _pre_report(self, *args):
        self._task.run(*args, self._cfg.macro_selection_pre_report)

    def _per_report(self, *args):
        self._task.run(*args, self._cfg.macro_selection_per_report)

    def _post_report(self, *args):
        self._task.run(*args, self._cfg.macro_selection_post_report)

    @Macro(name='add', signature='CMDs', meta='prompt `add CMDs ...` until aborted')
    def macro_add(self, name, *args):
        self._pre_report(*args)
        cmds = ("add", *args)
        while True:
            inp = self.prompt(f"task {' '.join(cmds)}> ", rmessage=name)
            if len(inp) == 0:
                self.error("empty input")
                continue
            self._task.run(*cmds, *inp)

    @Macro(name='iter', signature='FILTERs', meta='prompt for each task in selection')
    def macro_iter(self, name, *args, post_callback=None):
        tids = self._task.fetch_lines(*args, "_ids")
        if not tids:
            return
        self._pre_report(*args)
        # TODO use progress bar?
        for tid in tids:
            self._per_report(tid)
            cmds = [tid]
            # TODO handle keyboard interrupt properly
            inp = self.prompt(f"task {' '.join(cmds)}> ", rmessage=name)
            if len(inp) > 0:
                self._task.run(*cmds, *inp)
            if post_callback:
                post_callback(tid)
            # TODO show only modifications?
            self._per_report(tid)

    @Macro(name='gtd-capture', signature='CMDs', meta='prompt to add new tasks until aborted',
           gtd=True)
    def macro_gtd_capture(self, name, *args):
        self.macro_add(name, *self._pos_inbox_tags, *args)

    @Macro(name='gtd-process', signature='CMDs', meta='process captured tasks', gtd=True)
    def macro_gtd_clarify(self, name, *args):
        self.macro_iter(name, *self._pos_inbox_tags, *args,
                        post_callback=lambda tid: self._task.run(tid, "modify",
                                                                 *self._neg_inbox_tags, show=False))

    @staticmethod
    def _review_filter(uda, interval):
        return f'({uda}.none: or {uda}.before:now-{interval}) and (+PENDING or +WAITING)'

    @Macro(name='gtd-review', signature='CMDs', meta='review tasks', gtd=True)
    def macro_gtd_review(self, name, *args):
        def _update_reviewed_uda(tid):
            self._task.run(tid, "modify", f'{self._cfg.gtd_review_uda}:now', show=False)
        filter_expr = self._review_filter(self._cfg.gtd_review_uda, self._cfg.gtd_review_interval)
        self.macro_iter(name, filter_expr,
                        *args, post_callback=_update_reviewed_uda)

    @Macro(name='inbox-add', signature='CMDs', meta='prompt to add inbox tasks until aborted')
    def macro_inbox_add(self, name, *args):
        self.macro_add(name, *self._pos_inbox_tags, *args)

    @Macro(name='inbox-review', signature='FILTERs',
           meta='iterate inbox tasks, removing tag afterwards')
    def macro_inbox_review(self, name, *args):
        self.macro_iter(name, *self._pos_inbox_tags, *args,
                        post_callback=lambda tid: self._task.run(tid, "modify",
                                                                 *self._neg_inbox_tags, show=False))

    @Macro(name='edit', signature=f'FILTERs',
           meta='iterate selected tasks and in-place edit description')
    def macro_edit(self, name, *args):
        tids = self._task.fetch_lines(*args, "_ids")
        if not tids:
            return
        self._pre_report(*args)
        for tid in tids:
            self._per_report(tid)
            cmds = [tid, "modify"]
            try:
                logger.warning("in-place edit currently broken because of "
                               "https://github.com/jonathanslenders/"
                               "python-prompt-toolkit/issues/665")
                inp = self.prompt(f"task {' '.join(cmds)}> ", rmessage=name,
                                  default=self._task.fetch("_get", f"{tid}.description"))
                if len(inp) > 0:
                    self._task.run(tid, *cmds, *inp)
            except KeyboardInterrupt:
                # TODO not very intuitive behaviour?
                self.print("skipping edit")
            self._per_report(tid)

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
                            self._task.run(*inp)
                    except TaskError as e:
                        self.error(str(e))
                except KeyboardInterrupt:
                    pass
        except EOFError:
            self.print("exit")


main = ITask.main
