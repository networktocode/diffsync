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
    with open("pyproject.toml") as file:
        return toml.load(file)["tool"]["poetry"].get("version", "latest")


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
    return bool(strtobool(arg))


# Can be set to a separate Python version to be used for launching or building image
PYTHON_VER = os.getenv("PYTHON_VER", os.getenv("TRAVIS_PYTHON_VERSION", "3.7"))
# Name of the docker image/image
NAME = os.getenv("IMAGE_NAME", f"diffsync-py{PYTHON_VER}")
# Tag for the image
IMAGE_VER = os.getenv("IMAGE_VER", project_ver())
# Gather current working directory for Docker commands
PWD = os.getcwd()
# Local or Docker execution provide "local" to run locally without docker execution
INVOKE_LOCAL = is_truthy(os.getenv("INVOKE_LOCAL", False))  # pylint: disable=W1508


def run_cmd(context, exec_cmd, name=NAME, image_ver=IMAGE_VER, local=INVOKE_LOCAL):
    """Wrapper to run the invoke task commands.

    Args:
        context ([invoke.task]): Invoke task object.
        exec_cmd ([str]): Command to run.
        name ([str], optional): Image name to use if exec_env is `docker`. Defaults to NAME.
        image_ver ([str], optional): Version of image to use if exec_env is `docker`. Defaults to IMAGE_VER.
        local (bool): Define as `True` to execute locally

    Returns:
        result (obj): Contains Invoke result from running task.
    """
    if is_truthy(local):
        print(f"LOCAL - Running command {exec_cmd}")
        result = context.run(exec_cmd, pty=True)
    else:
        print(f"DOCKER - Running command: {exec_cmd} container: {name}:{image_ver}")
        result = context.run(f"docker run -it -v {PWD}:/local {name}:{image_ver} sh -c '{exec_cmd}'", pty=True)

    return result


@task
def build(
    context, name=NAME, python_ver=PYTHON_VER, image_ver=IMAGE_VER, nocache=False, forcerm=False
):  # pylint: disable=too-many-arguments
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
    exec_cmd = 'find . -name "*.py" -not -path "*/examples/*" -not -path "*/docs/*" | xargs mypy --show-error-codes'
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

    print("All tests have passed!")


@task
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
