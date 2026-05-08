import qrcode
from qrcode.image.svg import SvgPathImage


def generate_qr_svg(url: str, *, scale: int = 8) -> str:
    qr = qrcode.QRCode(box_size=scale, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    return img.to_string(encoding="unicode")
