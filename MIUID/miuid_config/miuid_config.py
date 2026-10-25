from gsuid_core.utils.plugins_config.gs_config import StringConfig

from ..utils.resource.RESOURCE_PATH import CONFIG_PATH
from .config_default import CONFIG_DEFAULT

MIUID_CONFIG = StringConfig(
    "MIUID",
    CONFIG_PATH,
    CONFIG_DEFAULT,
)
