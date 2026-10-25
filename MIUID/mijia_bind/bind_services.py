"""米家账号登录、登出与查看。"""

import json
import tempfile
from pathlib import Path

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from ..utils.api.mijia_login import MijiaLoginError, start_qr_login, wait_qr_login
from ..utils.database.model_mijia_user import MijiaUser
from ..utils.render.mijia_qr import render_qr_png


async def login(bot: Bot, ev: Event) -> None:
    with tempfile.TemporaryDirectory(prefix="mijia-login-") as temp_dir:
        auth_path = Path(temp_dir) / "auth.json"
        try:
            session = await start_qr_login(auth_path)
        except MijiaLoginError as exc:
            await bot.send(str(exc))
            return
        recycled = session.login_url is None
        if session.login_url is not None:
            await bot.send(await render_qr_png(session.login_url))
            await bot.send(
                [
                    MessageSegment.at(ev.user_id),
                    MessageSegment.text("请扫描二维码登录米家"),
                ]
            )
        try:
            auth_json = await wait_qr_login(session)
        except MijiaLoginError as exc:
            await bot.send(str(exc))
            return
        auth_data = json.loads(auth_json)
        mijia_user_id = str(auth_data["userId"])
        await MijiaUser.save_auth(
            user_id=ev.user_id,
            mijia_user_id=mijia_user_id,
            auth_json=auth_json,
        )
        await bot.send(
            [
                MessageSegment.at(ev.user_id),
                MessageSegment.text("米家账号登录成功" if not recycled else "米家登录凭证仍有效"),
            ]
        )


async def logout(bot: Bot, ev: Event) -> None:
    count = await MijiaUser.delete_default(ev.user_id)
    if count == 0:
        await bot.send("当前没有默认米家账号")
        return
    await bot.send("已登出默认米家账号")


async def view(bot: Bot, ev: Event) -> None:
    rows = await MijiaUser.get_by_user_id(ev.user_id)
    if not rows:
        await bot.send("当前没有绑定的米家账号")
        return
    lines = ["绑定的米家账号："]
    for index, row in enumerate(rows, start=1):
        mark = "（默认）" if row.is_default else ""
        lines.append(f"{index}. {row.mijia_user_id}{mark}")
    await bot.send("\n".join(lines))
