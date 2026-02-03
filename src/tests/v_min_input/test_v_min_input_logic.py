import pytest
import numpy as np
from jjjexperiment.v_min_input.logic import normalize_V_vent_g_i


def test_基本的な正規化():
    """基本的な正規化のテスト（基本フローで使用される shape (5,) の場合）"""
    # Arrange
    V_vent_g_i = np.array([100, 200, 300, 200, 100])  # shape (5,)
    V_hs_min = 1000.0

    # Act
    result = normalize_V_vent_g_i(V_vent_g_i, V_hs_min)

    # Assert
    assert np.isclose(result.sum(), V_hs_min)  # 合計が最低風量に等しい
    assert result.shape == (5,)  # 形状が維持されている
    assert np.isclose(result[0] / result[1], V_vent_g_i[0] / V_vent_g_i[1])  # 比率が維持されている


def test_全て同じ値の場合():
    """全て同じ値の場合のテスト"""
    # Arrange
    V_vent_g_i = np.array([100, 100, 100, 100, 100])  # shape (5,)
    V_hs_min = 500.0

    # Act
    result = normalize_V_vent_g_i(V_vent_g_i, V_hs_min)

    # Assert
    assert np.allclose(result, 100.0)  # 全て均等に分配される
    assert np.isclose(result.sum(), V_hs_min)


def test_サブケース_2次元配列():
    """サブケース: shape (5, 1) の2次元配列にも対応していることを確認"""
    # Arrange
    V_vent_g_i = np.array([[100], [200], [300], [200], [100]])  # shape (5, 1)
    V_hs_min = 1000.0

    # Act
    result = normalize_V_vent_g_i(V_vent_g_i, V_hs_min)

    # Assert
    assert np.isclose(result.sum(), V_hs_min)  # 合計が最低風量に等しい
    assert result.shape == (5, 1)  # 形状が維持されている
    assert np.isclose(result[0, 0] / result[1, 0], V_vent_g_i[0, 0] / V_vent_g_i[1, 0])  # 比率が維持されている


def test_一部がゼロの場合():
    """一部がゼロの場合のテスト"""
    # Arrange
    V_vent_g_i = np.array([0, 200, 300, 0, 100])  # shape (5,)
    V_hs_min = 600.0

    # Act
    result = normalize_V_vent_g_i(V_vent_g_i, V_hs_min)

    # Assert
    assert result[0] == 0  # ゼロはゼロのまま
    assert result[3] == 0
    assert np.isclose(result.sum(), V_hs_min)  # 合計が最低風量に等しい


def test_形状が不正な場合():
    """形状が不正な場合のテスト"""
    # Arrange
    V_vent_g_i = np.array([100, 200, 300])  # 1次元配列
    V_hs_min = 600.0

    # Act & Assert
    with pytest.raises(AssertionError):
        normalize_V_vent_g_i(V_vent_g_i, V_hs_min)


def test_負の値が含まれる場合():
    """負の値が含まれる場合のテスト"""
    # Arrange
    V_vent_g_i = np.array([100, 200, -50, 200, 100])  # shape (5,)
    V_hs_min = 550.0

    # Act & Assert
    with pytest.raises(AssertionError):
        normalize_V_vent_g_i(V_vent_g_i, V_hs_min)


def test_全てゼロの場合():
    """全てゼロの場合のテスト"""
    # Arrange
    V_vent_g_i = np.array([0, 0, 0, 0, 0])  # shape (5,)
    V_hs_min = 500.0

    # Act & Assert
    with pytest.raises(AssertionError):
        normalize_V_vent_g_i(V_vent_g_i, V_hs_min)


def test_最低風量がゼロの場合():
    """最低風量がゼロの場合のテスト"""
    # Arrange
    V_vent_g_i = np.array([100, 200, 300, 200, 100])  # shape (5,)
    V_hs_min = 0.0

    # Act & Assert
    with pytest.raises(AssertionError):
        normalize_V_vent_g_i(V_vent_g_i, V_hs_min)
