"""Nox sessions."""

import shutil
import sys
from pathlib import Path
from textwrap import dedent
from typing import Iterable
from typing import Iterator

import nox


package = "jbmanager"
python_versions = ["3.11", "3.10", "3.9", "3.8"]
nox.needs_version = ">= 2021.10.1"
nox.options.sessions = (
    "pre-commit",
    "safety",
    "mypy",
    "tests",
    "typeguard",
    "xdoctest",
    "docs-build",
)


def install(session: nox.Session, *, groups: Iterable[str], root: bool = True) -> None:
    """Install the dependency groups using Poetry.

    This function installs the given dependency groups into the session's
    virtual environment. When ``root`` is true (the default), the function
    also installs the root package and its default dependencies.

    To avoid an editable install, the root package is not installed using
    ``poetry install``. Instead, the function invokes ``pip install .``
    to perform a PEP 517 build.

    Args:
        session: The Session object.
        groups: The dependency groups to install.
        root: Install the root package.
    """
    session.run_always(
        "poetry",
        "install",
        "--no-root",
        "--sync",
        "--{}={}".format("only" if not root else "with", ",".join(groups)),
        external=True,
    )
    if root:
        session.install(".")


def export_requirements(session: nox.Session, *, extras: Iterable[str] = ()) -> Path:
    """Export a requirements file from Poetry.

    This function uses ``poetry export`` to generate a requirements file
    containing the default dependencies at the versions specified in
    ``poetry.lock``.

    Args:
        session: The Session object.
        extras: Extras supported by the project.

    Returns:
        The path to the requirements file.
    """
    # XXX Use poetry-export-plugin with dependency groups
    output = session.run_always(
        "poetry",
        "export",
        "--format=requirements.txt",
        "--without-hashes",
        *[f"--extras={extra}" for extra in extras],
        external=True,
        silent=True,
        stderr=None,
    )

    if output is None:
        session.skip(
            "The command `poetry export` was not executed"
            " (a possible cause is specifying `--no-install`)"
        )

    assert isinstance(output, str)  # nosec assert_used noqa: S101

    def _stripwarnings(lines: Iterable[str]) -> Iterator[str]:
        for line in lines:
            if line.startswith("Warning:"):
                print(line, file=sys.stderr)
                continue
            yield line

    text = "".join(_stripwarnings(output.splitlines(keepends=True)))

    path = session.cache_dir / "requirements.txt"
    path.write_text(text)

    return path


def activate_virtualenv_in_precommit_hooks(session: nox.Session) -> None:
    """Activate virtualenv in hooks installed by pre-commit.

    This function patches git hooks installed by pre-commit to activate the
    session's virtual environment. This allows pre-commit to locate hooks in
    that environment when invoked from git.

    Args:
        session: The Session object.
    """
    assert session.bin is not None  # nosec assert_used noqa: S101

    virtualenv = session.env.get("VIRTUAL_ENV")
    if virtualenv is None:
        return

    hookdir = Path(".git") / "hooks"
    if not hookdir.is_dir():
        return

    for hook in hookdir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        text = hook.read_text()
        bindir = repr(session.bin)[1:-1]  # strip quotes
        if not (
            Path("A") == Path("a") and bindir.lower() in text.lower() or bindir in text
        ):
            continue

        lines = text.splitlines()
        if not (lines[0].startswith("#!") and "python" in lines[0].lower()):
            continue

        header = dedent(
            f"""\
            import os
            os.environ["VIRTUAL_ENV"] = {virtualenv!r}
            os.environ["PATH"] = os.pathsep.join((
                {session.bin!r},
                os.environ.get("PATH", ""),
            ))
            """
        )

        lines.insert(1, header)
        hook.write_text("\n".join(lines))


@nox.session(name="pre-commit", python=python_versions[0])
def precommit(session: nox.Session) -> None:
    """Lint using pre-commit."""
    args = session.posargs or ["run", "--all-files", "--show-diff-on-failure"]
    install(session, groups=["pre-commit"], root=False)
    session.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(session)


@nox.session(python=python_versions[0])
def safety(session: nox.Session) -> None:
    """Scan dependencies for insecure packages."""
    # NOTE: Pass `extras` to `export_requirements` if the project supports any.
    requirements = export_requirements(session)
    install(session, groups=["safety"], root=False)
    session.run("safety", "check", "--full-report", f"--file={requirements}")


@nox.session(python=python_versions)
def mypy(session: nox.Session) -> None:
    """Type-check using mypy."""
    args = session.posargs or ["src", "tests", "docs/conf.py"]
    install(session, groups=["mypy", "tests"])
    session.run("mypy", *args)
    if not session.posargs:
        session.run("mypy", f"--python-executable={sys.executable}", "noxfile.py")


@nox.session(python=python_versions)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    install(session, groups=["coverage", "tests"])

    if session.python == "3.10":
        # Workaround an unidentified issue in Poetry 1.2.0a2.
        session.install("coverage[toml]==6.1.2")

    try:
        session.run("coverage", "run", "--parallel", "-m", "pytest", *session.posargs)
    finally:
        if session.interactive:
            session.notify("coverage", posargs=[])


@nox.session
def coverage(session: nox.Session) -> None:
    """Produce the coverage report."""
    args = session.posargs or ["report"]

    install(session, groups=["coverage"], root=False)

    if not session.posargs and any(Path().glob(".coverage.*")):
        session.run("coverage", "combine")

    session.run("coverage", *args)


@nox.session(python=python_versions)
def typeguard(session: nox.Session) -> None:
    """Runtime type checking using Typeguard."""
    install(session, groups=["typeguard", "tests"])
    session.run("pytest", f"--typeguard-packages={package}", *session.posargs)


@nox.session(python=python_versions)
def xdoctest(session: nox.Session) -> None:
    """Run examples with xdoctest."""
    args = session.posargs or ["all"]
    install(session, groups=["xdoctest"])
    session.run("python", "-m", "xdoctest", package, *args)


@nox.session(name="docs-build", python=python_versions[0])
def docs_build(session: nox.Session) -> None:
    """Build the documentation."""
    args = session.posargs or ["docs", "docs/_build"]
    install(session, groups=["docs"])

    build_dir = Path("docs", "_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    session.run("sphinx-build", *args)


@nox.session(python=python_versions[0])
def docs(session: nox.Session) -> None:
    """Build and serve the documentation with live reloading on file changes."""
    args = session.posargs or ["--open-browser", "docs", "docs/_build"]
    install(session, groups=["docs"])

    build_dir = Path("docs", "_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    session.run("sphinx-autobuild", *args)
