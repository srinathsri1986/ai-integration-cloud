"""External-system connectors — bootstrap all plugins into the registry on import."""

from .hcm.plugin import HCMPlugin
from .netsuite.plugin import NetSuitePlugin
from .oracle.plugin import OraclePlugin
from .postgres.plugin import PostgreSQLPlugin
from .registry import connector_registry
from .rest_api.plugin import RESTAPIPlugin
from .salesforce.plugin import SalesforcePlugin
from .sap.plugin import SAPPlugin
from .slack.plugin import SlackPlugin

connector_registry.register(NetSuitePlugin())
connector_registry.register(SalesforcePlugin())
connector_registry.register(SAPPlugin())
connector_registry.register(OraclePlugin())
connector_registry.register(HCMPlugin())
connector_registry.register(PostgreSQLPlugin())
connector_registry.register(RESTAPIPlugin())
connector_registry.register(SlackPlugin())

__all__ = ["connector_registry"]
