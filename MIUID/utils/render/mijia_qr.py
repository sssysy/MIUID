"""米家登录二维码渲染。"""

from io import BytesIO

import qrcode


async def render_qr_png(content: str) -> bytes:
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(content)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
