"""JJJ拡張による建研由来コードの変更箇所を示す内部マーカー。"""


# NOTE: オリジンが更新されたときに改変コードの追従対応を判断するためのラベル


def jjj_cloning(func):
    """pyhees関数をJJJ拡張側へ複製改変したことを示す。"""
    return func


def jjj_cloned(func):
    """pyhees内でJJJ拡張により複製改変したことを示す。"""
    return func


def jjj_mod(func):
    """pyhees内でJJJ拡張により直接改変したことを示す。"""
    return func
