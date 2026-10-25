"""米家二维码登录子进程管理。"""

import asyncio
import base64
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from gsuid_core.logger import logger

LOGIN_TIMEOUT = 120.0
QR_START = "[MIJIA_QR]"
QR_END = "[/MIJIA_QR]"
AUTH_START = "[MIJIA_AUTH]"
AUTH_END = "[/MIJIA_AUTH]"


@dataclass(frozen=True)
class MijiaLoginSession:
    process: asyncio.subprocess.Process
    login_url: str | None
    buffer: str


class MijiaLoginError(Exception):
    """米家登录失败。"""


def _extract(buffer: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), buffer, re.S)
    return match.group(1) if match else ""


async def start_qr_login(auth_path: Path) -> MijiaLoginSession:
    """启动登录子进程，读到二维码链接后立即返回。"""
    worker = Path(__file__).parent / "mijia_login_worker.py"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        str(worker),
        str(auth_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    if process.stdout is None:
        raise MijiaLoginError("登录子进程管道不可用")

    buffer = ""
    try:
        while True:
            chunk = await asyncio.wait_for(process.stdout.read(512), timeout=LOGIN_TIMEOUT)
            if not chunk:
                raise MijiaLoginError("未能获取登录二维码")
            buffer += chunk.decode("utf-8", errors="replace")
            auth_raw = _extract(buffer, AUTH_START, AUTH_END)
            if auth_raw:
                return MijiaLoginSession(process=process, login_url=None, buffer=buffer)
            encoded = _extract(buffer, QR_START, QR_END)
            if encoded:
                login_url = base64.urlsafe_b64decode(encoded).decode("utf-8")
                return MijiaLoginSession(process=process, login_url=login_url, buffer=buffer)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise MijiaLoginError("登录超时，请重试") from exc
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise


async def wait_qr_login(session: MijiaLoginSession) -> str:
    """等待扫码完成并返回 JSON 形式的完整凭据。"""
    process = session.process
    if process.stdout is None:
        raise MijiaLoginError("登录子进程管道不可用")
    buffer = session.buffer
    auth_raw = _extract(buffer, AUTH_START, AUTH_END)
    if auth_raw:
        await process.wait()
        return json.dumps(json.loads(auth_raw), ensure_ascii=False)
    try:
        while True:
            chunk = await asyncio.wait_for(process.stdout.read(512), timeout=LOGIN_TIMEOUT)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
        returncode = await process.wait()
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise MijiaLoginError("登录超时，请重试") from exc
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise

    auth_raw = _extract(buffer, AUTH_START, AUTH_END)
    if returncode != 0 or not auth_raw:
        logger.error(f"[米家] 登录子进程失败，退出码 {returncode}")
        raise MijiaLoginError("登录失败，请重新发起登录")
    auth_data = json.loads(auth_raw)
    if not isinstance(auth_data, dict):
        raise MijiaLoginError("登录返回的凭据格式异常")
    return json.dumps(auth_data, ensure_ascii=False)
