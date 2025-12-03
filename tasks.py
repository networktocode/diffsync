<<<<<<< HEAD
"""Replacement for Makefile.

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
from distutils.util import strtobool

from invoke import task  # type: ignore

try:
    import toml
except ImportError:
    sys.exit("Please make sure to `pip install toml` or enable the Poetry shell and run `poetry install`.")


def project_ver():
    """Find version from pyproject.toml to use for docker image tagging."""
    with open("pyproject.toml", encoding="UTF-8") as file:
        return toml.load(file)["tool"]["poetry"].get("version", "latest")
=======
"""Tasks for use with Invoke."""

import os
import re
from pathlib import Path

from invoke import Collection, Exit
from invoke import task as invoke_task
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
<<<<<<< HEAD
    return bool(strtobool(arg))


# Can be set to a separate Python version to be used for launching or building image
PYTHON_VER = os.getenv("PYTHON_VER", "3.9")
# Name of the docker image/image
NAME = os.getenv("IMAGE_NAME", f"diffsync-py{PYTHON_VER}")
# Tag for the image
IMAGE_VER = os.getenv("IMAGE_VER", project_ver())
# Gather current working directory for Docker commands
PWD = os.getcwd()
# Local or Docker execution provide "local" to run locally without docker execution
INVOKE_LOCAL = is_truthy(os.getenv("INVOKE_LOCAL", False))  # pylint: disable=W1508


def run_cmd(context, exec_cmd, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
=======

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    if val in ("n", "no", "f", "false", "off", "0"):
        return False
    raise ValueError(f"Invalid truthy value: `{arg}`")


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_DIFFSYNC_xxx
namespace = Collection("diffsync")
namespace.configure(
    {
        "diffsync": {
            "project_name": "diffsync",
            "python_ver": "3.10",
            "local": is_truthy(os.getenv("INVOKE_DIFFSYNC_LOCAL", "false")),
            "image_name": "diffsync",
            "image_ver": os.getenv("INVOKE_PARSER_IMAGE_VER", "latest"),
            "pwd": Path(__file__).parent,
        }
    }
)


# pylint: disable=keyword-arg-before-vararg
def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


def run_command(context, exec_cmd, port=None):
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)
    """Wrapper to run the invoke task commands.

    Args:
        context ([invoke.task]): Invoke task object.
        exec_cmd ([str]): Command to run.
<<<<<<< HEAD
        name ([str], optional): Image name to use if exec_env is `docker`. Defaults to NAME.
        image_ver ([str], optional): Version of image to use if exec_env is `docker`. Defaults to IMAGE_VER.
        local (bool): Define as `True` to execute locally
