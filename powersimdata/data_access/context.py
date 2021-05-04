from powersimdata.data_access.data_access import LocalDataAccess, SSHDataAccess
from powersimdata.data_access.launcher import HttpLauncher, NativeLauncher, SSHLauncher
from powersimdata.utility import server_setup
from powersimdata.utility.config import DeploymentMode, get_deployment_mode


class Context:
    """Factory for data access instances"""

    @staticmethod
    def get_data_access(data_loc=None):
        """Return a data access instance appropriate for the current
        environment.

        :param str data_loc: pass "disk" if using data from backup disk,
            otherwise leave the default.
        """
        if data_loc == "disk":
            root = server_setup.BACKUP_DATA_ROOT_DIR
        else:
            root = server_setup.DATA_ROOT_DIR

        mode = get_deployment_mode()
        if mode == DeploymentMode.Server:
            return SSHDataAccess(root)
        return LocalDataAccess(root)

    @staticmethod
    def get_launcher(scenario):
        """Return instance for interaction with simulation engine

        :param powersimdata.Scenario scenario: a scenario object
        """
        mode = get_deployment_mode()
        if mode == DeploymentMode.Server:
            return SSHLauncher(scenario)
        elif mode == DeploymentMode.Container:
            return HttpLauncher(scenario)
        return NativeLauncher(scenario)
