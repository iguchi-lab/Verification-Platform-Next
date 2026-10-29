"""Resolve seasonal floor-air paths, retaining the legacy common selector."""


def underfloor_enabled(data, season=None):
    if season is None:
        # Evaluate both selectors so an invalid disabled-side value cannot hide.
        heating = underfloor_enabled(data, "H")
        cooling = underfloor_enabled(data, "C")
        return heating or cooling
    if season not in ("H", "C"):
        raise ValueError("床下空調の季節は H または C を指定してください。")
    key = f"change_underfloor_temperature_{season}"
    value = data.get(key, data.get("change_underfloor_temperature", 1))
    if isinstance(value, bool) or str(value) not in ("1", "2"):
        raise ValueError(f"{key} は 1（使用しない）または 2（使用する）を指定してください。")
    return str(value) == "2"
