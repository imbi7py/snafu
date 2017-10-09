import functools
import pathlib
import sys

import click

from . import configs, operations
from . import __version__


class SnafuGroup(click.Group):
    """Force command name to 'snafu'.
    """
    def make_context(self, info_name, *args, **kwargs):
        return super().make_context('snafu', *args, **kwargs)


@click.group(cls=SnafuGroup, invoke_without_command=True)
@click.option('--version', is_flag=True, help='Print version and exit.')
@click.pass_context
def cli(ctx, version):
    if ctx.invoked_subcommand is None:
        if version:
            click.echo('SNAFU {}'.format(__version__))
        else:
            click.echo(ctx.get_help(), color=ctx.color)


@cli.command(help='Install a Python version.')
@click.argument('version')
@click.option('--file', 'from_file', type=click.Path(exists=True))
def install(version, from_file):
    version = operations.get_version(version)
    operations.check_status(version, False, on_exit=functools.partial(
        operations.link_commands, version,
    ))

    if from_file is None:
        installer_path = operations.download_installer(version)
    else:
        installer_path = pathlib.Path(from_file)

    click.echo('Running installer {}'.format(installer_path))
    dirpath = version.install(str(installer_path))

    operations.link_commands(version)
    click.echo('{} is installed succesfully to {}'.format(
        version, dirpath,
    ))


@cli.command(help='Uninstall a Python version.')
@click.argument('version')
@click.option('--file', 'from_file', type=click.Path(exists=True))
def uninstall(version, from_file):
    version = operations.get_version(version)
    operations.check_status(version, True, on_exit=functools.partial(
        operations.unlink_commands, version,
    ))
    operations.update_active_versions(remove=[version])

    if from_file is not None:
        uninstaller_path = pathlib.Path(from_file)
    else:
        try:
            uninstaller_path = version.get_cached_uninstaller()
        except FileNotFoundError:
            uninstaller_path = operations.download_installer(version)

    click.echo('Running uninstaller {}'.format(uninstaller_path))
    version.uninstall(str(uninstaller_path))
    operations.unlink_commands(version)
    click.echo('{} is uninstalled succesfully.'.format(version))


@cli.command(help='Upgrade an installed Python version.')
@click.argument('version')
@click.option('--file', 'from_file', type=click.Path(exists=True))
def upgrade(version, from_file):
    version = operations.get_version(version)
    operations.check_status(version, True, on_exit=functools.partial(
        operations.link_commands, version,
    ))
    installation_vi = version.get_installation_version_info()
    if installation_vi >= version.version_info:
        click.echo('Python {} is up to date.'.format(
            '.'.join(str(i) for i in installation_vi),
        ))
        return

    if from_file is None:
        installer_path = operations.download_installer(version)
    else:
        installer_path = pathlib.Path(from_file)

    click.echo('Running installer {}'.format(installer_path))
    version.upgrade(str(installer_path))

    operations.link_commands(version)
    click.echo('{} is upgraded succesfully at {}'.format(
        version, version.installation,
    ))


@cli.command(
    help='Set pythonX commands to, and link scripts for Python versions.',
    short_help='Set versions as active.',
)
@click.argument('version', nargs=-1)
def activate(version):
    if not version:
        version = operations.get_active_names()
    versions = [operations.get_version(v) for v in version]
    for version in versions:
        operations.check_status(version, True)
    if not versions:
        click.echo('No active versions."', err=True)
        sys.exit(1)
    # TODO: Be smarter and calculate diff, instead of rebuilding every time.
    operations.deactivate()
    operations.activate(versions)


@cli.command(
    help='Remove pythonX and linked Python script commands.',
    short_help='Deactivate all versions.',
)
def deactivate():
    operations.deactivate()


@cli.command(
    help='Prints where the executable of Python version is.',
    short_help='Print python.exe location.',
)
@click.argument('version')
def where(version):
    version = operations.get_version(version)
    operations.check_status(version, True)
    click.echo(str(version.installation.joinpath('python.exe')))


@cli.command(name='list', help='List Python versions (installed or all).')
@click.option('--all', 'list_all', is_flag=True)
def list_(list_all):
    vers = operations.get_versions(not list_all)
    active_names = set(operations.get_active_names())

    for v in vers:
        marker = ' '
        if v.name in active_names:
            marker = '*'
        elif v.is_installed():
            marker = 'o'
        # TODO: Show '+' for upgradable.
        # How should we show an upgradable *and* active version?
        click.echo('{} {}'.format(marker, v.name))

    if not list_all and not vers:
        click.echo(
            'No installed versions. Use --all to list all available versions '
            'for installation.',
            err=True,
        )


@cli.command(help='Make a command from active versions available.')
@click.argument('command')
@click.option('--force', is_flag=True)
def link(command, force):
    command_name = command
    active_names = operations.get_active_names()

    command = None
    for version_name in active_names:
        version = operations.get_version(version_name)
        try:
            command = version.find_script_path(command_name)
        except FileNotFoundError:
            continue
        break
    if command is None:
        click.echo('Command "{}" not found. Looked in {}: {}'.format(
            command_name,
            'version' if len(active_names) == 1 else 'versions',
            ', '.join(active_names),
        ), err=True)
        sys.exit(1)

    target_name = command.name
    target = configs.get_scripts_dir_path().joinpath(target_name)
    if target.exists() and not force:
        if target.read_bytes() == command.read_bytes():
            # If the two files are identical, we're good anyway.
            return
        click.echo('{} already exists. Use --force to overwrite.', err=True)
        sys.exit(1)
    operations.publish_script(command, target, overwrite=True, quiet=True)
    click.echo('Published {} from {}'.format(target_name, version))


if __name__ == '__main__':
    cli()
