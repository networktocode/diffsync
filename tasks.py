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
from invoke import task  # type: ignore


# Can be set to a separate Python version to be used for launching or building container
PYTHON_VER = os.getenv("PYTHON_VER", "3.7")
# Name of the docker image/container
NAME = os.getenv("IMAGE_NAME", "dsync-1.0.0")
# Gather current working directory for Docker commands
PWD = os.getcwd()


@task
def build_test_container(context, name=NAME, python_ver=PYTHON_VER):
    """This will build a container with the provided name and python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    print(f"Building container {name}-{python_ver}")
    result = context.run(
        f"docker build --tag {name}-{python_ver} --build-arg PYTHON_VER={python_ver} -f Dockerfile .", hide=True
    )
    if result.exited != 0:
        print(f"Failed to build container {name}-{python_ver}\nError: {result.stderr}")


@task
def build_test_containers(context):
    """This will build two containers using Python 3.6 and 3.7.

    Args:
        context (obj): Used to run specific commands
    """
    build_test_container(context, python_ver="3.6")
    build_test_container(context, python_ver="3.7")


@task
def clean_container(context, name=NAME):
    """This stops and removes the specified container.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
    """
    print(f"Attempting to stop {name}")
    stop = context.run(f"docker stop {name}")
    print(f"Successfully stopped {name}")
    if stop.ok:
        print(f"Attempting to remove {name}")
        context.run(f"docker rm {name}")
        print(f"Successfully removed {name}")
    else:
        print(f"Failed to stop container {name}")


@task
def _clean_image(context, name=NAME, python_ver=PYTHON_VER):
    """This will remove the specific image.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    print(f"Attempting to forcefully remove image {name}-{python_ver}")
    context.run(f"docker rmi {name}-{python_ver}:latest --force")
    print(f"Successfully removed image {name}-{python_ver}")


@task
def clean_images(context):
    """This will remove the Python 3.6 and 3.7 images.

    Args:
        context (obj): Used to run specific commands
    """
    _clean_image(context, NAME, "3.6")
    _clean_image(context, NAME, "3.7")


@task
def rebuild_docker_images(context):
    """This will clean the images for both Python 3.6 and 3.7 and then rebuild containers without using cache.

    Args:
        context (obj): Used to run specific commands
    """
    clean_images(context)
    build_test_containers(context)


@task
def pytest(context, name=NAME, python_ver=PYTHON_VER):
    """This will run pytest for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    # Install python module
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(
        f"{docker} /bin/bash -c 'poetry install && pytest --cov=dsync --cov-report html --cov-report term -vv'",
        pty=True,
    )


@task
def black(context, name=NAME, python_ver=PYTHON_VER):
    """This will run black to check that Python files adherence to black standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} black --check --diff .", pty=True)


@task
def flake8(context, name=NAME, python_ver=PYTHON_VER):
    """This will run flake8 for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} flake8 .", pty=True)


@task
def mypy(context, name=NAME, python_ver=PYTHON_VER):
    """This will run mypy for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} sh -c \"find . -name '*.py' | xargs mypy --show-error-codes \"", pty=True)


@task
def pylint(context, name=NAME, python_ver=PYTHON_VER):
    """This will run pylint for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} sh -c \"find . -name '*.py' | xargs pylint\"", pty=True)


@task
def yamllint(context, name=NAME, python_ver=PYTHON_VER):
    """This will run yamllint to validate formatting adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} yamllint .", pty=True)


@task
def pydocstyle(context, name=NAME, python_ver=PYTHON_VER):
    """This will run pydocstyle to validate docstring formatting adheres to NTC defined standards.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} pydocstyle .", pty=True)


@task
def bandit(context, name=NAME, python_ver=PYTHON_VER):
    """This will run bandit to validate basic static code security analysis.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # pty is set to true to properly run the docker commands due to the invocation process of docker
    # https://docs.pyinvoke.org/en/latest/api/runners.html - Search for pty for more information
    docker = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest"
    context.run(f"{docker} bandit --recursive ./ --configfile .bandit.yml", pty=True)


@task
def enter_container(context, name=NAME, python_ver=PYTHON_VER):
    """This will enter the container to perform troubleshooting or dev work.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    dev = f"docker run -it -v {PWD}:/local {name}-{python_ver}:latest /bin/bash"
    context.run(f"{dev}", pty=True)


@task
def tests(context, name=NAME, python_ver=PYTHON_VER):
    """This will run all tests for the specified name and Python version.

    Args:
        context (obj): Used to run specific commands
        name (str): Used to name the docker image
        python_ver (str): Will use the Python version docker image to build from
    """
    # Sorted loosely from fastest to slowest
    print("Running black...")
    black(context, name, python_ver)
    print("Running yamllint...")
    yamllint(context, name, python_ver)
    print("Running flake8...")
    flake8(context, name, python_ver)
    print("Running bandit...")
    bandit(context, name, python_ver)
    print("Running pydocstyle...")
    pydocstyle(context, name, python_ver)
    print("Running mypy...")
    mypy(context, name, python_ver)
    print("Running pylint...")
    pylint(context, name, python_ver)
    print("Running pytest...")
    pytest(context, name, python_ver)

    print("All tests have passed!")
