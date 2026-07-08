from PySide6.QtGui import QColor


def relative_luminance(color):
    def channel(value):
        value = value / 255
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(color.red())
        + 0.7152 * channel(color.green())
        + 0.0722 * channel(color.blue())
    )


def contrast_ratio(first, second):
    first_luminance = relative_luminance(first)
    second_luminance = relative_luminance(second)
    lighter = max(first_luminance, second_luminance)
    darker = min(first_luminance, second_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def readable_foreground(background, preferred=None):
    dark = QColor("#111827")
    light = QColor("#FFFFFF")
    if preferred is not None and preferred.isValid():
        if contrast_ratio(background, preferred) >= 4.5:
            return preferred
    return (
        dark
        if contrast_ratio(background, dark) >= contrast_ratio(background, light)
        else light
    )


def apply_readable_item_colors(item, background, preferred_foreground=None):
    if not background.isValid():
        return
    item.setBackground(background)
    item.setForeground(readable_foreground(background, preferred_foreground))


__all__ = [
    "apply_readable_item_colors",
    "contrast_ratio",
    "readable_foreground",
    "relative_luminance",
]
