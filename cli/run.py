import os

import click
import flask.cli as flask_cli


def _register_local_run_flag():
    run_command = flask_cli.run_command
    if any(
            isinstance(param, click.Option) and '--local' in param.opts
            for param in run_command.params):
        return

    run_command.params = list(run_command.params) + [
        click.Option(
            ('--local/--no-local',),
            default=True,
            help='Use HTTP for OAuth callbacks. Pass --no-local for HTTPS.',
        )
    ]

    original_callback = run_command.callback

    def callback(
            info, host, port, reload, debugger, eager_loading, with_threads, cert,
            extra_files, local=True):
        os.environ['OAUTH_CALLBACK_SCHEME'] = 'http' if local else 'https'
        return original_callback(
            info, host, port, reload, debugger, eager_loading, with_threads, cert,
            extra_files)

    run_command.callback = callback


_register_local_run_flag()
