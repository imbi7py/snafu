## Next (not released)

### Behavioural Changes

* The scripts PATH is moved ahead of the cmd. This provides potential for more flexible customisations, i.e. if multiple sources install the same executable (CPython and Anaconda, for example), one (CPython) can take precedence in cmd, but allow the user to override this by the `use` command.
* SNAFU now works system-wide Python installations, and can publish shims for them as well as `snafu install`-ed ones. It still only supports installing them in per-user mode, but other commands should mostly work.  
  **EXCEPTION**: Upgrading an MSI-based Python version (3.4 or earlier) is not supported.


## Unstable

Nothing yet.


## Version 2.0

### UI Changes

* Remove confusing `activate` and `deactivate` commands in favour of the `use` command. The previous “reactivation” behaviour is now mapped to `link --all`.
* A newly installed Python will be used if there are no other versions detected.
* Add `snafu upgrade self` to perform in-place upgrade without manually downloading the installer.
* Add `snafu download <version>` to download installer of given Python version without installing.
* More complete help messages are provided to command arguments.
* The uninstalling processes are now as interaction-free as installing. Previously some user intervention was needed (especially the EXE-based versions).

### Behavioural Changes

* `snafu install` now automatically uses the version if it is the only Python installation detected. This should simplify things even more for beginners.
* Minor update to Python 3.4 definition.
* Call `snafu link --all` automatically after installing with a shimmed pip command.
* Upgrade Python 3.4 definition to 3.4.4.
* Upgrade Python 3.6 definition to 3.6.4.
* Improve behaviour when uninstalling versions not installed by SNAFU.
* `snafu link --all` without active versions does not fail anymore. The warning message is still printed, but the exit code is now 0.
* Py Launcher usage is reduced in favour of reading the registry ourselves.
* Documentation is no longer installed with each Python version.

### Installer Changes

* Add an option to install and use a Python version after SNAFU is set up.
* 64-bit variant does not carry x86 MSU files anymore, reducing installer size.
* Correctly install Windows update KB2999226 on 32-bit Windows.


## Version 1.0

### UI Changes

* New `upgrade` command to install a newer patch version on an installed version.
* New `link` command to manually publish a script from the active Python versions.

### Behavioural Changes

* `pip-X.Y` are now published on install.
* Automatically deactivate an uninstalling active version.
* A Python exception will be raised early on download error, instead of failing later during installation.
* Uninstallation now skips gracefully if launcher scripts do not exist.

### Installer Changes

* Bundle and trigger Windows update KB2999226 on installation to provide necessary runtime files on Windows Vista to 8.1 so the bundled Python 3.6 can run correctly.
* Environment variables changes can now propagate correctly without OS restart.


## Version 0.2

### UI Changes

* `uninstall` now attempts to use Windows’s uninstall feature to avoid re-download.
* `install` and `uninstall` receives a `--file` option to allow using local installers without re-downloading.  
  **IMPORTANT:** Correctness of the installer is not checked. The user is responsible for choosing the correct and valid installer file. Results of installing a faulty installer is undefined.
* New command `where` to show where the actual interpreter is. This is useful if you need to pass it to another command (e.g. `pipenv --python`).
* `list` shows activeness.
* `snafu --version` shows program version.

### Behavioural Changes

* `activate` writes a pin file showing the current active versions.
* Symbols in `snafu list` are changed.

### Installer Changes

* Environment variables are now set up automatically during installation.
* Extract the py launcher MSI to make the distribution substentially smaller.
* The installer now comes with both 64- and 32-bit flavours.
* The uninstaller is now added to registry, so you can remove SNAFU in Control Panel.


## Version 0.1

Initial release. Features I want the most are largely implemented. Only 64-bit Pythons are supported for now, and the installer is 64-bit-only.

An all-in-one installer that installs SNAFU into
`%LOCALAPPDATA%\Programs\SNAFU`, and sets up the py launcher.

* `snafu install/uninstall <version>`
* `snafu list [--all]`
* `snafu activate/deactivate <version> [<version> ...]`
