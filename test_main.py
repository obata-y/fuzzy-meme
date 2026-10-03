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
    magic_power=20,
    defense=0,
    magic_defense=0,
    luck=0,
    speed=10,
    inputs=(),
    inventory=None,
):
    # 防御力と運は0にして、テストの結果に影響しないようにする
    if inventory is None:
        inventory = main.Inventory(deepcopy(main.items))

    return main.Hero(
        name,
        maxhp,
        maxmp,
        inventory,
        attack_power=attack_power,
        magic_power=magic_power,
        defense=defense,
        magic_defense=magic_defense,
        luck=luck,
        speed=speed,
        input_func=scripted_input(inputs),
    )


def make_monster(
    name="スライム",
    maxhp=100,
    attack_power=10,
    magic_power=10,
    defense=0,
    magic_defense=0,
    luck=0,
    speed=10,
    attacks=None,
):
    # 相手は必ず先頭のキャラ、技は必ず attacks の最初のものを選ぶモンスター
    if attacks is None:
        attacks = main.slime_attacks

    return main.Monster(
        name,
        maxhp,
        attacks,
        attack_power=attack_power,
        magic_power=magic_power,
        defense=defense,
        magic_defense=magic_defense,
        luck=luck,
        speed=speed,
        target_selector=lambda candidates: candidates[0],
        attack_chooser=lambda attacks, hp_ratio: next(iter(attacks)),
    )


# =======================================================================
# ダメージと防御（防御力を無視するダメージ）


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


def test_status_damage_ignores_defense():
    hero = make_hero(maxhp=100, defense=100, magic_defense=100)
    hero.status["poison_turn"] = 3

    hero.check_debuff()

    assert hero.hp == 85  # 毒の15ダメージがそのまま入る


def test_burn_halves_only_physical():
    hero = make_hero(attack_power=20, magic_power=30)
    hero.status["burn_turn"] = 3

    assert hero.get_attack_damage("physical") == 10
    assert hero.get_attack_damage("magic") == 30


def test_silence_halves_only_magic():
    hero = make_hero(attack_power=20, magic_power=30)
    hero.status["spell_interruption_turn"] = 3

    assert hero.get_attack_damage("physical") == 20
    assert hero.get_attack_damage("magic") == 15


def test_burn_and_silence_together():
    hero = make_hero(attack_power=20, magic_power=30)
    hero.status["burn_turn"] = 3
    hero.status["spell_interruption_turn"] = 3

    assert hero.get_attack_damage("physical") == 10
    assert hero.get_attack_damage("magic") == 15


def test_silence_does_not_block_action_or_deal_damage(capsys):
    hero = make_hero(maxhp=100)
    hero.status["spell_interruption_turn"] = 2

    can_act = hero.check_debuff()

    assert can_act is True
    assert hero.hp == 100
    assert hero.status["spell_interruption_turn"] == 1
    assert "に0のダメージ" not in capsys.readouterr().out

# =======================================================================
# 攻撃力と防御力


def test_get_attack_damage_by_type():
    hero = make_hero(attack_power=30, magic_power=50)

    assert hero.get_attack_damage("physical") == 30
    assert hero.get_attack_damage("magic") == 50


def test_get_attack_damage_is_at_least_one():
    hero = make_hero(magic_power=0)

    assert hero.get_attack_damage("magic") == 1


def test_get_attack_damage_rejects_unknown_type():
    hero = make_hero()

    with pytest.raises(ValueError):
        hero.get_attack_damage("fire")


def test_get_defense_by_type():
    hero = make_hero(defense=20, magic_defense=40)

    assert hero.get_defense("physical") == 20
    assert hero.get_defense("magic") == 40


def test_get_defense_rejects_unknown_type():
    hero = make_hero()

    with pytest.raises(ValueError):
        hero.get_defense("fire")


@pytest.mark.parametrize(
    ("damage", "defense", "expected"),
    [
        (100, 0, 100),   # 防御力0なら減らない
        (100, 25, 80),
        (100, 100, 50),  # 防御力100で半分
        (1, 900, 1),     # どれだけ防御力が高くても1は与える
    ],
)
def test_reduce_by_defense(damage, defense, expected):
    assert main.reduce_by_defense(damage, defense) == expected


def test_physical_damage_uses_defense():
    monster = make_monster(maxhp=100, defense=100, magic_defense=0)

    monster.take_damage(40, "physical")

    assert monster.hp == 80


def test_magic_damage_uses_magic_defense():
    monster = make_monster(maxhp=100, defense=0, magic_defense=100)

    monster.take_damage(40, "magic")

    assert monster.hp == 80


def test_zero_defense_does_not_reduce_damage():
    monster = make_monster(maxhp=200, defense=0)

    monster.take_damage(100, "physical")

    assert monster.hp == 100


def test_defense_and_defend_stack():
    hero = make_hero(maxhp=100, defense=100)
    hero.defend()

    hero.take_damage(40, "physical")

    assert hero.hp == 90  # 防御力で20、身構えてさらに10


