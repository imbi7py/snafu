import itertools
import json
import pathlib
import shutil
import struct
import subprocess
import zipfile

import click
import pkg_resources
import requests


VERSION = '3.6.3'

DOWNLOAD_PREFIX = 'https://www.python.org/ftp/python'

KB_CODE = 'KB2999226'

WINVERS = [
    '6.0',      # Vista.
    '6.1',      # 7.
    '8-RT',     # 8.
    '8.1',      # 8.1.
]

# For the Rust-base shims. Current version: VC140 (2015) Update 3 RC.
# https://www.microsoft/en-US/download/details.aspx?id=52685
VC_REDIST_UUID = '6AA4EDFF-645B-48C5-81CC-ED5963AEAD48'


def get_python_embed_url(architecture):
    return '{pref}/{vers}/python-{vers}-embed-{arch}.zip'.format(
        pref=DOWNLOAD_PREFIX,
        vers=VERSION,
        arch=architecture,
    )


def get_py_launcher_url(architecture):
    # I dug this URL out of Python's webinstaller build.
    # See this part in the build script for description.
    # https://github.com/python/cpython/blob/v3.6.3/Tools/msi/buildrelease.bat
    return '{pref}/{vers}/{arch}/launcher.msi'.format(
        pref=DOWNLOAD_PREFIX,
        vers=VERSION,
        arch=architecture,
    )


def get_kb_msu_url(architecture, wver, warc):
    return '{pref}/{vers}/{arch}/Windows{wver}-{code}-{warc}.msu'.format(
        pref=DOWNLOAD_PREFIX,
        vers=VERSION,
        arch=architecture,
        code=KB_CODE,
        wver=wver,
        warc=warc,
    )


def get_vc_redist_url(winarc):
    # URL scheme from this repository. UUID from official download link.
    # https://github.com/WPN-XM/vcredist
    return (
        'https://download.microsoft.com/download/'
        '{uuid[0]}/{uuid[1]}/{uuid[2]}/{uuid}/vc_redist.{warc}.exe'
    ).format(uuid=VC_REDIST_UUID, warc=winarc)


def get_snafu_version():
    with ROOT.parent.joinpath('snafu', '__init__.py').open() as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line[len('__version__ = '):])


def get_latest_python_name():

    def load_definition(p):
        with p.open() as f:
            data = json.load(f)
        data['name'] = p.stem
        return data

    definitions = [
        load_definition(p)
        for p in ROOT.parent.joinpath('snafu', 'versions').iterdir()
        if p.suffix == '.json'
    ]

    # 1. Prefer newer versions.
    # 2. Prefer shorter names because they look "more default".
    latest_definition = max(
        definitions,
        key=lambda d: (d['version_info'], -len(d['name'])),
    )
    return latest_definition['name']


ROOT = pathlib.Path(__file__).parent.resolve(strict=True)

ASSETSDIR = ROOT.joinpath('assets')
ASSETSDIR.mkdir(exist_ok=True)


def download_file(url, path):
    click.echo('Downloading {}'.format(url))
    response = requests.get(url, stream=True)
    response.raise_for_status()

    installer_name = url.rsplit('/', 1)[-1]
    total = response.headers.get('content-length', '')
    chunks = []

    if total.isdigit():
        length = int(total)
    else:
        length = None
    with click.progressbar(length=length, label=installer_name) as b:
        for chunk in response.iter_content(chunk_size=4096):
            chunks.append(chunk)
            if length is not None:
                b.update(len(chunk))

    path.write_bytes(b''.join(chunks))


def get_py_launcher(arch):
    installer_path = ASSETSDIR.joinpath('py-{vers}-{arch}.msi'.format(
        vers=VERSION,
        arch=arch,
    ))
    if not installer_path.exists():
        download_file(get_py_launcher_url(arch), installer_path)
    return installer_path


def get_embed_bundle(arch):
    url = get_python_embed_url(arch)
    bundle_path = ASSETSDIR.joinpath(url.rsplit('/', 1)[-1])
    if not bundle_path.exists():
        download_file(url, bundle_path)
    return bundle_path


def get_kb_msu(arch, winver, winarc):
    url = get_kb_msu_url(arch, winver, winarc)
    msu_path = ASSETSDIR.joinpath(url.rsplit('/', 1)[-1])
    if not msu_path.exists():
        download_file(url, msu_path)
    return msu_path


def get_vc_redist(winarc):
    url = get_vc_redist_url(winarc)
    installer_path = ASSETSDIR.joinpath(url.rsplit('/', 1)[-1])
    if not installer_path.exists():
        download_file(url, installer_path)
    return installer_path


def get_dependency_names():
    lock_path = ROOT.parent.joinpath('Pipfile.lock')
    with lock_path.open() as f:
        data = json.load(f)
    return data['default'].keys()


class PackageResolutionError(ValueError):
    pass


def build_package_path(location, name):
    path = pathlib.Path(location, name)
    if path.is_dir():
        return path
    path = pathlib.Path(location, '{}.py'.format(name))
    if path.is_file():
        return path
    raise PackageResolutionError(name)


def get_package_paths():
    # TODO: This only works for pure Python packages.
    # This will fail if we need binary dependencies (e.g. pypiwin32) in the
    # future because the host will only have either 32- or 64-bit binary, but
    # we need both to build installers for each architecture. We should instead
    # download wheels from PyPI, and extract to get the packages.
    paths = []
    for name in get_dependency_names():
        dist = pkg_resources.get_distribution(name)
        top_level = pathlib.Path(dist.egg_info).joinpath('top_level.txt')
        paths.extend(
            build_package_path(dist.location, n)
            for n in top_level.read_text().split('\n') if n
        )
    return paths


