# File: test_main.py
from copy import deepcopy

import pytest

import main


# =======================================================================
# テスト用の補助関数


def scripted_input(values):
    # 決めておいた順番で値を返す入力関数を作る
    iterator = iter(values)

    def _input(message=""):
        try:
            return next(iterator)
        except StopIteration:
            raise AssertionError(f"入力が足りません（{message}）")

    return _input


def make_hero(
    name="勇者",
    maxhp=100,
    maxmp=30,
    attack_power=20,
    speed=10,
    inputs=(),
    inventory=None,
):
    if inventory is None:
        inventory = main.Inventory(deepcopy(main.items))

    return main.Hero(
        name,
        maxhp,
        maxmp,
        attack_power,
        inventory,
        speed=speed,
        input_func=scripted_input(inputs),
    )


def make_monster(name="スライム", maxhp=100, attack_power=10, speed=10):
    # 相手は必ず先頭のキャラ、技は必ず通常攻撃（id 0）を選ぶモンスター
    return main.Monster(
        name,
        maxhp,
        attack_power,
        main.slime_attacks,
        speed=speed,
        target_selector=lambda candidates: candidates[0],
        attack_chooser=lambda attacks, hp_ratio: 0,
    )


# =======================================================================
# ダメージと防御


def test_take_damage_reduces_hp():
    hero = make_hero(maxhp=100)

    hero.take_damage(30)

    assert hero.hp == 70


def test_hp_does_not_go_below_zero():
    hero = make_hero(maxhp=100)

    hero.take_damage(999)

    assert hero.hp == 0


def test_defend_halves_damage_rounded_up():
    hero = make_hero(maxhp=100)
    hero.defend()

    hero.take_damage(15)

    assert hero.hp == 92  # (15 + 1) // 2 = 8


def test_start_turn_cancels_defend():
    hero = make_hero()
    hero.defend()

    hero.start_turn()

    assert hero.is_defending is False


# =======================================================================
# 回復と蘇生


def test_heal_hp_does_not_exceed_maxhp():
    hero = make_hero(maxhp=100)
    hero.hp = 50

    healed = hero.heal_hp(80)

    assert healed == 50
    assert hero.hp == 100


def test_heal_hp_does_not_revive_fallen():
    hero = make_hero()
    hero.hp = 0

    healed = hero.heal_hp(50)

    assert healed == 0
    assert hero.hp == 0


def test_revive_restores_hp_and_clears_status():
    hero = make_hero(maxhp=100)
    hero.status["poison_turn"] = 3
    hero.hp = 0

    assert hero.revive(50) is True
    assert hero.hp == 50
    assert hero.status["poison_turn"] == 0


def test_revive_fails_if_alive():
    hero = make_hero()

    assert hero.revive(50) is False


# =======================================================================
# 状態異常


def test_apply_status_keeps_longer_turn():
    hero = make_hero()

    hero.apply_status("poison_turn", 3)
    hero.apply_status("poison_turn", 1)

    assert hero.status["poison_turn"] == 3


def test_paralysis_blocks_action():
    hero = make_hero(maxhp=100)
    hero.status["paralysis_turn"] = 1

    can_act = hero.check_debuff()

    assert can_act is False
    assert hero.hp == 95
    assert hero.status["paralysis_turn"] == 0


def test_poison_does_not_block_action():
    hero = make_hero(maxhp=100)
    hero.status["poison_turn"] = 3

    can_act = hero.check_debuff()

    assert can_act is True
    assert hero.hp == 85
    assert hero.status["poison_turn"] == 2


def test_burn_halves_attack_power():
    hero = make_hero(attack_power=20)
    hero.status["burn_turn"] = 3

    assert hero.get_attack_power() == 10


# =======================================================================
# レベルアップとMP


@pytest.mark.parametrize(
    ("exp", "expected_level"),
    [
        (29, 1),  # 30に届かない
        (30, 2),  # ちょうど届く
        (90, 3),  # Lv1→2で30、Lv2→3で60
    ],
)
def test_gain_exp_levels_up(exp, expected_level):
    hero = make_hero()

    hero.gain_exp(exp)

    assert hero.level == expected_level


