"""在子进程中完成米家二维码登录。"""

import base64
import json
import sys
from pathlib import Path

from mijiaAPI import mijiaAPI

QR_START = "[MIJIA_QR]"
QR_END = "[/MIJIA_QR]"


def main() -> None:
    auth_path = Path(sys.argv[1])
    api = mijiaAPI(str(auth_path))
    login_data = api._get_qr_login_data()
    if login_data.get("refreshed"):
        auth = api.auth_data
        if auth:
            print(f"[MIJIA_AUTH]{json.dumps(auth, ensure_ascii=False)}[/MIJIA_AUTH]", flush=True)
        return

    login_url = login_data["loginUrl"]
    encoded = base64.urlsafe_b64encode(login_url.encode("utf-8")).decode("ascii")
    print(f"{QR_START}{encoded}{QR_END}", flush=True)
    auth = api._complete_qr_login(login_data)
    print(f"[MIJIA_AUTH]{json.dumps(auth, ensure_ascii=False)}[/MIJIA_AUTH]", flush=True)


if __name__ == "__main__":
    main()
