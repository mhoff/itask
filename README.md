# itask: interactive taskwarrior shell

*itask* is an interactive shell for the (free and open-source) task-management software [taskwarrior](https://taskwarrior.org/). taskwarrior, or in short *task*, is already a highly flexible and powerful word processing tool, which not only supports fine-granular task-managment, but also complex queries and batch processing.

itask intends to complement this functionality with a more smart and interactive interface.
In essence, itask provides a shell repeatedly prompting the user to *only* complete pre-written task commands.

Imagine you want to add multiple tasks to the project your are currently working on.
Using plain task, you would find yourself doing something like:

```
$ task add project:my_cool_project +ui use material design
$ task add project:my_cool_project +ui rewrite button labels
$ task add project:my_cool_project +ui fix input dialog
```
The itask equivalent, on the other hand, looks as follows:
```
$ itask
task> %add project:my_cool_project +ui
task project:my_cool_project +ui> use material design
task project:my_cool_project +ui> rewrite button labels
task project:my_cool_project +ui> fix input dialog
task project:my_cool_project +ui> ^D
task>
```
The *macro* `%add` is pre-defined in itask and transparently constructs task commands which suit the users' needs.
Another macro is `%edit` wich, in contrast to `%add` does not prompt for new tasks,
but iterates over selection of tasks and provides an in-place editable prompt for every single task.
Hence, the user can quickly modify small bits of task descriptions,
or change meta information by simply appending to the prompt.

## current status

itask is currently undergoing heavy development.
The shell does already provide ipython-like auto-completion of commands, tags, projects and macros.
We intend to make this completion even smarter by utilizing a simple grammar,
allowing for context-dependent user support.

Another feature of itask is strong support for standard processes, e.g. getting-things-done.
itask already provides macros for capturing, organizing/clarifying and reviewing tasks.

## requirements

- `taskwarrior` (see https://taskwarrior.org/download/)
- `python3.6` or newer
- pypi packages `prompt-toolkit` and `configargparse` (`pip -r requirements.txt` or `pip install .`)
