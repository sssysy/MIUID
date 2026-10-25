from gsuid_core.data_store import get_res_path

MAIN_PATH = get_res_path() / "MIUID"
CONFIG_PATH = MAIN_PATH / "config.json"
CACHE_PATH = MAIN_PATH / "cache"
RESOURCE_PATH = MAIN_PATH / "resource"

for path in (CACHE_PATH, RESOURCE_PATH):
    path.mkdir(parents=True, exist_ok=True)
