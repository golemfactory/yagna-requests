import asyncio
import logging
import os
from pathlib import Path

import pytest

from goth.configuration import load_yaml
from goth.runner.log import configure_logging
from goth.runner import Runner
from goth.runner.probe import RequestorProbe

from .assertions import assert_no_errors

import requests

logger = logging.getLogger("goth.test.run_proxy")


@pytest.fixture(scope='module')
def event_loop():
    """This overrides `pytest.asyncio` fixture"""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
async def requestor_proxy(
    project_dir: Path, log_dir: Path, goth_config_path: Path
) -> None:
    goth_config = load_yaml(goth_config_path)
    requestor_script_path = project_dir / "examples" / "requestor_proxy" / "requestor_proxy.py"
    configure_logging(log_dir)
    runner = Runner(
        base_log_dir=log_dir,
        compose_config=goth_config.compose_config,
    )

    async with runner(goth_config.containers):

        requestor = runner.get_probes(probe_type=RequestorProbe)[0]

        async with requestor.run_command_on_host(
            f"{requestor_script_path} goth",
            env=os.environ,
        ) as (cmd_task, cmd_monitor):
            cmd_monitor.add_assertion(assert_no_errors)

            await cmd_monitor.wait_for_pattern(".*STARTED ON provider.*", timeout=200)
            logger.info("STARTED!")

            yield

            cmd_task.cancel()


@pytest.mark.asyncio
async def test_1(requestor_proxy):
    res = requests.get('http://localhost:5000/add/1/2')
    assert res.status_code == 200
    assert res.text == '3'


@pytest.mark.asyncio
async def test_2(requestor_proxy):
    res = requests.get('http://localhost:5000/add/1/2')
    assert res.status_code == 200
    assert res.text == '4'


@pytest.mark.asyncio
async def test_3(requestor_proxy):
    res = requests.get('http://localhost:5000/add/1/2')
    assert res.status_code == 200
    assert res.text == '3'
