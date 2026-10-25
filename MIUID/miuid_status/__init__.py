from pathlib import Path

from PIL import Image

from gsuid_core.status.plugin_status import register_status

from ..version import MIUID_version
from ..utils.resource.RESOURCE_PATH import RESOURCE_PATH

ICON = Path(__file__).parent.parent.parent / "ICON.png"


async def get_version() -> str:
    return MIUID_version


async def get_resource_num() -> int:
    return sum(1 for path in RESOURCE_PATH.iterdir() if path.is_file())


register_status(
    Image.open(ICON),
    "MIUID",
    {
        "版本": get_version,
        "资源文件": get_resource_num,
    },
)