# =======================================================================
# ダメージの揺れ幅とクリティカル


def test_calculation_damage_without_fluctuation_or_critical(monkeypatch):
    monkeypatch.setattr(main.random, "randint", lambda a, b: 0)
    monkeypatch.setattr(main.random, "random", lambda: 0.99)
    hero = make_hero(luck=10)

    assert hero.calculation_damage(50) == 50


@pytest.mark.parametrize(
    ("roll", "expected"),
    [
        (-20, 80),   # 揺れ幅の下限
        (20, 120),   # 揺れ幅の上限
    ],
)
def test_calculation_damage_fluctuation(monkeypatch, roll, expected):
    monkeypatch.setattr(main.random, "randint", lambda a, b: roll)
    monkeypatch.setattr(main.random, "random", lambda: 0.99)
    hero = make_hero(luck=0)

    assert hero.calculation_damage(100) == expected


@pytest.mark.parametrize(
    ("luck", "roll", "expected"),
    [
        (10, 0.05, 100),  # 10%の範囲に入ったのでクリティカル
        (10, 0.10, 50),   # ちょうど境目はクリティカルにならない
        (0, 0.0, 50),     # 運0なら絶対にクリティカルにならない
        (100, 0.99, 100), # 運100なら必ずクリティカル
    ],
)
def test_critical_depends_on_luck(monkeypatch, luck, roll, expected):
    monkeypatch.setattr(main.random, "randint", lambda a, b: 0)
    monkeypatch.setattr(main.random, "random", lambda: roll)
    hero = make_hero(luck=luck)

    assert hero.calculation_damage(50) == expected


def test_critical_shows_message(monkeypatch, capsys):
    monkeypatch.setattr(main.random, "randint", lambda a, b: 0)
    monkeypatch.setattr(main.random, "random", lambda: 0.0)
    hero = make_hero(luck=100)

    hero.calculation_damage(50)

    assert "クリティカル" in capsys.readouterr().out


# =======================================================================
# 攻撃・魔法・技の種類


def test_normal_attack_uses_defense(fixed_damage):
    hero = make_hero(attack_power=40)
    monster = make_monster(maxhp=100, defense=100)

    hero.attack(monster)

    assert monster.hp == 80  # 40 × 100 / 200 = 20


def test_normal_attack_uses_attack_power_not_magic_power(fixed_damage):
    hero = make_hero(attack_power=30, magic_power=99)
    monster = make_monster(maxhp=100)

    hero.attack(monster)

    assert monster.hp == 70


def test_fire_uses_magic_power_and_magic_defense(fixed_damage, always_hit):
    # ファイア → 敵0。物理攻撃力と物理防御力は使われないことも確かめる
    hero = make_hero(maxmp=30, attack_power=100, magic_power=20, inputs=[2, 0])
    monster = make_monster(maxhp=100, defense=999, magic_defense=0)

    result = hero.choose_magic_action([monster], [hero])

    assert result is True
    assert monster.hp == 74  # round(20 × 1.3) = 26
    assert monster.status["burn_turn"] == 3
    assert hero.mp == 20


def test_monster_skill_is_physical_by_default(fixed_damage):
    monster = make_monster(attack_power=40)
    hero = make_hero(maxhp=100, defense=100, magic_defense=0)

    monster.use_skill(hero, "体当たり", 1.0)

    assert hero.hp == 80


def test_dragon_breath_is_magic(fixed_damage, always_hit):
    dragon = make_monster(magic_power=20, attacks=main.dragon_attacks)
    hero = make_hero(maxhp=100, defense=999, magic_defense=0)

    main.dragon_attacks[30]["function"](dragon, hero)

    assert hero.hp == 72  # round(20 × 1.4) = 28
    assert hero.status["burn_turn"] == 3


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
    hero = make_hero(maxhp=100, attack_power=20, magic_power=20)

    hero.gain_exp(30)

    assert hero.maxhp == 120
    assert hero.attack_power == 24
    assert hero.magic_power == 24
    assert hero.defense == 2
    assert hero.magic_defense == 2


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


def test_party_shares_inventory_without_changing_master_items():
    party = main.create_party()

    party[0].inventory.consume(0)

    assert all(member.inventory is party[0].inventory for member in party)
    assert party[2].inventory.items[0]["count"] == 2
    assert main.items[0]["count"] == 3  # 元の定義は変わらない


# =======================================================================
# 魔法


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

# =======================================================================
# 定義データ


@pytest.mark.parametrize("key", list(main.status_definitions))
def test_status_definition_has_required_fields(key):
    definition = main.status_definitions[key]

    for field in ("label", "message", "damage", "blocks_action"):
        assert field in definition, f"{key} に {field} がありません"


def test_status_keys_in_magics_and_items_exist():
    for data in list(main.magics.values()) + list(main.items.values()):
        status_key = data["params"].get("status_key")

        if status_key is not None:
            assert status_key in main.status_definitions, data["name"]