def test_level_up_increases_stats():
    hero = make_hero(maxhp=100, attack_power=20)

    hero.gain_exp(30)

    assert hero.maxhp == 120
    assert hero.attack_power == 24


def test_use_mp_fails_when_not_enough():
    hero = make_hero(maxmp=5)

    assert hero.use_mp(10) is False
    assert hero.mp == 5


# =======================================================================
# アイテム


def test_inventory_get_returns_none_for_unknown_item():
    inventory = main.Inventory(deepcopy(main.items))

    assert inventory.get(999) is None


def test_potion_heals_and_is_consumed():
    hero = make_hero(maxhp=100, inputs=[0, 0])  # 回復薬 → 自分
    hero.hp = 50

    result = hero.choose_item([hero])

    assert result is True
    assert hero.hp == 80
    assert hero.inventory.items[0]["count"] == 2


def test_potion_is_not_consumed_when_hp_is_full(capsys):
    hero = make_hero(inputs=[0, 0, -1])  # 回復薬 → 自分 → 失敗したので戻る

    result = hero.choose_item([hero])

    assert result is False
    assert hero.inventory.items[0]["count"] == 3
    assert "すでにHPは最大です" in capsys.readouterr().out


def test_revival_potion_revives_fallen_ally():
    inventory = main.Inventory(deepcopy(main.items))
    hero = make_hero(inputs=[4, 1], inventory=inventory)  # 蘇生薬 → 戦士
    warrior = make_hero(name="戦士", maxhp=150, inventory=inventory)
    warrior.hp = 0

    result = hero.choose_item([hero, warrior])

    assert result is True
    assert warrior.hp == 75
    assert inventory.items[4]["count"] == 0


# =======================================================================
# 魔法


def test_fire_deals_damage_and_burns(fixed_damage, always_hit):
    hero = make_hero(maxmp=30, attack_power=20, inputs=[2, 0])  # ファイア → 敵0
    monster = make_monster(maxhp=100)

    result = hero.choose_magic_action([monster], [hero])

    assert result is True
    assert monster.hp == 74  # round(20 × 1.3) = 26
    assert monster.status["burn_turn"] == 3
    assert hero.mp == 20


def test_heal_does_not_use_mp_when_hp_is_full():
    hero = make_hero(maxmp=30, inputs=[4, 0, -1])  # ヒール → 自分 → 戻る

    result = hero.choose_magic_action([], [hero])

    assert result is False
    assert hero.mp == 30


# =======================================================================
# 戦闘の進行


@pytest.mark.parametrize(
    ("player_hp", "monster_hp", "expected"),
    [
        (10, 10, None),
        (10, 0, "players"),
        (0, 10, "monsters"),
        (0, 0, "draw"),
    ],
)
def test_get_battle_result(player_hp, monster_hp, expected):
    hero = make_hero()
    monster = make_monster()
    hero.hp = player_hp
    monster.hp = monster_hp

    assert main.get_battle_result([hero], [monster]) == expected


def test_turn_order_is_by_speed_and_skips_fallen():
    fast = make_hero(name="速い", speed=20)
    slow = make_hero(name="遅い", speed=5)
    fallen = make_monster(name="倒れた", speed=99)
    fallen.hp = 0

    order = main.get_turn_order([slow, fast], [fallen])

    assert order == [fast, slow]


def test_lowest_hp_ratio_target_is_selected():
    healthy = make_hero(maxhp=100)
    wounded = make_hero(maxhp=200)
    wounded.hp = 50  # 25%

    assert main.select_lowest_hp_ratio_target([healthy, wounded]) is wounded


def test_choose_action_defend():
    hero = make_hero(inputs=[3])

    assert hero.choose_action([], [hero]) is True
    assert hero.is_defending is True


def test_battle_players_win(fixed_damage):
    hero = make_hero(attack_power=100, speed=15, inputs=[0, 0])  # 攻撃 → 敵0
    monster = make_monster(maxhp=50, speed=10)

    assert main.battle([hero], [monster]) == "players"


def test_battle_monsters_win(fixed_damage):
    hero = make_hero(maxhp=10, speed=5)
    monster = make_monster(attack_power=50, speed=20)

    assert main.battle([hero], [monster]) == "monsters"
