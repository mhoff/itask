import configargparse
import os
import re
import logging

from itask import utils


class Config:
    default_config_path = os.path.join('~', '.itaskrc')

    def __init__(self):
        self._parser = Config._create_parser()
        self._args = None

    @staticmethod
    def _type_tag(value):
        if len(value) == 0 or not re.fullmatch(r'[a-zA-Z_.]+', value):
            raise configargparse.ArgumentTypeError(f"{value} is not a valid tag")
        return value

    @staticmethod
    def _type_report(value):
        # TODO check against available reports
        if len(value) == 0 or not re.fullmatch(r'[a-zA-Z_.]+', value):
            raise configargparse.ArgumentTypeError(f"{value} is not a valid report")
        return value

    @staticmethod
    def _create_parser():
        parser = configargparse.ArgParser(default_config_files=[Config.default_config_path])
        parser.add_argument('-c', '--config', is_config_file=True, help='custom config file path')

        def add_bool(parser, opt, default=None, help=None):
            def str2bool(v):
                if v.lower() in ('yes', 'true', 't', 'y', '1'):
                    return True
                elif v.lower() in ('no', 'false', 'f', 'n', '0'):
                    return False
                else:
                    raise configargparse.ArgumentTypeError(f'{v} is not a valid value')

            dest = opt.replace('-', '_')
            excl = parser.add_mutually_exclusive_group()
            excl.add_argument(f'--{opt}', type=str2bool, const=True, nargs='?', metavar='FLAG', dest=dest)
            excl.add_argument(f'--no-{opt}', action='store_false', dest=dest, help=help)
            excl.set_defaults(**{dest: default})

        grp = parser.add_argument_group('general')
        grp.add_argument('-v', '--verbose', action='store_true')

        grp = parser.add_argument_group('auto-complete')
        add_bool(grp, 'complete-while-typing', True,
                 help="show completions on any keystroke automatically")
        add_bool(grp, 'complete-expand-tags', True,
                 help="hide tag completions until a tag prefix (+,-) is present")
        add_bool(grp, 'complete-expand-projects', default=True,
                 help="hide project completions until the project keyword has been entered")
        grp.add_argument('--complete-display', type=str, choices=['multi', '2col'], default='multi',
                         help='either display completions side-by-side with their explanation,'
                              'or more completions at once')

        grp = parser.add_argument_group('getting-things-done (https://gettingthingsdone.com/five-steps/)')
        grp.add_argument('--gtd-capture-tags', default=['inbox'], type=Config._type_tag, nargs='+',
                         help="filter tags used in GTD macros. "
                              # TODO https://github.com/bw2/ConfigArgParse/issues/95
                              "WARNING: tag-lists can not yet be saved, due to a bug in ConfigArgParse")

        grp = parser.add_argument_group('macros')
        grp.add_argument('--macro-selection-pre-report', default='ls', type=Config._type_report,
                         help="report for displaying affected tasks before processing")
        grp.add_argument('--macro-selection-per-report', default='info', type=Config._type_report,
                         help="report for displaying task details per iteration")
        grp.add_argument('--macro-selection-post-report', default='ls', type=Config._type_report,
                         help="report for displaying affected tasks after processing")
        return parser

    @property
    def args(self):
        if self._args is None:
            self._args = self._parser.parse_args()
            if self._args.verbose:
                print(self._args)
        return self._args

    @property
    def config_path(self):
        return os.path.expanduser(self.args.config if self.args.config is not None else Config.default_config_path)

    def has_config_file(self):
        return os.path.exists(self.config_path)

    def write_config_file(self):
        # TODO https://github.com/bw2/ConfigArgParse/issues/95
        not_saveable = {"gtd_capture_tags", "config"}.intersection(self._args.__dict__.keys())
        if not_saveable:
            logging.warning(f"options ({', '.join(map(lambda s: s.replace('_', '-'), not_saveable))}) can not be saved")
        args = configargparse.Namespace(**{k: v for k, v in self.args.__dict__.items()
                                           if k not in not_saveable})

        # TODO https://github.com/bw2/ConfigArgParse/issues/127
        with utils.suppress_stdout():
            self._parser.write_config_file(args, [self.config_path])
