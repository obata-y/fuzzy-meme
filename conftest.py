# File: conftest.py
import pytest

import main


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # すべてのテストで待ち時間をなくす
    monkeypatch.setattr(main.time, "sleep", lambda seconds: None)


@pytest.fixture
def fixed_damage(monkeypatch):
    # 乱数とクリティカルをなくし、ダメージを攻撃力と同じ値にする
    monkeypatch.setattr(main, "calculation_damage", lambda attack_power: attack_power)


@pytest.fixture
def always_hit(monkeypatch):
    # 状態異常が必ず発生するようにする
    monkeypatch.setattr(main.random, "random", lambda: 0.0)