def build_python(arch, libdir):
    pythondir = libdir.joinpath('python')
    pythondir.mkdir()

    # Extract Python distribution.
    click.echo('Populating Embeddable Python.')
    with zipfile.ZipFile(str(get_embed_bundle(arch))) as f:
        f.extractall(str(pythondir))

    # Copy SNAFU.
    click.echo('Populate SNAFU.')
    shutil.copytree(
        str(ROOT.parent.joinpath('snafu')),
        str(pythondir.joinpath('snafu')),
    )

    # Write SNAFU configurations.
    with pythondir.joinpath('snafu', 'installation.json').open('w') as f:
        json.dump({
            'cmd_dir': '..\\..\\..\\cmd',
            'scripts_dir': '..\\..\\..\\scripts',
            'shims_dir': '..\\..\\shims',
        }, f)

    # Copy dependencies.
    click.echo('Populate dependencies...')
    for path in get_package_paths():
        click.echo('  {}'.format(path.stem))
        if path.is_dir():
            shutil.copytree(str(path), str(pythondir.joinpath(path.name)))
        else:
            shutil.copy2(str(path), str(pythondir.joinpath(path.name)))

    # Cleanup.
    click.echo('Remove junks...')
    for p in pythondir.rglob('__pycache__'):
        shutil.rmtree(str(p))
    for p in pythondir.rglob('*.py[co]'):
        shutil.rmtree(str(p))


SCRIPT_EXTS = ('.py', '.vbs')


def build_setup(arch, libdir):
    setupdir = libdir.joinpath('setup')
    setupdir.mkdir()

    # Copy necessary updates.
    winarcs = {
        'amd64': ['x64'],
        'win32': ['x86', 'x64'],
    }[arch]
    for winver, winarc in itertools.product(WINVERS, winarcs):
        msu_path = get_kb_msu(arch, winver, winarc)
        click.echo('Copy {}'.format(msu_path.name))
        shutil.copy2(
            str(msu_path),
            setupdir.joinpath(msu_path.name),
        )

    # Copy VC redistributable installer.
    winarc = {
        'amd64': 'x64',
        'win32': 'x86',
    }[arch]
    installer = get_vc_redist(winarc)
    click.echo('Copy {}'.format(installer.name))
    shutil.copy2(
        str(installer),
        setupdir.joinpath(installer.name),
    )

    # Copy Py launcher MSI.
    click.echo('Copy py.msi')
    msi = get_py_launcher(arch)
    shutil.copy2(str(msi), str(setupdir.joinpath('py.msi')))

    # Copy setup scripts.
    click.echo('Copy setup scripts...')
    for path in ROOT.joinpath('lib', 'setup').iterdir():
        if path.suffix not in SCRIPT_EXTS:
            continue
        name = path.name
        click.echo('  {}'.format(name))
        shutil.copy2(str(path), str(setupdir.joinpath(name)))


def build_shims(libdir):
    rust_project_root = ROOT.parent.joinpath('shims')

    click.echo('Build shims...')
    subprocess.check_call(
        'cargo build --release',
        shell=True, cwd=str(rust_project_root),
    )

    shimsdir = libdir.joinpath('shims')
    shimsdir.mkdir()
    click.echo('Copy shims...')
    for path in rust_project_root.joinpath('target', 'release').iterdir():
        if path.suffix != '.exe':
            continue
        name = path.name
        click.echo('  {}'.format(name))
        shutil.copy2(str(path), str(shimsdir.joinpath(name)))


def build_lib(arch, container):
    libdir = container.joinpath('lib')
    libdir.mkdir()
    build_python(arch, libdir)
    build_setup(arch, libdir)
    build_shims(libdir)


def build_files(arch):
    container = ROOT.joinpath('snafu')
    if container.exists():
        shutil.rmtree(str(container))
    container.mkdir()
    build_lib(arch, container)


def build_installer(outpath):
    if outpath.exists():
        outpath.unlink()
    click.echo('Building installer.')
    subprocess.check_call([
        'makensis',
        '/DPYTHONVERSION={}'.format(get_latest_python_name()),
        str(ROOT.joinpath('snafu.nsi')),
    ], shell=True)
    click.echo('snafu-setup.exe -> {}'.format(outpath))
    shutil.move(str(ROOT.joinpath('snafu-setup.exe')), str(outpath))


def cleanup():
    container = ROOT.joinpath('snafu')
    shutil.rmtree(str(container))
    subprocess.check_call(
        'cargo clean',
        shell=True, cwd=str(ROOT.parent.joinpath('shims')),
    )


@click.command()
@click.argument('version', default='dev')
@click.option('--clean/--no-clean', is_flag=True, default=True)
@click.option('--clean-only', is_flag=True)
def build(version, clean, clean_only):
    if clean_only:
        cleanup()
        return
    arch = {
        8: 'amd64',
        4: 'win32',
    }[struct.calcsize('P')]
    out = 'snafu-setup-{}-{}.exe'.format(arch, version.strip())
    outpath = pathlib.Path(out)
    if not outpath.is_absolute():
        outpath = ROOT.joinpath(outpath)

    build_files(arch)
    build_installer(outpath)
    if clean:
        cleanup()


if __name__ == '__main__':
    build()
