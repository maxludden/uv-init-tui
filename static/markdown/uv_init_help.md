---
CSS: ../css/styles.css
---



# `uv init --help`

```Create a new project.```



## Usage

<span style="color:#AF00FF;font-family:Urbanist;">uv</span> init <span style="color: #0FF; font-family: MesloLGS NF;">[OPTIONS]</span> <span style="color: #FF0; font-family: MesloLGS NF;">[PATH]</span>

### Arguments

| Argument | Description                            |
| -------- | -------------------------------------- |
| [PATH]   | The path to use for the project/script |

## Options

### Project Configuration

| Option             | Metavar           | Description                                                  |                         |
| ------------------ | ----------------- | ------------------------------------------------------------ | ----------------------- |
| `--name <NAME>`    |                   | The name of the project                                      |                         |
| `--bare`           |                   | Only create a pyproject.toml                                 |                         |
| `--package`        |                   | Set up the project to be built as a Python package           |                         |
| `--no-package`     |                   | Do not set up the project to be built as a Python package    |                         |
| `--app`            |                   | Create a project for an application                          |                         |
| `--lib`            |                   | Create a project for a library                               |                         |
| `--script`         |                   | Create a script                                              |                         |
| ``--description`   | `<DESCRIPTION>`   | Set the project description                                  |                         |
| `--no-description` |                   | Disable the description for the project                      |                         |
| `--vcs <VCS>`      |                   | Initialize a version control system for the projectPossible values: auto, git, none |                         |
| `--build-backen`   | `<BUILD_BACKEND>` | Initialize a build backend of choicePossible values: uv, hatch, flit, pdm, poetry, setuptools, maturin, scikit | `UV_INIT_BUILD_BACKEND` |
| `--no-readme`      |                   | Do not create a README.md file                               |                         |
| `--author-from`    | `<AUTHOR_FROM>`   | Add author metadata to pyproject.tomlPossible values: auto, git, none |                         |
| `--no-pin-python`  |                   | Do not create a .python-version file                         |                         |
| `--no-workspace`   |                   | Avoid discovering a workspace and create a standalone project |                         |

### Python Options

| Option                  | Metavar    | Description                                                  | ENV Variable                |
| ----------------------- | ---------- | ------------------------------------------------------------ | --------------------------- |
| `-p`, `--python`        | `<PYTHON>` | The Python interpreter to use to determine the minimum supported. | `UV_PYTHON`                 |
| `--managed-python`      |            | Require use of uv-managed Python                             | ` UV_MANAGED_PYTHON`        |
| `--no-managed-python`   |            | Disable use of uv-managed Python                             | `UV_NO_MANAGED_PYTHON`      |
| `--no-python-downloads` |            | Disable automatic downloads of Python                        | `UV_PYTHON_DOWNLOADS=never` |

### Cache Options

| Option           | Metavar       | Description                                                  | ENV Variable | Possible Values |
| ---------------- | ------------- | ------------------------------------------------------------ | ------------ | --------------- |
| `-n, --no-cache` |               | Avoid reading from or writing to the cache; use a temporary cache directory for the operation | UV_NO_CACHE  |                 |
| `--cache-dir`    | `<CACHE_DIR>` | Path to the cache directory                                  | UV_CACHE_DIR |                 |
|                  |               |                                                              |              |                 |

### Global Options

| Option                  | Metavar                 | Description                                                  | ENV Variable       | Possible Values             |
| ----------------------- | ----------------------- | ------------------------------------------------------------ | ------------------ | --------------------------- |
| `-q`, `--quiet`         |                         | Use quiet output.                                            |                    |                             |
| `-v`, `--verbose`       |                         | Use verbose output.                                          |                    |                             |
| `--color `              | `<COLOR_CHOICE>`        | Use of color in output.                                      |                    | `auto`, `always`, `never`*  |
| `--native-tls`          |                         | Whether to load TLS certificates from the platform’s native store. | `UV_NATIVE_TLS`    |                             |
| `--offline`             |                         | Disable network access                                       | `UV_OFFLINE`       |                             |
| `--allow-insecure-host` | `<ALLOW_INSECURE_HOST>` | Allow insecure connections to a host.                        | `UV_INSECURE_HOST` |                             |
| ``--no-progress`        |                         | Hide all progress outputs.                                   | `UV_NO_PROGRESS`   |                             |
| `--directory`           | ` <DIRECTORY>`          | Change to the given directory prior to running the command.  | `UV_WORKING_DIR`   |                             |
| `--project`             | `<PROJECT>`             | Discover a project in the given directory                    | `UV_PROJECT`       |                             |
| `--config-file`         | `<CONFIG_FILE>`         | Path to a uv.toml file to use for configuration.             | `UV_CONFIG_FILE`   |                             |
| `--no-config`           |                         | Avoid discovering configuration files                        | `UV_NO_CONFIG`     | `pyproject.toml`, `uv.toml` |
|                         |                         |                                                              |                    |                             |
|                         |                         |                                                              |                    |                             |
|                         |                         |                                                              |                    |                             |

### Help

| Option         | Description                            |      |
| -------------- | -------------------------------------- | ---- |
| `-h`, `--help` | Display concise help for this command. |      |
|                |                                        |      |
