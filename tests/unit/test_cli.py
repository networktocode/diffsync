"""Example Test using Fixtures."""

import mock

from diffsync import cli


@mock.patch("diffsync.cli.log")
def test_cli_logging(log, cli_runner):
    """Assert our logging gets called in CLI app."""
    result = cli_runner.invoke(cli.main, ["--test", "ntc"])

    assert result.exit_code == 0
    assert result.output == "ntc\n"
    log.info.assert_called()
    log.info.assert_called_with("Entrypoint of the CLI app.")