=======
        port (int): Used to serve local docs.
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)

    Returns:
        result (obj): Contains Invoke result from running task.
    """
<<<<<<< HEAD
    if is_truthy(local):
        print(f"LOCAL - Running command {exec_cmd}")
        result = context.run(exec_cmd, pty=True)
    else:
        print(f"DOCKER - Running command: {exec_cmd} container: {name}:{image_ver}")
        result = context.run(f"docker run -it -v {PWD}:/local {name}:{image_ver} sh -c '{exec_cmd}'", pty=True)
=======
    if is_truthy(context.diffsync.local):
        print(f"LOCAL - Running command {exec_cmd}")
        result = context.run(exec_cmd, pty=True)
    else:
        print(
            f"DOCKER - Running command: {exec_cmd} container: {context.diffsync.image_name}:{context.diffsync.image_ver}"
        )
        if port:
            result = context.run(
                f"docker run -it -p {port} -v {context.diffsync.pwd}:/local {context.diffsync.image_name}:{context.diffsync.image_ver} sh -c '{exec_cmd}'",
                pty=True,
            )
        else:
            result = context.run(
                f"docker run -it -v {context.diffsync.pwd}:/local {context.diffsync.image_name}:{context.diffsync.image_ver} sh -c '{exec_cmd}'",
                pty=True,
            )
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)

    return result


<<<<<<< HEAD
@task
def build(
    context, name=NAME, python_ver=PYTHON_VER, image_ver=IMAGE_VER, nocache=False, forcerm=False
):  # pylint: disable=too-many-arguments, too-many-positional-arguments
    """This will build an image with the provided name and python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Define the Python version docker image to build from
        image_ver (str): Define image version
        nocache (bool): Do not use cache when building the image
        forcerm (bool): Always remove intermediate containers
    """
    print(f"Building image {name}:{image_ver}")
    command = f"docker build --tag {name}:{image_ver} --build-arg PYTHON_VER={python_ver} -f Dockerfile ."

    if nocache:
        command += " --no-cache"
    if forcerm:
        command += " --force-rm"

    result = context.run(command, hide=False)
    if result.exited != 0:
        print(f"Failed to build image {name}:{image_ver}\nError: {result.stderr}")


@task
def clean_image(context, name=NAME, image_ver=IMAGE_VER):
    """This will remove the specific image.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
    """
    print(f"Attempting to forcefully remove image {name}:{image_ver}")
    context.run(f"docker rmi {name}:{image_ver} --force")
    print(f"Successfully removed image {name}:{image_ver}")


@task
def rebuild(context, name=NAME, python_ver=PYTHON_VER, image_ver=IMAGE_VER):
    """This will clean the image and then rebuild image without using cache.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Define the Python version docker image to build from
        image_ver (str): Define image version
    """
    clean_image(context, name, image_ver)
    build(context, name, python_ver, image_ver)


@task
def pytest(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run pytest for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Will use the container version docker image
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    # Install python module
    exec_cmd = "pytest --cov=diffsync --cov-config pyproject.toml --cov-report html --cov-report term -vv"
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def black(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run black to check that Python files adherence to black standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "black --check --diff ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def flake8(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run flake8 for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "flake8 ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def mypy(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run mypy for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "mypy -p diffsync"
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def pylint(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run pylint for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = 'find . -name "*.py" | xargs pylint'
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def yamllint(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "yamllint ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def pydocstyle(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run pydocstyle to validate docstring formatting adheres to NTC defined standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "pydocstyle ."
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def bandit(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run bandit to validate basic static code security analysis.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    exec_cmd = "bandit --recursive ./ --configfile .bandit.yml"
    run_cmd(context, exec_cmd, name, image_ver, local)


@task
def cli(context, name=NAME, image_ver=IMAGE_VER):
    """This will enter the image to perform troubleshooting or dev work.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
    """
    dev = f"docker run -it -v {PWD}:/local {name}:{image_ver} /bin/bash"
    context.run(f"{dev}", pty=True)


@task
def tests(context, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """This will run all tests for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        image_ver (str): Define image version
        local (bool): Define as `True` to execute locally
    """
    black(context, name, image_ver, local)
    flake8(context, name, image_ver, local)
    pylint(context, name, image_ver, local)
    yamllint(context, name, image_ver, local)
    pydocstyle(context, name, image_ver, local)
    mypy(context, name, image_ver, local)
    bandit(context, name, image_ver, local)
    pytest(context, name, image_ver, local)

=======
# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "cache": "Whether to use Docker's cache when building images (default enabled)",
        "force_rm": "Always remove intermediate images",
        "hide": "Suppress output from Docker",
    }
)
def build(context, cache=True, force_rm=False, hide=False):
    """Build a Docker image."""
    print(f"Building image {context.diffsync.image_name}:{context.diffsync.image_ver}")
    command = f"docker build --tag {context.diffsync.image_name}:{context.diffsync.image_ver} --build-arg PYTHON_VER={context.diffsync.python_ver} -f Dockerfile ."

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    result = context.run(command, hide=hide)
    if result.exited != 0:
        print(
            f"Failed to build image {context.diffsync.image_name}:{context.diffsync.image_ver}\nError: {result.stderr}"
        )


@task
def generate_packages(context):
    """Generate all Python packages inside docker and copy the file locally under dist/."""
    command = "poetry build"
    run_command(context, command)


@task(
    help={
        "check": (
            "If enabled, check for outdated dependencies in the poetry.lock file, "
            "instead of generating a new one. (default: disabled)"
        )
    }
)
def lock(context, check=False):
    """Generate poetry.lock inside the library container."""
    run_command(context, f"poetry {'check' if check else 'lock --no-update'}")


@task
def clean(context):
    """Remove the project specific image."""
    print(
        f"Attempting to forcefully remove image {context.diffsync.image_name}:{context.diffsync.image_ver}"
    )
    context.run(f"docker rmi {context.diffsync.image_name}:{context.diffsync.image_ver} --force")
    print(f"Successfully removed image {context.diffsync.image_name}:{context.diffsync.image_ver}")


@task
def rebuild(context):
    """Clean the Docker image and then rebuild without using cache."""
    clean(context)
    build(context, cache=False)


@task
def coverage(context):
    """Run the coverage report against pytest."""
    exec_cmd = "coverage run --source=diffsync -m pytest"
    run_command(context, exec_cmd)
    run_command(context, "coverage report")
    run_command(context, "coverage html")


@task
def pytest(context):
    """Run pytest test cases."""
    exec_cmd = "pytest -vv --doctest-modules diffsync/ && coverage run --source=diffsync -m pytest && coverage report"
    run_command(context, exec_cmd)


@task(aliases=("a",))
def autoformat(context):
    """Run code autoformatting."""
    ruff(context, action=["format"], fix=True)


@task(
    help={
        "action": "Available values are `['lint', 'format']`. Can be used multiple times. (default: `['lint', 'format']`)",
        "target": "File or directory to inspect, repeatable (default: all files in the project will be inspected)",
        "fix": "Automatically fix selected actions. May not be able to fix all issues found. (default: False)",
        "output_format": "See https://docs.astral.sh/ruff/settings/#output-format for details. (default: `concise`)",
    },
    iterable=["action", "target"],
)
def ruff(context, action=None, target=None, fix=False, output_format="concise"):
    """Run ruff to perform code formatting and/or linting."""
    if not action:
        action = ["lint", "format"]
    if not target:
        target = ["."]

    exit_code = 0

    if "format" in action:
        command = "ruff format "
        if not fix:
            command += "--check "
        command += " ".join(target)
        if not run_command(context, command):
            exit_code = 1

    if "lint" in action:
        command = "ruff check "
        if fix:
            command += "--fix "
        command += f"--output-format {output_format} "
        command += " ".join(target)
        if not run_command(context, command):
            exit_code = 1

    if exit_code != 0:
        raise Exit(code=exit_code)


@task
def pylint(context):
    """Run pylint for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
    """
    exec_cmd = 'find . -name "*.py" | grep -vE "tests/unit" | xargs pylint'
    run_command(context, exec_cmd)


@task
def yamllint(context):
    """Run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
    """
    exec_cmd = "yamllint ."
    run_command(context, exec_cmd)


@task
def cli(context):
    """Enter the image to perform troubleshooting or dev work.

    Args:
        context (obj): Used to run specific commands
    """
    dev = f"docker run -it -v {context.diffsync.pwd}:/local {context.diffsync.image_name}:{context.diffsync.image_ver} /bin/bash"
    context.run(f"{dev}", pty=True)


@task(
    help={
        "lint-only": "Only run linters; unit tests will be excluded. (default: False)",
    }
)
def tests(context, lint_only=False):
    """Run all tests for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        lint_only (bool): If True, only run linters and skip unit tests.
    """
    # If we are not running locally, start the docker containers so we don't have to for each test
    # Sorted loosely from fastest to slowest
    print("Running ruff...")
    ruff(context)
    print("Running yamllint...")
    yamllint(context)
    print("Running poetry check...")
    lock(context, check=True)
    print("Running pylint...")
    pylint(context)
    print("Running mkdocs...")
    build_and_check_docs(context)
    if not lint_only:
        print("Running unit tests...")
        pytest(context)
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)
    print("All tests have passed!")


@task
<<<<<<< HEAD
def html(context, sourcedir="docs/source", builddir="docs/build"):
    """Creates html docs using sphinx-build command.

    Args:
        context (obj): Used to run specific commands
        sourcedir (str, optional): Source directory for sphinx to use. Defaults to "source".
        builddir (str, optional): Output directory for sphinx to use. Defaults to "build".
    """
    print("Building html documentation...")
    clean_docs(context, builddir)
    command = f"sphinx-build {sourcedir} {builddir}"
    context.run(command)


@task
def clean_docs(context, builddir="docs/build"):
    """Removes the build directory and all of its contents.

    Args:
        context (obj): Used to run specific commands
        builddir (str, optional): Directory to be removed. Defaults to "build".
    """
    print(f"Removing everything under {builddir} directory...")
    context.run("rm -rf " + builddir)
=======
def build_and_check_docs(context):
    """Build documentation and test the configuration."""
    command = "mkdocs build --no-directory-urls --strict"
    run_command(context, command)

    # Check for the existence of a release notes file for the current version if it's not a prerelease.
    version = context.run("poetry version --short", hide=True)
    match = re.match(r"^(\d+)\.(\d+)\.\d+$", version.stdout.strip())
    if match:
        major = match.group(1)
        minor = match.group(2)
        release_notes_file = Path(__file__).parent / "docs" / "admin" / "release_notes" / f"version_{major}.{minor}.md"
        if not release_notes_file.exists():
            print(f"Release notes file `version_{major}.{minor}.md` does not exist.")
            raise Exit(code=1)


@task
def docs(context):
    """Build and serve docs locally for development."""
    exec_cmd = "mkdocs serve -v"
    run_command(context, exec_cmd, port="8001:8001")


@task(
    help={
        "version": "Version of diffsync to generate the release notes for.",
    }
)
def generate_release_notes(context, version=""):
    """Generate Release Notes using Towncrier."""
    command = "poetry run towncrier build"
    if version:
        command += f" --version {version}"
    else:
        command += " --version `poetry version -s`"
    # Due to issues with git repo ownership in the containers, this must always run locally.
    context.run(command)
>>>>>>> c5f3eb1 (Cookie initialy baked by NetworkToCode Cookie Drift Manager Tool)
