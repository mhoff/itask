import logging
from prompt_toolkit.completion import Completer, Completion

logger = logging.getLogger('itask')


class ITaskCompleter(Completer):
    command_signature = {
        'add': 'add [proj:...] [due:...] [+TAGs] TEXT',
        'info': 'info [IDs]',
        'delete': 'delete [IDs]',
    }

    def __init__(self, task, macros, indirect_tags, indirect_projects):
        self._task = task

        self._indirect_tags = indirect_tags
        self._indirect_projects = indirect_projects

        cmds = [line.split(':') for line in self._task.fetch_lines('_zshcommands')]
        self._cmds = [
            self._completion(cmd, display=self.command_signature.get(cmd),
                             meta=f"[{category}] {description}")
            for (cmd, category, description) in cmds
        ]

        self._macros = [
            self._completion(key, meta=macro.meta, display=macro.display)
            for key, macro in macros.items()
        ]

        self._project_prefixes = [f'{prefix}:'
                                  for prefix in ['pro', 'proj', 'proje', 'projec', 'project']]
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
            prefix: [self._completion(f'{prefix}{project}')
                     for project in self._task.fetch_lines("_projects")]
            for prefix in self._project_prefixes
        }

        tags = list(filter(lambda t: not all(c.isupper() for c in t),
                           self._task.fetch_lines("_tags")))
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
                yield self._completion(tag_prefix, display=f'{tag_prefix}...',
                                       meta=f'{label} tag selector')

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
