import json
from pathlib import Path

from PIL import Image

from gsuid_core.help.draw_new_plugin_help import get_new_help
from gsuid_core.help.model import PluginHelp
from gsuid_core.sv import get_plugin_available_prefix

from ..version import MIUID_version

ICON = Path(__file__).parent.parent.parent / "ICON.png"
HELP_DATA = Path(__file__).parent / "help.json"


def get_help_data() -> dict[str, PluginHelp]:
    with HELP_DATA.open(encoding="utf-8") as file:
        return json.load(file)


PLUGIN_HELP = get_help_data()


async def get_help(pm: int = 6) -> bytes:
    return await get_new_help(
        plugin_name="MIUID",
        plugin_info={f"v{MIUID_version}": ""},
        plugin_icon=Image.open(ICON),
        plugin_help=PLUGIN_HELP,
        plugin_prefix=get_plugin_available_prefix("MIUID"),
        help_mode="dark",
        enable_cache=True,
        pm=pm,
    )
