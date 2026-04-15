"""Phone number masking utility for API responses."""


def mask_phone(phone: str | None) -> str | None:
    """
    Mask phone number: show first 4 + last 3 digits.
    628527078xxxx → 6285***2220
    """
    if not phone:
        return phone
    phone = str(phone).strip()
    if len(phone) <= 7:
        return phone[:2] + "***" + phone[-1:]
    return phone[:4] + "***" + phone[-3:]
