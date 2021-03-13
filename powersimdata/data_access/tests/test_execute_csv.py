import os
import shutil
from collections import OrderedDict

import pandas as pd
import pytest
from numpy.testing import assert_array_equal
from pandas.testing import assert_frame_equal

import powersimdata.utility.templates as templates
from powersimdata.data_access.data_access import LocalDataAccess, SSHDataAccess
from powersimdata.data_access.execute_list import ExecuteListManager
from powersimdata.utility import server_setup


@pytest.fixture
def data_access():
    data_access = SSHDataAccess()
    yield data_access
    data_access.close()


@pytest.fixture
def execute_table(data_access):
    execute_list_manager = ExecuteListManager(data_access)
    return execute_list_manager.get_execute_table()


@pytest.mark.integration
@pytest.mark.ssh
def test_get_execute_file_local(execute_table):
    ecm = ExecuteListManager(None)
    from_local = ecm.get_execute_table()
    assert_frame_equal(from_local, execute_table)


@pytest.mark.integration
@pytest.mark.ssh
def test_get_execute_file_from_server_type(execute_table):
    assert isinstance(execute_table, pd.DataFrame)


@pytest.mark.integration
@pytest.mark.ssh
def test_get_execute_file_from_server_header(execute_table):
    header = ["status"]
    assert_array_equal(execute_table.columns, header)
    assert "id" == execute_table.index.name


def clone_template():
    orig = os.path.join(templates.__path__[0], "ExecuteList.csv")
    dest = os.path.join(server_setup.LOCAL_DIR, "ExecuteList.csv.test")
    os.makedirs(server_setup.LOCAL_DIR, exist_ok=True)
    shutil.copy(orig, dest)


def mock_row():
    return OrderedDict(
        [
            ("id", "1"),
            ("state", "create"),
            ("interconnect", "Western"),
        ]
    )


@pytest.fixture
def manager():
    clone_template()
    data_access = LocalDataAccess()
    manager = ExecuteListManager(data_access)
    manager._FILE_NAME = "ExecuteList.csv.test"
    return manager


def test_blank_csv_append(manager):
    manager.add_entry(mock_row())
    table = manager.get_execute_table()
    assert table.shape == (1, 1)
    status = manager.get_status(1)
    assert status == "created"


def test_set_status(manager):
    manager.add_entry(mock_row())
    asdf = "asdf"
    result = manager.set_status(1, asdf)
    assert result.loc[1, "status"] == asdf

    foo = "foo"
    result = manager.set_status("1", foo)
    assert result.loc[1, "status"] == foo


def test_get_status(manager):
    manager.add_entry(mock_row())
    status = manager.get_status(1)
    assert status == "created"

    status = manager.get_status("1")
    assert status == "created"


def test_delete(manager):
    manager.add_entry(mock_row())
    table = manager.get_execute_table()
    assert table.shape == (1, 1)

    table = manager.delete_entry(1)
    assert table.shape == (0, 1)

    table = manager.get_execute_table()
    assert table.shape == (0, 1)
