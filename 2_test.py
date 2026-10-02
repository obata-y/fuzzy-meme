# File: 2_test.py
import importlib
from copy import deepcopy
from unittest.mock import Mock, patch


# 数字で始まるモジュール名はimportlibで読み込む。
# ゲーム側の関数をモックにするときも、このgameを指定する。
game = importlib.import_module("1_main")


# =======================================================================
# テスト用の共通確認


def assert_same_objects(actual, expected):
    """リストの要素が、同じオブジェクト・同じ順序か確認する。"""
    assert len(actual) == len(expected), "一覧の長さが違います"

    assert all(
        current is original
        for current, original in zip(actual, expected)
    ), "一覧の要素・順序が違います"


def make_status(**turns):
    """期待する状態の辞書を作る。書かなかった状態異常は0になる。"""
    status = {
        key: 0
        for key in game.status_definitions
    }

    for key, turn in turns.items():
        assert key in status, f"未登録の状態異常です：{key}"
        status[key] = turn

    return status

# =======================================================================
# 対象選択・状態異常・防御


def test_monster_choose_target():
    fallen = game.Player("戦闘不能のキャラクター", 100, 10)
    fallen.hp = 0

    survivor = game.Player("生存者", 100, 10)
    monster = game.Monster("テスト用モンスター", 50, 10, {})

    target = monster.choose_target([fallen, survivor])

    assert target is survivor, "生存者が選ばれていません"
    assert monster.choose_target([fallen]) is None
    assert monster.choose_target([]) is None


def test_apply_status():
    # 現在ターン数、追加ターン数、期待ターン数
    cases = [
        (0, 3, 3),
        (1, 3, 3),
        (5, 3, 5),
        (3, 3, 3),
    ]

    for current, added, expected in cases:
        player = game.Player("状態異常テスト", 100, 10)
        player.status["poison_turn"] = current

        success = player.apply_status("poison_turn", added)

        assert success is True
        assert player.status["poison_turn"] == expected, (
            f"現在={current}、追加={added}、"
            f"期待={expected}、実際={player.status['poison_turn']}"
        )


def test_apply_status_rejected():
    cases = [
        (0, "poison_turn", 3),
        (100, "unknown_status", 3),
        (100, "poison_turn", 0),
        (100, "poison_turn", -1),
    ]

    for hp, key, turns in cases:
        player = game.Player("状態異常拒否テスト", 100, 10)
        player.hp = hp
        player.status["poison_turn"] = 2
        player.status["paralysis_turn"] = 1

        before = player.status.copy()
        success = player.apply_status(key, turns)

        assert success is False
        assert player.status == before, (
            f"拒否したのに状態が変わりました：{key}, {turns}"
        )
        assert player.hp == hp


def test_debuff():
    # 開始HP、麻痺、毒、期待行動可否、期待HP、期待麻痺、期待毒
    cases = [
        (100, 0, 0, True, 100, 0, 0),
        (100, 0, 3, True, 85, 0, 2),
        (100, 1, 0, False, 95, 0, 0),
        (100, 1, 3, False, 80, 0, 2),
        (5, 1, 3, False, 0, 0, 3),
        (0, 3, 3, False, 0, 3, 3),
    ]

    with patch.object(game.time, "sleep"):
        for (
            hp,
            paralysis,
            poison,
            expected_can_act,
            expected_hp,
            expected_paralysis,
            expected_poison,
        ) in cases:
            player = game.Player("状態異常処理テスト", 100, 10)
            player.hp = hp
            player.status["paralysis_turn"] = paralysis
            player.status["poison_turn"] = poison

            can_act = player.check_debuff()

            assert can_act is expected_can_act
            assert player.hp == expected_hp
            assert player.status == make_status(
                poison_turn=expected_poison, paralysis_turn=expected_paralysis
            )


def test_defend():
    # 開始HP、防御するか、ダメージ、期待HP
    cases = [
        (100, False, 10, 90),
        (100, True, 10, 95),
        (100, True, 5, 97),
        (2, True, 10, 0),
    ]

    for hp, defending, damage, expected_hp in cases:
        player = game.Player("防御テスト", 100, 10)
        player.hp = hp

        assert player.is_defending is False

        if defending:
            player.defend()

        player.take_damage(damage)

        assert player.hp == expected_hp
        assert player.is_defending is defending

    player = game.Player("連続被弾テスト", 100, 10)
    player.defend()
    player.take_damage(10)
    player.take_damage(10)

    assert player.hp == 90
    assert player.is_defending is True

    player = game.Player("防御解除テスト", 100, 10)
    player.defend()
    player.start_turn()

    assert player.is_defending is False

    player.take_damage(10)
    assert player.hp == 90


# =======================================================================
# HP・MP・回復魔法


def test_heal_hp():
    # 開始HP、回復指定量、期待HP、実際の回復量
    cases = [
        (50, 30, 80, 30),
        (90, 30, 100, 10),
        (100, 30, 100, 0),
        (50, 0, 50, 0),
    ]

    for hp, amount, expected_hp, expected_amount in cases:
        player = game.Player("回復テスト", 100, 10)
        player.hp = hp

        actual = player.heal_hp(amount)

        assert actual == expected_amount
        assert player.hp == expected_hp


def test_use_mp():
    cases = [
        (0, True, 10),
        (8, True, 2),
        (10, True, 0),
        (11, False, 10),
        (-1, False, 10),
    ]

    for cost, expected_success, expected_mp in cases:
        player = game.Hero(
            "MPテスト", 200, 10, 10, game.Inventory({})
        )

        success = player.use_mp(cost)

        assert success is expected_success
        assert player.mp == expected_mp


def test_heal_magic_self():
    # 開始HP、開始MP、期待成否、期待HP、期待MP
    cases = [
        (100, 8, True, 150, 0),
        (190, 8, True, 200, 0),
        (200, 8, False, 200, 8),
        (100, 7, False, 100, 7),
    ]

    for hp, mp, expected_success, expected_hp, expected_mp in cases:
        player = game.Hero(
            "自己回復テスト", 200, 10, 10, game.Inventory({})
        )
        player.hp = hp
        player.mp = mp

        success = player.heal_magic(player)

        assert success is expected_success
        assert player.hp == expected_hp
        assert player.mp == expected_mp


def test_heal_magic():
    # 使用者HP、使用者MP、対象HP、期待成否、期待使用者MP、期待対象HP
    cases = [
        (120, 8, 100, True, 0, 150),
        (200, 8, 200, False, 8, 200),
        (200, 8, 0, False, 8, 0),
        (200, 7, 100, False, 7, 100),
    ]

    for (
        caster_hp,
        caster_mp,
        target_hp,
        expected_success,
        expected_mp,
        expected_hp,
    ) in cases:
        inventory = game.Inventory({})
        caster = game.Hero("使用者", 200, 10, 10, inventory)
        target = game.Hero("回復対象", 200, 10, 10, inventory)

        caster.hp = caster_hp
        caster.mp = caster_mp
        target.hp = target_hp
        target.mp = 0

        success = caster.heal_magic(target)

        assert success is expected_success
        assert caster.hp == caster_hp
        assert caster.mp == expected_mp
        assert target.hp == expected_hp
        assert target.mp == 0


def test_clear_status():
    # ケース名、HP、キー、毒、麻痺、期待成否、期待毒、期待麻痺
    cases = [
        ("毒解除", 100, "poison_turn", 3, 0, True, 0, 0),
        ("麻痺解除", 100, "paralysis_turn", 0, 1, True, 0, 0),
        ("麻痺を残す", 100, "poison_turn", 3, 1, True, 0, 1),
        ("毒を残す", 100, "paralysis_turn", 3, 1, True, 3, 0),
        ("未登録", 100, "unknown_status", 3, 1, False, 3, 1),
        ("残り0", 100, "poison_turn", 0, 1, False, 0, 1),
        ("残り負数", 100, "poison_turn", -1, 1, False, -1, 1),
        ("戦闘不能", 0, "poison_turn", 3, 1, False, 3, 1),
    ]

    for (
        label,
        hp,
        key,
        poison,
        paralysis,
        expected_success,
        expected_poison,
        expected_paralysis,
    ) in cases:
        player = game.Player("解除テスト", 100, 10)
        player.hp = hp
        player.status["poison_turn"] = poison
        player.status["paralysis_turn"] = paralysis

        success = player.clear_status(key)

        assert success is expected_success, label
        assert player.hp == hp, label
        assert player.status == make_status(
            poison_turn=expected_poison, paralysis_turn=expected_paralysis
        ), label


def test_cure_magic():
    # ケース名、使用者MP、対象HP、毒、麻痺、期待成否、期待MP、期待毒
    cases = [
        ("毒治療", 5, 100, 3, 0, True, 0, 0),
        ("毒なし", 5, 100, 0, 0, False, 5, 0),
        ("MP不足", 4, 100, 3, 0, False, 4, 3),
        ("戦闘不能", 5, 0, 3, 0, False, 5, 3),
        ("麻痺を残す", 5, 100, 3, 1, True, 0, 0),
        ("麻痺だけ", 5, 100, 0, 1, False, 5, 0),
    ]

    for (
        label,
        caster_mp,
        target_hp,
        poison,
        paralysis,
        expected_success,
        expected_mp,
        expected_poison,
    ) in cases:
        inventory = game.Inventory({})
        caster = game.Hero("使用者", 200, 10, 10, inventory)
        target = game.Hero("治療対象", 200, 10, 10, inventory)

        caster.hp = 120
        caster.mp = caster_mp
        target.hp = target_hp
        target.mp = 7
        target.status["poison_turn"] = poison
        target.status["paralysis_turn"] = paralysis

        caster_status = caster.status.copy()
        success = caster.cure_magic(target)

        assert success is expected_success, label
        assert caster.mp == expected_mp, label
        assert caster.hp == 120, label
        assert caster.status == caster_status, label
        assert target.hp == target_hp, label
        assert target.mp == 7, label
        assert target.status == make_status(
            poison_turn=expected_poison, paralysis_turn=paralysis
        ), label


def test_cure_magic_self():
    player = game.Hero(
        "自己治療テスト", 200, 10, 10, game.Inventory({})
    )
    player.hp = 120
    player.status["poison_turn"] = 3
    player.status["paralysis_turn"] = 1

    success = player.cure_magic(player)

    assert success is True
    assert player.mp == 5
    assert player.hp == 120
    assert player.status == make_status(
        poison_turn=0, paralysis_turn=1
    )

    success = player.cure_magic(player)

    assert success is False
    assert player.mp == 5
    assert player.hp == 120
    assert player.status == make_status(
        poison_turn=0, paralysis_turn=1
    )


# =======================================================================
# ポイズン


def test_poison_magic():
    # ケース名、MP、対象HP、毒、期待成否、期待MP、期待HP、期待毒
    cases = [
        ("通常使用", 6, 50, 0, True, 0, 40, 3),
        ("MP不足", 5, 50, 0, False, 5, 50, 0),
        ("戦闘不能", 6, 0, 2, False, 6, 0, 2),
        ("毒延長", 6, 50, 1, True, 0, 40, 3),
        ("毒を短縮しない", 6, 50, 5, True, 0, 40, 5),
        ("過剰ダメージで倒す", 6, 5, 0, True, 0, 0, 0),
        ("ちょうどHP0", 6, 10, 0, True, 0, 0, 0),
        ("MPに余裕あり", 10, 50, 0, True, 4, 40, 3),
    ]

    with patch.object(
        game,
        "calculation_damage",
        return_value=20,
    ) as damage_mock, patch.object(game.time, "sleep"):
        for (
            label,
            mp,
            hp,
            poison,
            expected_success,
            expected_mp,
            expected_hp,
            expected_poison,
        ) in cases:
            caster = game.Hero(
                "使用者", 200, 10, 20, game.Inventory({})
            )
            caster.hp = 120
            caster.mp = mp
            caster_status = caster.status.copy()

            target = game.Monster("対象", 50, 10, {})
            target.hp = hp
            target.status["poison_turn"] = poison
            target.status["paralysis_turn"] = 1

            damage_mock.reset_mock()

            success = caster.poison_magic(target)

            assert success is expected_success, label
            assert caster.mp == expected_mp, label
            assert caster.hp == 120, label
            assert caster.status == caster_status, label
            assert target.hp == expected_hp, label
            assert target.status == make_status(
                poison_turn=expected_poison, paralysis_turn=1
            ), label

            if expected_success:
                damage_mock.assert_called_once_with(
                    caster.attack_power
                )
            else:
                damage_mock.assert_not_called()


def test_monster_poison_turn():
    cases = [
        (50, 35, True),
        (15, 0, False),
        (10, 0, False),
    ]

    with patch.object(game.time, "sleep"):
        for hp, expected_hp, expected_can_act in cases:
            monster = game.Monster("毒テスト敵", 50, 10, {})
            monster.hp = hp

            applied = monster.apply_status("poison_turn", 3)
            assert applied is True

            monster.defend()
            monster.start_turn()

            assert monster.is_defending is False

            can_act = monster.check_debuff()

            assert can_act is expected_can_act
            assert monster.hp == expected_hp
            assert monster.status == make_status(
                poison_turn=2
            )


# =======================================================================
# 勝敗・行動順


def test_get_battle_result():
    cases = [
        ("両方生存", [100], [100], None),
        ("味方勝利", [100], [0], "players"),
        ("敵勝利", [0], [100], "monsters"),
        ("両方全滅", [0], [0], "draw"),
        ("両方空", [], [], "draw"),
        ("敵が空", [100], [], "players"),
        ("味方が空", [], [100], "monsters"),
        ("生死混在", [0, 100], [100, 0], None),
        ("敵全滅", [0, 100], [0, 0], "players"),
        ("味方全滅", [0, 0], [0, 100], "monsters"),
        ("味方全滅・敵空", [0], [], "draw"),
        ("味方空・敵全滅", [], [0], "draw"),
    ]

    for label, player_hps, monster_hps, expected in cases:
        players = []
        monsters = []

        for index, hp in enumerate(player_hps):
            player = game.Player(f"味方{index}", 100, 10)
            player.hp = hp
            players.append(player)

        for index, hp in enumerate(monster_hps):
            monster = game.Monster(f"敵{index}", 100, 10, {})
            monster.hp = hp
            monsters.append(monster)

        players_before = players.copy()
        monsters_before = monsters.copy()

        result = game.get_battle_result(players, monsters)

        assert result == expected, label
        assert_same_objects(players, players_before)
        assert_same_objects(monsters, monsters_before)
        assert [player.hp for player in players] == player_hps
        assert [monster.hp for monster in monsters] == monster_hps


def test_battle_already_finished():
    player = game.Hero(
        "勇者", 100, 10, 10, game.Inventory({})
    )

    with patch.object(game.time, "sleep"), patch(
        "builtins.input",
        side_effect=AssertionError(
            "決着済みなのに入力を要求しました"
        ),
    ), patch.object(
        game,
        "process_turn",
    ) as turn_mock:
        result = game.battle([player], [])

        assert result == "players"
        turn_mock.assert_not_called()


def test_get_turn_order():
    # 各キャラクターは「名前、素早さ、HP」
    cases = [
        (
            "敵味方混在",
            [("勇者", 15, 100), ("戦士", 8, 100)],
            [
                ("スライムA", 10, 50),
                ("スライムB", 6, 50),
                ("ゴブリンA", 18, 50),
            ],
            ["ゴブリンA", "勇者", "スライムA", "戦士", "スライムB"],
        ),
        (
            "同速",
            [("味方A", 10, 100), ("味方B", 10, 100)],
            [("敵A", 10, 50), ("敵B", 10, 50)],
            ["味方A", "味方B", "敵A", "敵B"],
        ),
        (
            "戦闘不能除外",
            [("倒れた味方", 100, 0), ("生存味方", 10, 100)],
            [("倒れた敵", 200, 0), ("生存敵", 20, 50)],
            ["生存敵", "生存味方"],
        ),
        ("両方空", [], [], []),
        (
            "敵が空",
            [("遅い味方", 5, 100), ("速い味方", 15, 100)],
            [],
            ["速い味方", "遅い味方"],
        ),
        (
            "味方が空",
            [],
            [("遅い敵", 5, 50), ("速い敵", 15, 50)],
            ["速い敵", "遅い敵"],
        ),
        (
            "全員戦闘不能",
            [("倒れた味方", 10, 0)],
            [("倒れた敵", 20, 0)],
            [],
        ),
    ]

    for label, player_specs, monster_specs, expected_names in cases:
        inventory = game.Inventory({})
        players = []
        monsters = []

        for name, speed, hp in player_specs:
            player = game.Hero(
                name, 100, 10, 10, inventory, speed=speed
            )
            player.hp = hp
            players.append(player)

        for name, speed, hp in monster_specs:
            monster = game.Monster(
                name, 100, 10, {}, speed=speed
            )
            monster.hp = hp
            monsters.append(monster)

        players_before = players.copy()
        monsters_before = monsters.copy()
        characters = players + monsters

        originals = {
            character.name: character
            for character in characters
        }

        states_before = [
            (
                character.hp,
                character.speed,
                character.is_defending,
                character.status.copy(),
            )
            for character in characters
        ]

        order = game.get_turn_order(players, monsters)

        assert isinstance(order, list)
        assert [character.name for character in order] == expected_names, label

        for character, name in zip(order, expected_names):
            assert character is originals[name], label

        assert_same_objects(players, players_before)
        assert_same_objects(monsters, monsters_before)

        for character, before in zip(characters, states_before):
            after = (
                character.hp,
                character.speed,
                character.is_defending,
                character.status,
            )
            assert after == before, label


def test_speed_initialization():
    inventory = game.Inventory({})

    default_characters = [
        game.Player("基本キャラ", 100, 10),
        game.Hero("勇者", 100, 10, 10, inventory),
        game.Monster("敵", 100, 10, {}),
    ]

    for character in default_characters:
        assert character.speed == 10

    custom_characters = [
        game.Player("基本キャラ", 100, 10, speed=12),
        game.Hero("勇者", 100, 10, 10, inventory, speed=15),
        game.Monster("敵", 100, 10, {}, speed=18),
    ]

    for character, expected in zip(
        custom_characters,
        [12, 15, 18],
    ):
        assert character.speed == expected


# =======================================================================
# 初期メンバー・ゲーム間の独立


def test_create_battle_members_initial_state():
    players, monsters = game.create_battle_members()

    assert isinstance(players, list)
    assert isinstance(monsters, list)
    assert len(players) == 2
    assert len(monsters) == 3

    expected_players = [
        ("勇者", 200, 30, 20, 15),
        ("戦士", 150, 0, 40, 8),
    ]

    for player, expected in zip(players, expected_players):
        assert isinstance(player, game.Hero)
        assert (
            player.name,
            player.maxhp,
            player.maxmp,
            player.attack_power,
            player.speed,
        ) == expected
        assert player.mp == player.maxmp

    expected_monsters = [
        ("スライムA", 50, 10, 10, game.slime_attacks),
        ("スライムB", 70, 8, 6, game.slime_attacks),
        ("ゴブリンA", 80, 15, 18, game.gobrin_attacks),
    ]

    for monster, expected in zip(monsters, expected_monsters):
        name, maxhp, attack_power, speed, attacks = expected

        assert isinstance(monster, game.Monster)
        assert (
            monster.name,
            monster.maxhp,
            monster.attack_power,
            monster.speed,
        ) == (name, maxhp, attack_power, speed)
        assert monster.attacks is attacks

    for character in players + monsters:
        assert character.hp == character.maxhp
        assert character.is_defending is False
        assert character.status == make_status()
    inventory = players[0].inventory

    assert isinstance(inventory, game.Inventory)
    assert inventory.items == game.items
    assert inventory.items[0]["count"] == 3
    assert inventory.items[1]["count"] == 1

    order = game.get_turn_order(players, monsters)

    assert [character.name for character in order] == [
        "ゴブリンA",
        "勇者",
        "スライムA",
        "戦士",
        "スライムB",
    ]


def test_create_battle_members_independence():
    items_before = deepcopy(game.items)

    players1, monsters1 = game.create_battle_members()
    players2, monsters2 = game.create_battle_members()

    inventory1 = players1[0].inventory
    inventory2 = players2[0].inventory

    assert players1[1].inventory is inventory1
    assert players2[1].inventory is inventory2

    assert players1 is not players2
    assert monsters1 is not monsters2
    assert inventory1 is not inventory2

    for first, second in zip(
        players1 + monsters1,
        players2 + monsters2,
    ):
        assert first is not second
        assert first.status is not second.status

    assert inventory1.items is not inventory2.items

    for inventory in (inventory1, inventory2):
        assert inventory.items is not game.items
        assert inventory.items == items_before

        for item_id in items_before:
            assert inventory.items[item_id] is not game.items[item_id]

    for item_id in items_before:
        assert inventory1.items[item_id] is not inventory2.items[item_id]

    hero1 = players1[0]
    hero2 = players2[0]
    hero1.hp = 100

    success = hero1.use_item(0)

    assert success is True
    assert hero1.hp == 130
    assert inventory1.items[0]["count"] == 2
    assert players1[1].inventory.items[0]["count"] == 2
    assert inventory2.items[0]["count"] == 3

    applied = hero1.apply_status("poison_turn", 3)
    assert applied is True

    hero1.mp = 0
    hero1.is_defending = True

    assert hero1.status["poison_turn"] == 3
    assert hero2.hp == 200
    assert hero2.mp == 30
    assert hero2.is_defending is False
    assert hero2.status == make_status()

    assert game.items == items_before
    assert game.items[0]["count"] == 3


# =======================================================================
# 1人分のターン処理


def test_process_turn():
    # 名前、HP、毒、麻痺、防御、
    # 期待HP、期待毒、期待麻痺、行動するか
    cases = [
        ("通常行動", 50, 0, 0, False, 50, 0, 0, True),
        ("最初から戦闘不能", 0, 3, 0, True, 0, 3, 0, False),
        ("毒で戦闘不能", 15, 3, 0, False, 0, 2, 0, False),
        ("毒でも生存", 50, 3, 0, False, 35, 2, 0, True),
        ("麻痺", 50, 0, 1, False, 45, 0, 0, False),
        ("防御解除後に毒", 50, 3, 0, True, 35, 2, 0, True),
        ("毒と麻痺", 50, 3, 1, False, 30, 2, 0, False),
    ]

    for side in ("players", "monsters"):
        for (
            label,
            hp,
            poison,
            paralysis,
            defending,
            expected_hp,
            expected_poison,
            expected_paralysis,
            should_act,
        ) in cases:
            hero = game.Hero(
                "テスト勇者", 100, 10, 10, game.Inventory({})
            )
            monster = game.Monster("テスト敵", 100, 10, {})

            players = [hero]
            monsters = [monster]

            character = hero if side == "players" else monster
            character.hp = hp
            character.status["poison_turn"] = poison
            character.status["paralysis_turn"] = paralysis
            character.is_defending = defending

            context = f"{side}／{label}"

            with patch.object(
                game.time,
                "sleep",
            ), patch.object(
                hero,
                "choose_action",
                return_value=True,
            ) as hero_action, patch.object(
                monster,
                "act",
            ) as monster_action, patch.object(
                monster,
                "choose_target",
                wraps=monster.choose_target,
            ) as choose_target, patch.object(
                character,
                "check_debuff",
                wraps=character.check_debuff,
            ) as debuff_check, patch.object(
                game,
                "get_battle_result",
                side_effect=AssertionError(
                    "process_turn内で勝敗判定を呼んでいます"
                ),
            ):
                result = game.process_turn(
                    character, players, monsters
                )

                assert result is None, context
                assert character.hp == expected_hp, context
                assert character.is_defending is False, context
                assert character.status == make_status(
                    poison_turn=expected_poison, paralysis_turn=expected_paralysis
                ), context

                if hp <= 0:
                    debuff_check.assert_not_called()
                else:
                    debuff_check.assert_called_once_with()

                if side == "players":
                    monster_action.assert_not_called()
                    choose_target.assert_not_called()

                    if should_act:
                        hero_action.assert_called_once_with(
                            monsters, players
                        )
                    else:
                        hero_action.assert_not_called()

                else:
                    hero_action.assert_not_called()

                    if should_act:
                        choose_target.assert_called_once_with(
                            players
                        )
                        monster_action.assert_called_once_with(
                            hero
                        )
                    else:
                        choose_target.assert_not_called()
                        monster_action.assert_not_called()


def test_process_turn_no_target():
    for label in ("味方一覧が空", "味方全員戦闘不能"):
        monster = game.Monster("テスト敵", 100, 10, {})
        monsters = [monster]

        if label == "味方一覧が空":
            players = []
        else:
            hero = game.Hero(
                "倒れた勇者", 100, 10, 10, game.Inventory({})
            )
            hero.hp = 0
            players = [hero]

        with patch.object(
            game.time,
            "sleep",
        ), patch.object(
            monster,
            "act",
        ) as attack_mock, patch.object(
            monster,
            "choose_target",
            wraps=monster.choose_target,
        ) as target_mock, patch.object(
            game,
            "get_battle_result",
            side_effect=AssertionError(
                "process_turn内で勝敗判定を呼んでいます"
            ),
        ):
            result = game.process_turn(
                monster, players, monsters
            )

            assert result is None, label
            assert monster.hp == 100, label
            target_mock.assert_called_once_with(players)
            attack_mock.assert_not_called()


def test_process_turn_monster_attack():
    for starting_hp, expected_hp in [(50, 30), (20, 0)]:
        hero = game.Hero(
            "攻撃対象", 100, 10, 10, game.Inventory({})
        )
        hero.hp = starting_hp
        monster = game.Monster("攻撃する敵", 100, 10, {})

        def fixed_attack(target):
            target.take_damage(20)

        def verify_down_check():
            assert hero.hp == expected_hp, (
                "ダメージ処理より先に死亡確認をしています"
            )

        with patch.object(
            game.time,
            "sleep",
        ), patch.object(
            monster,
            "act",
            side_effect=fixed_attack,
        ) as attack_mock, patch.object(
            hero,
            "check_down",
            side_effect=verify_down_check,
        ) as down_mock:
            result = game.process_turn(
                monster, [hero], [monster]
            )

            assert result is None
            assert hero.hp == expected_hp
            attack_mock.assert_called_once_with(hero)
            down_mock.assert_called_once_with()


def test_battle_ends_after_poison():
    cases = [
        ("味方が毒で全滅", "players", "monsters"),
        ("敵が毒で全滅", "monsters", "players"),
    ]

    for label, poisoned_side, expected_result in cases:
        hero = game.Hero(
            "勇者",
            100,
            10,
            10,
            game.Inventory({}),
            speed=10,
        )
        monster = game.Monster(
            "敵", 100, 10, {}, speed=10
        )

        character = (
            hero if poisoned_side == "players" else monster
        )
        character.speed = 20
        character.hp = 15
        character.status["poison_turn"] = 3

        with patch.object(
            game.time,
            "sleep",
        ), patch.object(
            hero,
            "choose_action",
            side_effect=AssertionError(
                f"{label}：終了するはずなのに味方が行動しました"
            ),
        ) as hero_action, patch.object(
            monster,
            "act",
            side_effect=AssertionError(
                f"{label}：終了するはずなのに敵が行動しました"
            ),
        ) as monster_action:
            result = game.battle([hero], [monster])

            assert result == expected_result, label
            assert character.hp == 0, label
            assert character.status["poison_turn"] == 2, label

            hero_action.assert_not_called()
            monster_action.assert_not_called()


# =======================================================================
# 対象選択関数の注入


def test_select_lowest_hp_ratio_target():
    # 名前、各対象の「現在HP・最大HP」、期待する位置
    cases = [
        ("HPではなく割合", [(80, 200), (70, 150)], 0),
        ("2人目が低い", [(150, 200), (30, 150)], 1),
        ("同率なら先頭", [(100, 200), (75, 150)], 0),
        ("同率で逆順", [(75, 150), (100, 200)], 0),
        ("候補1人", [(20, 100)], 0),
        ("全員満タン", [(200, 200), (150, 150)], 0),
    ]

    for label, specs, expected_index in cases:
        candidates = []

        for index, (hp, maxhp) in enumerate(specs):
            character = game.Player(f"対象{index}", maxhp, 10)
            character.hp = hp
            candidates.append(character)

        before = candidates.copy()
        states_before = [
            deepcopy(character.__dict__)
            for character in candidates
        ]

        target = game.select_lowest_hp_ratio_target(candidates)

        assert target is before[expected_index], label
        assert_same_objects(candidates, before)

        for character, state in zip(before, states_before):
            assert character.__dict__ == state, label


def test_select_random_target():
    first = game.Player("対象A", 100, 10)
    second = game.Player("対象B", 100, 10)
    candidates = [first, second]

    before = candidates.copy()
    states_before = [
        deepcopy(character.__dict__)
        for character in candidates
    ]

    with patch.object(
        game.random,
        "choice",
        return_value=second,
    ) as choice_mock:
        target = game.select_random_target(candidates)

        choice_mock.assert_called_once_with(before)
        assert target is second

    assert_same_objects(candidates, before)

    for character, state in zip(before, states_before):
        assert character.__dict__ == state


def test_monster_target_selector():
    # 名前、候補のHP、選択関数が返す元一覧上の位置
    cases = [
        ("戦闘不能除外", [0, 80, 0, 50], 3),
        ("生存者1人", [0, 80, 0], 1),
        ("全員生存", [80, 50], 0),
        ("全員戦闘不能", [0, 0], None),
        ("候補なし", [], None),
    ]

    for label, hps, selected_index in cases:
        targets = []

        for index, hp in enumerate(hps):
            character = game.Player(f"対象{index}", 100, 10)
            character.hp = hp
            targets.append(character)

        before = targets.copy()
        states_before = [
            deepcopy(character.__dict__)
            for character in targets
        ]

        expected_candidates = [
            character
            for character in before
            if character.hp > 0
        ]

        expected_target = (
            before[selected_index]
            if selected_index is not None
            else None
        )

        selector = Mock(return_value=expected_target)

        monster = game.Monster(
            "テスト敵",
            100,
            10,
            {},
            target_selector=selector,
        )

        assert monster.target_selector is selector, label

        result = monster.choose_target(targets)

        assert result is expected_target, label

        if expected_candidates:
            selector.assert_called_once_with(expected_candidates)
        else:
            selector.assert_not_called()

        assert_same_objects(targets, before)

        for character, state in zip(before, states_before):
            assert character.__dict__ == state, label


def test_target_selector_initialization():
    default_monster = game.Monster("既定の敵", 100, 10, {})

    assert (
        default_monster.target_selector
        is game.select_random_target
    )

    none_monster = game.Monster(
        "None指定の敵",
        100,
        10,
        {},
        target_selector=None,
    )

    assert (
        none_monster.target_selector
        is game.select_random_target
    )

    players, monsters = game.create_battle_members()

    assert len(monsters) == 3

    expected_selectors = [
        ("スライムA", game.select_random_target),
        ("スライムB", game.select_random_target),
        ("ゴブリンA", game.select_lowest_hp_ratio_target),
    ]

    for monster, (name, selector) in zip(
        monsters, expected_selectors
    ):
        assert monster.name == name
        assert monster.target_selector is selector

    hero, warrior = players
    hero.hp = 80
    warrior.hp = 70

    goblin = monsters[2]

    assert goblin.choose_target(players) is hero

    hero.hp = 0
    assert goblin.choose_target(players) is warrior

    warrior.hp = 0
    assert goblin.choose_target(players) is None


# =======================================================================
# 魔法のMPコスト定義


def test_magic_mpcosts():
    original_costs = {
        "fire": 10,
        "poison": 6,
        "heal": 8,
        "cure": 5,
        "revive": 15,
    }

    # 魔法ID、コストのキー、ラベルの魔法名
    magic_specs = [
        (2, "fire", "ファイア"),
        (3, "poison", "ポイズン"),
        (4, "heal", "ヒール"),
        (5, "cure", "キュア"),
        (6, "revive", "リザレクト"),
    ]

    # ---------------------------------------------------------------
    # 1. 通常時：定義の値とメニュー辞書が一致する

    assert game.magic_mpcosts == original_costs

    hero = game.Hero(
        "MP定義テスト", 200, 30, 20, game.Inventory({})
    )
    magic_dict = hero.get_magic_action()

    for magic_id, cost_key, name in magic_specs:
        cost = game.magic_mpcosts[cost_key]

        assert magic_dict[magic_id]["mpcost"] == cost, name
        assert magic_dict[magic_id]["label"] == f"{name}(MP{cost})", name

    # ---------------------------------------------------------------
    # 2. ファイアのコストだけを一時的に3へ変更する

    with patch.dict(
        game.magic_mpcosts,
        {"fire": 3},
    ), patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ) as damage_mock, patch.object(game.time, "sleep"):
        assert game.magic_mpcosts["fire"] == 3
        assert game.magic_mpcosts["poison"] == 6

        # メニュー辞書は呼び出した時点の値で作られる
        magic_dict = hero.get_magic_action()

        assert magic_dict[2]["mpcost"] == 3
        assert magic_dict[2]["label"] == "ファイア(MP3)"
        assert magic_dict[3]["mpcost"] == 6

        # 2-1. fire_magic()を直接呼ぶと、MPが3だけ減る
        caster = game.Hero(
            "使用者", 200, 30, 20, game.Inventory({})
        )
        target = game.Monster("対象", 50, 10, {})

        success = caster.fire_magic(target)

        assert success is True
        assert caster.mp == 27
        assert target.hp == 37
        damage_mock.assert_called_once_with(20)

        # 2-2. MPが3未満なら失敗し、何も変わらない
        caster = game.Hero(
            "MP不足の使用者", 200, 30, 20, game.Inventory({})
        )
        caster.mp = 2
        target = game.Monster("対象", 50, 10, {})
        damage_mock.reset_mock()

        success = caster.fire_magic(target)

        assert success is False
        assert caster.mp == 2
        assert target.hp == 50
        damage_mock.assert_not_called()

        # 2-3. メニュー経由でも、判定と消費が同じ値になる
        # 1回目の入力：魔法ID 2、2回目の入力：対象 0
        input_mock = Mock(side_effect=[2, 0])

        caster = game.Hero(
            "メニュー使用者",
            200,
            30,
            20,
            game.Inventory({}),
            input_func=input_mock,
        )
        caster.mp = 3
        target = game.Monster("対象", 50, 10, {})
        damage_mock.reset_mock()

        success = caster.choose_magic_action([target], [caster])

        assert success is True
        assert caster.mp == 0
        assert target.hp == 37
        assert input_mock.call_count == 2
        damage_mock.assert_called_once_with(20)

    # ---------------------------------------------------------------
    # 3. withを抜けると元の値に戻る

    assert game.magic_mpcosts == original_costs

    magic_dict = hero.get_magic_action()

    assert magic_dict[2]["mpcost"] == 10
    assert magic_dict[2]["label"] == "ファイア(MP10)"


# =======================================================================
# 攻撃選択関数の注入


def test_monster_attack_chooser():
    # ---------------------------------------------------------------
    # 1. 初期値：省略時もNone指定時もselect_weighted_attackになる

    default_monster = game.Monster("既定の敵", 100, 10, {})

    assert (
        default_monster.attack_chooser
        is game.select_weighted_attack
    )

    none_monster = game.Monster(
        "None指定の敵",
        100,
        10,
        {},
        attack_chooser=None,
    )

    assert (
        none_monster.attack_chooser
        is game.select_weighted_attack
    )

    # ---------------------------------------------------------------
    # 2. 初期メンバーは3体とも既定の選び方を使う

    players, monsters = game.create_battle_members()

    assert len(monsters) == 3

    for monster in monsters:
        assert (
            monster.attack_chooser
            is game.select_weighted_attack
        ), monster.name

    # ---------------------------------------------------------------
    # 3. choose_attack()は渡された関数に選択を任せる
    # 現在HP、期待するHP割合（最大HPは80）
    cases = [
        (80, 1.0),
        (60, 0.75),
        (40, 0.5),
        (20, 0.25),
    ]

    for hp, expected_ratio in cases:
        attack_a = Mock()
        attack_b = Mock()

        attacks = {
            10: {
                "name": "攻撃A",
                "function": attack_a,
                "weight": lambda hp_ratio: 1,
            },
            20: {
                "name": "攻撃B",
                "function": attack_b,
                "weight": lambda hp_ratio: 1,
            },
        }

        chooser = Mock(return_value=20)

        monster = game.Monster(
            "テスト敵",
            80,
            10,
            attacks,
            attack_chooser=chooser,
        )
        monster.hp = hp

        label = f"HP{hp}/80"

        assert monster.attack_chooser is chooser, label

        # 生成しただけでは選び方の関数を呼ばない
        chooser.assert_not_called()

        attack_id = monster.choose_attack()

        assert attack_id == 20, label
        chooser.assert_called_once_with(attacks, expected_ratio)

        # ==での一致だけでなく、同じ辞書オブジェクトが渡されたか
        assert chooser.call_args.args[0] is attacks, label

        # 攻撃を選ぶだけで、攻撃関数は呼ばない
        attack_a.assert_not_called()
        attack_b.assert_not_called()

        # -----------------------------------------------------------
        # 4. act()は選ばれたIDの攻撃関数だけを呼ぶ

        target = game.Player("攻撃対象", 100, 10)
        chooser.reset_mock()

        result = monster.act(target)

        assert result is None, label
        chooser.assert_called_once_with(attacks, expected_ratio)
        attack_b.assert_called_once_with(monster, target)
        attack_a.assert_not_called()

        # 攻撃関数は代役なので、HPは変わらない
        assert monster.hp == hp, label
        assert target.hp == 100, label


def test_select_weighted_attack():
    # 攻撃IDはわざと連番にしない（位置ではなくキーを使うか確認するため）
    attacks = {
        0: {
            "name": "固定の重み",
            "function": game.Player.attack,
            "weight": lambda hp_ratio: 4,
        },
        5: {
            "name": "HPが高いほど重い",
            "function": game.Monster.special_attack,
            "weight": lambda hp_ratio: 10 * hp_ratio,
        },
        9: {
            "name": "HPが低いほど重い",
            "function": game.Monster.poison_attack,
            "weight": lambda hp_ratio: 20 - 10 * hp_ratio,
        },
    }

    # 実行前の状態を控える（内側の辞書は浅いコピーで十分）
    keys_before = list(attacks.keys())
    inner_before = {
        attack_id: data
        for attack_id, data in attacks.items()
    }
    contents_before = {
        attack_id: data.copy()
        for attack_id, data in attacks.items()
    }

    # ---------------------------------------------------------------
    # 1. random.choicesへの渡し方と、戻り値の取り出し方
    # HP割合、期待する重み、choicesの代役が返すID
    cases = [
        (1.0, [4, 10.0, 10.0], 9),
        (0.5, [4, 5.0, 15.0], 5),
        (0.25, [4, 2.5, 17.5], 0),
    ]

    for hp_ratio, expected_weights, returned_id in cases:
        label = f"HP割合{hp_ratio}"

        with patch.object(
            game.random,
            "choices",
            return_value=[returned_id],
        ) as choices_mock:
            result = game.select_weighted_attack(attacks, hp_ratio)

        assert result == returned_id, label
        choices_mock.assert_called_once_with(
            [0, 5, 9],
            weights=expected_weights,
            k=1,
        )

    # ---------------------------------------------------------------
    # 2. 本物のrandom.choicesで、重み0の攻撃は選ばれない

    zero_weight_attacks = {
        1: {
            "name": "選ばれない攻撃",
            "function": game.Player.attack,
            "weight": lambda hp_ratio: 0,
        },
        2: {
            "name": "必ず選ばれる攻撃",
            "function": game.Monster.special_attack,
            "weight": lambda hp_ratio: 5,
        },
    }

    for _ in range(20):
        result = game.select_weighted_attack(zero_weight_attacks, 0.5)
        assert result == 2

    # ---------------------------------------------------------------
    # 3. 攻撃定義の辞書を変更していない

    assert list(attacks.keys()) == keys_before

    for attack_id, data in attacks.items():
        assert data is inner_before[attack_id]
        assert data == contents_before[attack_id]


# =======================================================================
# 入力関数の注入


ACTION_MESSAGE = (
    "行動を決めてください\n"
    "[0:攻撃 1:アイテム 2:魔法 3:防御]："
)
ITEM_MESSAGE = "使用するアイテムを選んでください："
TARGET_MESSAGE = "対象を選択してください："


def get_input_messages(input_mock):
    """代役の入力関数に渡されたメッセージを、呼ばれた順に返す。"""
    return [
        called.args[0]
        for called in input_mock.call_args_list
    ]


def test_hero_input_func():
    # ---------------------------------------------------------------
    # 1. 初期値：省略時もNone指定時もinput_intになる

    default_hero = game.Hero(
        "既定の勇者", 100, 10, 10, game.Inventory({})
    )

    assert default_hero.input_func is game.input_int

    none_hero = game.Hero(
        "None指定の勇者",
        100,
        10,
        10,
        game.Inventory({}),
        input_func=None,
    )

    assert none_hero.input_func is game.input_int

    # ---------------------------------------------------------------
    # 2. 初期メンバーは2人とも本物の入力関数を使う

    players, monsters = game.create_battle_members()

    assert len(players) == 2

    for player in players:
        assert player.input_func is game.input_int, player.name

    # ---------------------------------------------------------------
    # 3. 攻撃：[0, 0] → 攻撃を選び、対象0を攻撃する

    input_mock = Mock(side_effect=[0, 0])
    hero = game.Hero(
        "攻撃する勇者",
        100,
        10,
        20,
        game.Inventory({}),
        input_func=input_mock,
    )
    monster = game.Monster("対象", 50, 10, {})

    assert hero.input_func is input_mock

    # 生成しただけでは入力を求めない
    input_mock.assert_not_called()

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ) as damage_mock, patch.object(game.time, "sleep"):
        success = hero.choose_action([monster], [hero])

    assert success is True
    assert monster.hp == 40
    assert hero.is_defending is False
    damage_mock.assert_called_once_with(20)
    assert input_mock.call_count == 2
    assert get_input_messages(input_mock) == [
        ACTION_MESSAGE,
        TARGET_MESSAGE,
    ]

    # ---------------------------------------------------------------
    # 4. キャンセル：[0, -1, 3] → 対象選択から戻って防御する

    input_mock = Mock(side_effect=[0, -1, 3])
    hero = game.Hero(
        "キャンセルする勇者",
        100,
        10,
        20,
        game.Inventory({}),
        input_func=input_mock,
    )
    monster = game.Monster("対象", 50, 10, {})

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ) as damage_mock, patch.object(game.time, "sleep"):
        success = hero.choose_action([monster], [hero])

    assert success is True
    assert hero.is_defending is True
    assert monster.hp == 50
    damage_mock.assert_not_called()
    assert input_mock.call_count == 3
    assert get_input_messages(input_mock) == [
        ACTION_MESSAGE,
        TARGET_MESSAGE,
        ACTION_MESSAGE,
    ]

    # ---------------------------------------------------------------
    # 5. アイテム：[1, 9, 0] → 存在しないID9のあとに回復薬を使う

    input_mock = Mock(side_effect=[1, 9, 0])
    inventory = game.Inventory(deepcopy(game.items))
    hero = game.Hero(
        "アイテムを使う勇者",
        200,
        10,
        20,
        inventory,
        input_func=input_mock,
    )
    hero.hp = 100
    monster = game.Monster("対象", 50, 10, {})

    success = hero.choose_action([monster], [hero])

    assert success is True
    assert hero.hp == 130
    assert inventory.items[0]["count"] == 2
    assert inventory.items[1]["count"] == 1
    assert input_mock.call_count == 3
    assert get_input_messages(input_mock) == [
        ACTION_MESSAGE,
        ITEM_MESSAGE,
        ITEM_MESSAGE,
    ]

    # ---------------------------------------------------------------
    # 6. 対象選択：範囲外 → 負の数 → 戦闘不能 → 正しい番号

    fallen = game.Player("戦闘不能の対象", 100, 10)
    fallen.hp = 0
    survivor = game.Player("生存している対象", 100, 10)
    targets = [fallen, survivor]

    # -2は「戻る」ではなく範囲外として扱われることも確認する
    input_mock = Mock(side_effect=[5, -2, 0, 1])
    hero = game.Hero(
        "対象を選ぶ勇者",
        100,
        10,
        20,
        game.Inventory({}),
        input_func=input_mock,
    )

    result = hero.choose_target(targets)

    assert result == (True, 1)
    assert input_mock.call_count == 4
    assert get_input_messages(input_mock) == [TARGET_MESSAGE] * 4

    # ---------------------------------------------------------------
    # 7. 対象選択の「戻る」：[-1] → (False, -1)

    input_mock = Mock(side_effect=[-1])
    hero = game.Hero(
        "戻る勇者",
        100,
        10,
        20,
        game.Inventory({}),
        input_func=input_mock,
    )

    result = hero.choose_target(targets)

    assert result == (False, -1)
    assert input_mock.call_count == 1

# =======================================================================
# 状態異常の表示

def test_get_status_text():
    # ---------------------------------------------------------------
    # 1. 戻り値：Player・Hero・Monsterのどれでも同じ結果になる
    # ケース名、麻痺、毒、期待する文字列
    cases = [
        ("状態異常なし", 0, 0, ""),
        ("毒だけ", 0, 3, "(毒3ターン)"),
        ("麻痺だけ", 1, 0, "(麻痺1ターン)"),
        ("麻痺と毒", 1, 3, "(麻痺1ターン)(毒3ターン)"),
        ("残り負数は表示しない", 0, -1, ""),
        ("負数と麻痺", 1, -1, "(麻痺1ターン)"),
    ]

    for label, paralysis, poison, expected in cases:
        characters = [
            game.Player("基本キャラ", 100, 10),
            game.Hero("勇者", 100, 10, 10, game.Inventory({})),
            game.Monster("敵", 100, 10, {}),
        ]

        for character in characters:
            # 定義データと逆の並び順にしておく。
            # 表示順が self.status ではなく定義データで決まることを確認するため。
            status = make_status(
                paralysis_turn=paralysis,
                poison_turn=poison,
            )
            character.status = dict(reversed(list(status.items())))

            status_object = character.status
            status_before = character.status.copy()
            context = f"{type(character).__name__}／{label}"

            result = character.get_status_text()

            assert isinstance(result, str), context
            assert result == expected, context

            # 表示用の文字列を作るだけで、状態は変えない
            assert character.status is status_object, context
            assert character.status == status_before, context

    # ---------------------------------------------------------------
    # 2. ラベルは定義データから読む
    # 内側の辞書を渡し、"label"だけを一時的に変える

    poison_definition = game.status_definitions["poison_turn"]
    definition_before = poison_definition.copy()

    hero = game.Hero("ラベル確認の勇者", 100, 10, 10, game.Inventory({}))
    hero.status["poison_turn"] = 2

    assert hero.get_status_text() == "(毒2ターン)"

    with patch.dict(
        game.status_definitions["poison_turn"],
        {"label": "猛毒"},
    ):
        assert hero.get_status_text() == "(猛毒2ターン)"

        # "label"以外のキーは残っている
        assert poison_definition == {
            **definition_before,
            "label": "猛毒",
        }

        # 内側の辞書は差し替えられていない
        assert game.status_definitions["poison_turn"] is poison_definition

    # withを抜けると元に戻る
    assert hero.get_status_text() == "(毒2ターン)"
    assert poison_definition == definition_before
    assert game.status_definitions["poison_turn"] is poison_definition

    # ---------------------------------------------------------------
    # 3. 表示している3か所がget_status_text()を使う

    hero = game.Hero(
        "表示する勇者",
        100,
        10,
        10,
        game.Inventory({}),
        input_func=Mock(side_effect=[-1]),
    )
    monster = game.Monster("表示する敵", 100, 10, {})

    with patch.object(
        hero,
        "get_status_text",
        return_value="[勇者の目印]",
    ) as hero_text, patch.object(
        monster,
        "get_status_text",
        return_value="[敵の目印]",
    ) as monster_text, patch("builtins.print") as print_mock:
        hero.show_status()
        monster.show_status()
        result = hero.choose_target([monster, hero])

    assert result == (False, -1)

    # 各自：show_statusで1回＋対象一覧で1回
    assert hero_text.call_count == 2
    assert monster_text.call_count == 2

    printed = " ".join(
        str(arg)
        for called in print_mock.call_args_list
        for arg in called.args
    )

    assert printed.count("[勇者の目印]") == 2
    assert printed.count("[敵の目印]") == 2


# =======================================================================
# 状態異常の付与


def get_printed_lines(print_mock):
    """print()の代役に渡された内容を、1回の呼び出しにつき1行で返す。"""
    return [
        " ".join(str(arg) for arg in called.args)
        for called in print_mock.call_args_list
    ]


def test_inflict_status():
    # ---------------------------------------------------------------
    # 1. 付与に成功した場合
    # ケース名、キー、現在ターン、付与ターン、期待ターン、期待メッセージ
    success_cases = [
        ("毒の付与", "poison_turn", 0, 3, 3, "<対象は毒にかかった！>"),
        ("麻痺の付与", "paralysis_turn", 0, 1, 1, "<対象は麻痺にかかった！>"),
        ("毒を延長", "poison_turn", 1, 3, 3, "<対象は毒にかかった！>"),
        ("毒を短縮しない", "poison_turn", 5, 3, 5, "<対象は毒にかかった！>"),
    ]

    for (
        label,
        key,
        current,
        turn,
        expected_turn,
        expected_message,
    ) in success_cases:
        characters = [
            game.Player("対象", 100, 10),
            game.Hero("対象", 100, 10, 10, game.Inventory({})),
            game.Monster("対象", 100, 10, {}),
        ]

        for character in characters:
            context = f"{type(character).__name__}／{label}"
            character.status[key] = current

            other_keys = [
                other for other in character.status if other != key
            ]

            with patch.object(
                game.time,
                "sleep",
            ) as sleep_mock, patch(
                "builtins.print",
            ) as print_mock, patch.object(
                character,
                "apply_status",
                wraps=character.apply_status,
            ) as apply_mock:
                result = character.inflict_status(key, turn)

            assert result is True, context
            assert character.status[key] == expected_turn, context

            for other in other_keys:
                assert character.status[other] == 0, context

            apply_mock.assert_called_once_with(key, turn)
            sleep_mock.assert_called_once_with(1)
            assert get_printed_lines(print_mock) == [expected_message], context

    # ---------------------------------------------------------------
    # 2. 付与を拒否された場合：待ち時間も表示もない
    # ケース名、HP、キー、付与ターン
    rejected_cases = [
        ("戦闘不能", 0, "poison_turn", 3),
        ("未登録のキー", 100, "unknown_status", 3),
        ("0ターン", 100, "poison_turn", 0),
        ("負のターン", 100, "paralysis_turn", -1),
    ]

    for label, hp, key, turn in rejected_cases:
        character = game.Monster("対象", 100, 10, {})
        character.hp = hp
        character.status["poison_turn"] = 2
        character.status["paralysis_turn"] = 1
        status_before = character.status.copy()

        with patch.object(
            game.time,
            "sleep",
        ) as sleep_mock, patch(
            "builtins.print",
        ) as print_mock, patch.object(
            character,
            "apply_status",
            wraps=character.apply_status,
        ) as apply_mock:
            result = character.inflict_status(key, turn)

        assert result is False, label
        assert character.status == status_before, label
        assert character.hp == hp, label
        apply_mock.assert_called_once_with(key, turn)
        sleep_mock.assert_not_called()
        print_mock.assert_not_called()

    # ---------------------------------------------------------------
    # 3. メッセージのラベルは定義データから読む

    character = game.Player("対象", 100, 10)

    with patch.dict(
        game.status_definitions["poison_turn"],
        {"label": "猛毒"},
    ), patch.object(game.time, "sleep"), patch(
        "builtins.print",
    ) as print_mock:
        result = character.inflict_status("poison_turn", 3)

    assert result is True
    assert get_printed_lines(print_mock) == ["<対象は猛毒にかかった！>"]
    assert game.status_definitions["poison_turn"]["label"] == "毒"

    # ---------------------------------------------------------------
    # 4. ポイズン魔法はinflict_status()で毒を付与する

    caster = game.Hero("使用者", 200, 30, 20, game.Inventory({}))
    target = game.Monster("対象", 50, 10, {})

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ), patch.object(game.time, "sleep"), patch.object(
        target,
        "inflict_status",
        wraps=target.inflict_status,
    ) as inflict_mock:
        success = caster.poison_magic(target)

    assert success is True
    assert caster.mp == 24
    assert target.hp == 45
    assert target.status["poison_turn"] == 3
    inflict_mock.assert_called_once_with("poison_turn", 3)

    # ---------------------------------------------------------------
    # 5. 敵の毒液・電撃もinflict_status()で付与する
    # メソッド名、random.random()の戻り値、期待する呼び出し（Noneなら呼ばない）
    attack_cases = [
        ("poison_attack", 0.0, ("poison_turn", 3)),
        ("poison_attack", 0.99, None),
        ("paralysis_attack", 0.0, ("paralysis_turn", 1)),
        ("paralysis_attack", 0.99, None),
    ]

    for method_name, random_value, expected_call in attack_cases:
        context = f"{method_name}／乱数{random_value}"

        monster = game.Monster("攻撃する敵", 100, 10, {})
        target = game.Player("攻撃対象", 100, 10)

        with patch.object(
            game,
            "calculation_damage",
            return_value=10,
        ), patch.object(
            game.random,
            "random",
            return_value=random_value,
        ), patch.object(game.time, "sleep"), patch.object(
            target,
            "inflict_status",
            wraps=target.inflict_status,
        ) as inflict_mock:
            getattr(monster, method_name)(target)

        # 10 × 0.7 = 7ダメージ
        assert target.hp == 93, context

        if expected_call is None:
            inflict_mock.assert_not_called()
            assert target.status == make_status(), context
        else:
            key, turn = expected_call
            inflict_mock.assert_called_once_with(key, turn)
            assert target.status[key] == turn, context


def test_poison_magic_return_value():
    # ---------------------------------------------------------------
    # 1. 毒の付与が拒否されても、発動したならTrueを返す

    caster = game.Hero("使用者", 200, 30, 20, game.Inventory({}))
    target = game.Monster("対象", 50, 10, {})

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ), patch.object(game.time, "sleep"), patch.object(
        target,
        "inflict_status",
        return_value=False,
    ) as inflict_mock:
        success = caster.poison_magic(target)

    assert success is True
    assert caster.mp == 24
    assert target.hp == 45
    inflict_mock.assert_called_once_with("poison_turn", 3)

    # ---------------------------------------------------------------
    # 2. メニュー経由：付与が拒否されても、1回の行動で終わる
    # 1回目の入力：魔法ID 3（ポイズン）、2回目の入力：対象 0

    input_mock = Mock(side_effect=[3, 0])
    caster = game.Hero(
        "メニュー使用者",
        200,
        30,
        20,
        game.Inventory({}),
        input_func=input_mock,
    )
    target = game.Monster("対象", 50, 10, {})

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ), patch.object(game.time, "sleep"), patch.object(
        target,
        "inflict_status",
        return_value=False,
    ) as inflict_mock:
        success = caster.choose_magic_action([target], [caster])

    assert success is True
    assert caster.mp == 24
    assert target.hp == 45
    assert input_mock.call_count == 2
    inflict_mock.assert_called_once_with("poison_turn", 3)

# =======================================================================
# 初期メンバーへの入力関数の注入・戦闘全体


def test_create_battle_members_input_func():
    # ---------------------------------------------------------------
    # 1. 省略時・None指定時は、2人とも本物の入力関数を使う

    for players, _ in (
        game.create_battle_members(),
        game.create_battle_members(input_func=None),
    ):
        assert len(players) == 2

        for player in players:
            assert player.input_func is game.input_int, player.name

    # ---------------------------------------------------------------
    # 2. 代役を渡すと、2人とも同じ代役を使う

    input_mock = Mock()
    players, monsters = game.create_battle_members(input_func=input_mock)

    for player in players:
        assert player.input_func is input_mock, player.name

    # 生成しただけでは入力を求めない
    input_mock.assert_not_called()

    # 入力関数以外の初期状態は変わらない
    assert [player.name for player in players] == ["勇者", "戦士"]
    assert [monster.name for monster in monsters] == [
        "スライムA",
        "スライムB",
        "ゴブリンA",
    ]
    assert players[1].inventory is players[0].inventory

    # ---------------------------------------------------------------
    # 3. 別の呼び出しには影響しない

    other_mock = Mock()
    players1, _ = game.create_battle_members(input_func=input_mock)
    players2, _ = game.create_battle_members(input_func=other_mock)
    players3, _ = game.create_battle_members()

    for player in players1:
        assert player.input_func is input_mock

    for player in players2:
        assert player.input_func is other_mock

    for player in players3:
        assert player.input_func is game.input_int


def test_full_battle_with_scripted_input():
    # 入力の台本（勇者と戦士で同じ代役を共有する）
    # ROUND1：勇者 → 攻撃・ゴブリンA(2)、戦士 → 攻撃・スライムA(0)
    # ROUND2：勇者 → 攻撃・スライムB(1) で決着
    input_mock = Mock(side_effect=[0, 2, 0, 0, 0, 1])

    players, monsters = game.create_battle_members(input_func=input_mock)
    hero, warrior = players
    slime_a, slime_b, goblin = monsters

    # 攻撃は常に通常攻撃（スライムはID 0、ゴブリンはID 10）
    slime_a.attack_chooser = Mock(return_value=0)
    slime_b.attack_chooser = Mock(return_value=0)
    goblin.attack_chooser = Mock(return_value=10)

    # スライムは生存者の先頭を狙う。ゴブリンは本物のHP割合選択のまま
    def select_first(candidates):
        return candidates[0]

    slime_a.target_selector = select_first
    slime_b.target_selector = select_first

    # 味方（攻撃力20・40）は100ダメージ、敵（攻撃力15・10・8）は1ダメージ
    def fixed_damage(attack_power):
        return 100 if attack_power >= 20 else 1

    with patch.object(
        game,
        "calculation_damage",
        side_effect=fixed_damage,
    ) as damage_mock, patch.object(game.time, "sleep"):
        result = game.battle(players, monsters)

    # ---------------------------------------------------------------
    # 結果

    assert result == "players"

    # ゴブリン・スライムA・スライムBが1回ずつ勇者を攻撃した
    assert hero.hp == 197
    assert warrior.hp == 150

    for monster in monsters:
        assert monster.hp == 0, monster.name

    # ---------------------------------------------------------------
    # 進行の順番

    # 台本の入力をちょうど使い切った
    assert input_mock.call_count == 6

    # 行動順：ゴブリンA → 勇者 → スライムA → 戦士 → スライムB → 勇者
    attack_powers = [
        called.args[0]
        for called in damage_mock.call_args_list
    ]
    assert attack_powers == [15, 20, 10, 40, 8, 20]

    # 各モンスターは1回ずつ攻撃を選んだ
    for monster, expected_hp_ratio in [
        (goblin, 1.0),
        (slime_a, 1.0),
        (slime_b, 1.0),
    ]:
        monster.attack_chooser.assert_called_once_with(
            monster.attacks,
            expected_hp_ratio,
        )

# =======================================================================
# 経験値とレベルアップ


def test_hero_gain_exp():
    # ---------------------------------------------------------------
    # 1. 初期値

    hero = game.Hero("新人勇者", 100, 10, 20, game.Inventory({}))

    assert hero.level == 1
    assert hero.exp == 0

    # ---------------------------------------------------------------
    # 2. 経験値とレベルの計算
    # ケース名、開始レベル、開始経験値、獲得量、
    # 期待上昇数、期待レベル、期待経験値
    cases = [
        ("足りない", 1, 0, 29, 0, 1, 29),
        ("ちょうど", 1, 0, 30, 1, 2, 0),
        ("余りを持ち越す", 1, 0, 38, 1, 2, 8),
        ("ためた分と合わせる", 1, 25, 5, 1, 2, 0),
        ("2レベル上昇", 1, 0, 90, 2, 3, 0),
        ("レベル2は60必要", 2, 0, 59, 0, 2, 59),
        ("0は無視", 1, 10, 0, 0, 1, 10),
        ("負数は無視", 1, 10, -5, 0, 1, 10),
    ]

    for (
        label,
        level,
        exp,
        amount,
        expected_gained,
        expected_level,
        expected_exp,
    ) in cases:
        hero = game.Hero("経験値テスト", 100, 10, 20, game.Inventory({}))
        hero.level = level
        hero.exp = exp
        hero.hp = 50

        with patch("builtins.print") as print_mock:
            gained = hero.gain_exp(amount)

        assert gained == expected_gained, label
        assert hero.level == expected_level, label
        assert hero.exp == expected_exp, f"{label}: exp={hero.exp}, exp_exp={expected_exp}"

        # 1レベルごとに最大HP・HP +20、攻撃力 +4
        assert hero.maxhp == 100 + 20 * expected_gained, label
        assert hero.hp == 50 + 20 * expected_gained, label
        assert hero.attack_power == 20 + 4 * expected_gained, label

        # MPは変わらない
        assert hero.maxmp == 10, label
        assert hero.mp == 10, label

        # 上がったレベルごとに1行ずつメッセージが出る
        expected_messages = [
            f"<経験値テストはレベル{new_level}に上がった！>"
            for new_level in range(level + 1, expected_level + 1)
        ]
        level_up_lines = [
            line
            for line in get_printed_lines(print_mock)
            if "に上がった！" in line
        ]
        assert level_up_lines == expected_messages, label

    # ---------------------------------------------------------------
    # 3. 上昇量と必要経験値は定義データから読む

    hero = game.Hero("調整テスト", 100, 10, 20, game.Inventory({}))

    with patch.dict(
        game.level_settings,
        {"exp_per_level": 10, "maxhp": 1, "attack_power": 2},
    ):
        gained = hero.gain_exp(10)

    assert gained == 1
    assert hero.level == 2
    assert hero.exp == 0
    assert hero.maxhp == 101
    assert hero.attack_power == 22
    assert game.level_settings == {
        "exp_per_level": 30,
        "maxhp": 20,
        "attack_power": 4,
    }


def test_distribute_exp():
    # ---------------------------------------------------------------
    # 1. モンスターの経験値の初期値

    assert game.Monster("既定の敵", 100, 10, {}).exp == 0

    players, monsters = game.create_battle_members()

    assert [monster.exp for monster in monsters] == [8, 10, 20]

    for player in players:
        assert (player.level, player.exp) == (1, 0), player.name

    # ---------------------------------------------------------------
    # 2. 倒した敵の経験値を、生存している味方がそれぞれ受け取る
    # ケース名、敵のHP、味方のHP、期待合計、
    # 期待する味方の（レベル、経験値）
    cases = [
        ("全員撃破・全員生存", [0, 0, 0], [200, 150], 38, [(2, 8), (2, 8)]),
        ("戦士は戦闘不能", [0, 0, 0], [200, 0], 38, [(2, 8), (1, 0)]),
        ("ゴブリンだけ撃破", [50, 70, 0], [200, 150], 20, [(1, 20), (1, 20)]),
        ("撃破なし", [50, 70, 80], [200, 150], 0, [(1, 0), (1, 0)]),
    ]

    for label, monster_hps, player_hps, expected_total, expected_states in cases:
        players, monsters = game.create_battle_members()

        for monster, hp in zip(monsters, monster_hps):
            monster.hp = hp

        for player, hp in zip(players, player_hps):
            player.hp = hp

        monster_states_before = [
            (monster.hp, monster.exp)
            for monster in monsters
        ]

        with patch.object(game.time, "sleep"):
            total = game.distribute_exp(players, monsters)

        assert total == expected_total, label

        for player, hp, (level, exp) in zip(
            players, player_hps, expected_states
        ):
            context = f"{label}／{player.name}"

            assert player.level == level, context
            assert player.exp == exp, context

            # 戦闘不能の味方は経験値を受け取らず、HPも0のまま
            if hp <= 0:
                assert player.hp == 0, context

        # モンスターの状態は変えない
        assert [
            (monster.hp, monster.exp)
            for monster in monsters
        ] == monster_states_before, label

# =======================================================================
# 状態異常の枠と定義データ


def test_status_slots_follow_definitions():
    # 確認実験などで定義に追加されるキーと重ならない名前にする
    new_key = "slot_check_turn"

    # 実行前の定義を控える（キーの並びと、各定義の辞書そのもの）
    keys_before = list(game.status_definitions)
    inner_before = dict(game.status_definitions)

    # ---------------------------------------------------------------
    # 1. 状態の枠は定義データと同じキー・同じ順番で、すべて0

    characters = [
        game.Player("基本キャラ", 100, 10),
        game.Hero("勇者", 100, 10, 10, game.Inventory({})),
        game.Monster("敵", 100, 10, {}),
    ]

    for character in characters:
        context = type(character).__name__

        assert list(character.status) == keys_before, context
        assert all(turn == 0 for turn in character.status.values()), context

    # キャラクターごとに別の辞書を持つ
    first = game.Player("A", 100, 10)
    second = game.Player("B", 100, 10)

    assert first.status is not second.status

    first.apply_status("poison_turn", 3)
    assert second.status == make_status()

    # ---------------------------------------------------------------
    # 2. 定義を1つ足すだけで、新しい状態異常が使える

    assert new_key not in game.status_definitions, (
        f"{new_key}がすでに定義されています。テスト用のキー名を変えてください"
    )

    new_definition = {
        "label": "確認用",
        "message": "確認中!",
        "damage": 7,
        "blocks_action": False,
    }

    with patch.dict(
        game.status_definitions,
        {new_key: new_definition},
    ), patch.object(game.time, "sleep"):
        character = game.Monster("新状態の敵", 100, 10, {})

        # 枠が自動で作られる
        assert character.status[new_key] == 0
        assert character.status == make_status()

        # 付与・表示・毎ターンの処理が、ゲーム側を変えずに動く
        assert character.apply_status(new_key, 2) is True
        assert character.get_status_text() == "(確認用2ターン)"

        can_act = character.check_debuff()

        assert can_act is True
        assert character.hp == 93
        assert character.status == make_status(**{new_key: 1})

        # 解除もできる
        assert character.clear_status(new_key) is True
        assert character.status == make_status()

    # ---------------------------------------------------------------
    # 3. withを抜けると、定義は実行前と同じに戻る

    assert new_key not in game.status_definitions
    assert list(game.status_definitions) == keys_before

    for key, definition in game.status_definitions.items():
        assert definition is inner_before[key], key

    # 新しく作るキャラクターには、追加した枠がない
    character = game.Player("元に戻った後", 100, 10)

    assert new_key not in character.status
    assert list(character.status) == keys_before
    assert character.status == make_status()


# =======================================================================
# 火傷


def test_burn_status():
    # ---------------------------------------------------------------
    # 1. 定義データ

    burn = game.status_definitions["burn_turn"]

    assert burn["label"] == "火傷"
    assert burn["damage"] == 8
    assert burn["blocks_action"] is False
    assert burn["attack_multiplier"] == 0.5

    assert list(game.status_definitions) == [
        "paralysis_turn",
        "poison_turn",
        "burn_turn",
    ]

    # 倍率は任意の項目なので、麻痺と毒には書かない
    for key in ("paralysis_turn", "poison_turn"):
        assert "attack_multiplier" not in game.status_definitions[key], key

    # 新しく作るキャラクターには火傷の枠がある
    assert game.Player("新規", 100, 10).status["burn_turn"] == 0

    # ---------------------------------------------------------------
    # 2. get_attack_power()：火傷の間だけ攻撃力が半分になる
    # ケース名、状態異常、期待する攻撃力（元の攻撃力は20）
    cases = [
        ("状態異常なし", {}, 20),
        ("火傷", {"burn_turn": 2}, 10),
        ("火傷が残り0", {"burn_turn": 0}, 20),
        ("毒だけ", {"poison_turn": 3}, 20),
        (
            "火傷と毒と麻痺",
            {"burn_turn": 1, "poison_turn": 3, "paralysis_turn": 1},
            10,
        ),
    ]

    for label, turns, expected in cases:
        characters = [
            game.Player("基本キャラ", 100, 20),
            game.Hero("勇者", 100, 10, 20, game.Inventory({})),
            game.Monster("敵", 100, 20, {}),
        ]

        for character in characters:
            context = f"{type(character).__name__}／{label}"
            character.status = make_status(**turns)
            status_before = character.status.copy()

            result = character.get_attack_power()

            assert result == expected, context

            # 元の能力値と状態は変えない
            assert character.attack_power == 20, context
            assert character.status == status_before, context

    # ---------------------------------------------------------------
    # 3. 倍率は定義データから読む

    character = game.Player("調整テスト", 100, 20)
    character.status["burn_turn"] = 1

    with patch.dict(
        game.status_definitions["burn_turn"],
        {"attack_multiplier": 0.25},
    ):
        assert character.get_attack_power() == 5

    assert character.get_attack_power() == 10

    # 倍率の項目がない定義は、攻撃力を変えない
    with patch.dict(
        game.status_definitions,
        {
            "slot_check_turn": {
                "label": "確認用",
                "message": "確認中!",
                "damage": 1,
                "blocks_action": False,
            },
        },
    ):
        character = game.Player("倍率なし", 100, 20)
        character.status["slot_check_turn"] = 2

        assert character.get_attack_power() == 20

    # ---------------------------------------------------------------
    # 4. 敵の攻撃は、下がった攻撃力でダメージを計算する

    for method_name in (
        "attack",
        "special_attack",
        "poison_attack",
        "paralysis_attack",
    ):
        monster = game.Monster("火傷の敵", 100, 20, {})
        monster.status["burn_turn"] = 2
        target = game.Player("攻撃対象", 100, 10)

        with patch.object(
            game,
            "calculation_damage",
            return_value=10,
        ) as damage_mock, patch.object(
            game.random,
            "random",
            return_value=0.99,
        ), patch.object(game.time, "sleep"):
            getattr(monster, method_name)(target)

        assert damage_mock.call_args_list == [((10,),)], method_name
        assert monster.attack_power == 20, method_name

    # 勇者の魔法も同じ
    for method_name in ("fire_magic", "poison_magic"):
        caster = game.Hero("火傷の勇者", 200, 30, 20, game.Inventory({}))
        caster.status["burn_turn"] = 2
        target = game.Monster("対象", 50, 10, {})

        with patch.object(
            game,
            "calculation_damage",
            return_value=10,
        ) as damage_mock, patch.object(
            game.random,
            "random",
            return_value=0.99,
        ), patch.object(game.time, "sleep"):
            success = getattr(caster, method_name)(target)

        assert success is True, method_name
        assert damage_mock.call_args_list == [((10,),)], method_name

    # ---------------------------------------------------------------
    # 5. ファイアは30%で火傷を付与する
    # ケース名、対象HP、乱数、期待する火傷ターン、inflict_statusを呼ぶか
    fire_cases = [
        ("付与する", 50, 0.0, 3, True),
        ("境界の0.3は付与する", 50, 0.3, 3, True),
        ("確率で外れる", 50, 0.99, 0, False),
        ("倒したら付与しない", 5, 0.0, 0, False),
    ]

    for label, target_hp, random_value, expected_burn, should_inflict in fire_cases:
        caster = game.Hero("使用者", 200, 30, 20, game.Inventory({}))
        target = game.Monster("対象", 50, 10, {})
        target.hp = target_hp

        with patch.object(
            game,
            "calculation_damage",
            return_value=10,
        ), patch.object(
            game.random,
            "random",
            return_value=random_value,
        ), patch.object(game.time, "sleep"), patch.object(
            target,
            "inflict_status",
            wraps=target.inflict_status,
        ) as inflict_mock:
            success = caster.fire_magic(target)

        assert success is True, label
        assert caster.mp == 20, label
        assert target.hp == max(target_hp - 13, 0), label
        assert target.status["burn_turn"] == expected_burn, label

        if should_inflict:
            inflict_mock.assert_called_once_with("burn_turn", 3)
        else:
            inflict_mock.assert_not_called()

    # ---------------------------------------------------------------
    # 6. 毎ターンの処理：8ダメージ、行動はできる

    with patch.object(game.time, "sleep"):
        monster = game.Monster("火傷の敵", 100, 10, {})
        monster.status["burn_turn"] = 3

        can_act = monster.check_debuff()

        assert can_act is True
        assert monster.hp == 92
        assert monster.status == make_status(burn_turn=2)

        # 火傷のダメージで倒れる
        monster = game.Monster("瀕死の敵", 100, 10, {})
        monster.hp = 8
        monster.status["burn_turn"] = 3

        can_act = monster.check_debuff()

        assert can_act is False
        assert monster.hp == 0

    # ---------------------------------------------------------------
    # 7. キュアでは火傷を治せない

    caster = game.Hero("使用者", 200, 30, 20, game.Inventory({}))
    target = game.Hero("火傷の味方", 200, 10, 20, game.Inventory({}))
    target.status["burn_turn"] = 2

    success = caster.cure_magic(target)

    assert success is False
    assert caster.mp == 30
    assert target.status == make_status(burn_turn=2)

# =======================================================================
# 敵の技の共通化


def test_monster_use_skill():
    # ---------------------------------------------------------------
    # 1. 状態異常のない技：表示・ダメージだけで、乱数は使わない

    monster = game.Monster("敵", 100, 20, {})
    target = game.Player("対象", 100, 10)

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ) as damage_mock, patch.object(
        game.random,
        "random",
        return_value=0.0,
    ) as random_mock, patch.object(
        target,
        "inflict_status",
        wraps=target.inflict_status,
    ) as inflict_mock, patch("builtins.print") as print_mock:
        result = monster.use_skill(target, "体当たり", 1.1)

    assert result is None
    damage_mock.assert_called_once_with(20)

    # 10 × 1.1 = 11ダメージ
    assert target.hp == 89
    assert get_printed_lines(print_mock)[0] == "<敵の体当たり！>"
    random_mock.assert_not_called()
    inflict_mock.assert_not_called()
    assert target.status == make_status()

    # ---------------------------------------------------------------
    # 2. 状態異常のある技：生存していて、乱数が確率以下なら付与する
    # ケース名、対象HP、乱数、期待する毒ターン、乱数を使うか
    cases = [
        ("付与する", 100, 0.0, 3, True),
        ("境界の確率は付与する", 100, 0.75, 3, True),
        ("確率で外れる", 100, 0.76, 0, True),
        ("倒したら判定しない", 5, 0.0, 0, False),
    ]

    for label, target_hp, random_value, expected_poison, uses_random in cases:
        monster = game.Monster("敵", 100, 20, {})
        target = game.Player("対象", 100, 10)
        target.hp = target_hp

        with patch.object(
            game,
            "calculation_damage",
            return_value=10,
        ), patch.object(
            game.random,
            "random",
            return_value=random_value,
        ) as random_mock, patch.object(
            target,
            "inflict_status",
            wraps=target.inflict_status,
        ) as inflict_mock, patch.object(game.time, "sleep"):
            monster.use_skill(target, "毒液", 0.7, "poison_turn", 3, 0.75)

        # 10 × 0.7 = 7ダメージ
        assert target.hp == max(target_hp - 7, 0), label
        assert target.status["poison_turn"] == expected_poison, label
        assert random_mock.call_count == (1 if uses_random else 0), label

        if expected_poison > 0:
            inflict_mock.assert_called_once_with("poison_turn", 3)
        else:
            inflict_mock.assert_not_called()

    # ---------------------------------------------------------------
    # 3. 下がった攻撃力でダメージを計算する

    monster = game.Monster("火傷の敵", 100, 20, {})
    monster.status["burn_turn"] = 2
    target = game.Player("対象", 100, 10)

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ) as damage_mock:
        monster.use_skill(target, "体当たり", 1.1)

    damage_mock.assert_called_once_with(10)
    assert monster.attack_power == 20

    # ---------------------------------------------------------------
    # 4. 3つの技は、決まった引数でuse_skill()を呼ぶだけ
    # メソッド名、use_skillに渡す（targetより後ろの）引数
    delegation_cases = [
        ("special_attack", ("体当たり", 1.1)),
        ("poison_attack", ("毒液", 0.7, "poison_turn", 3, 0.75)),
        ("paralysis_attack", ("電撃", 0.7, "paralysis_turn", 1, 0.25)),
    ]

    for method_name, expected_args in delegation_cases:
        monster = game.Monster("敵", 100, 20, {})
        target = game.Player("対象", 100, 10)

        with patch.object(monster, "use_skill") as skill_mock:
            result = getattr(monster, method_name)(target)

        assert result is None, method_name
        skill_mock.assert_called_once_with(target, *expected_args)

        # 代役なので、実際の攻撃は起きない
        assert target.hp == 100, method_name

    # ---------------------------------------------------------------
    # 5. 技名の表示がそろっている（電撃にも< >が付く）

    for method_name, skill_name in [
        ("special_attack", "体当たり"),
        ("poison_attack", "毒液"),
        ("paralysis_attack", "電撃"),
    ]:
        monster = game.Monster("敵", 100, 20, {})
        target = game.Player("対象", 100, 10)

        with patch.object(
            game,
            "calculation_damage",
            return_value=10,
        ), patch.object(
            game.random,
            "random",
            return_value=0.99,
        ), patch("builtins.print") as print_mock:
            getattr(monster, method_name)(target)

        assert get_printed_lines(print_mock)[0] == f"<敵の{skill_name}！>", method_name

# =======================================================================
# ボス戦


def test_boss_dragon():
    # ---------------------------------------------------------------
    # 1. 初期生成

    bosses = game.create_boss_monsters()

    assert isinstance(bosses, list)
    assert len(bosses) == 1

    dragon = bosses[0]

    assert isinstance(dragon, game.Monster)
    assert dragon.name == "ドラゴン"
    assert dragon.hp == 250
    assert dragon.maxhp == 250
    assert dragon.attack_power == 22
    assert dragon.speed == 12
    assert dragon.exp == 60
    assert dragon.attacks is game.dragon_attacks
    assert dragon.target_selector is game.select_lowest_hp_ratio_target
    assert dragon.attack_chooser is game.select_weighted_attack
    assert dragon.status == make_status()

    # 呼び出すたびに別のボスを作る
    other = game.create_boss_monsters()[0]

    assert other is not dragon
    assert other.status is not dragon.status

    # ---------------------------------------------------------------
    # 2. 攻撃定義の並びと名前

    assert list(game.dragon_attacks) == [10, 20, 30]
    assert game.dragon_attacks[10]["name"] == "攻撃"
    assert game.dragon_attacks[20]["name"] == "体当たり"
    assert game.dragon_attacks[30]["name"] == "炎のブレス"
    assert game.dragon_attacks[10]["function"] is game.Player.attack
    assert game.dragon_attacks[20]["function"] is game.Monster.special_attack

    # ---------------------------------------------------------------
    # 3. HPが半分を切ると、炎のブレスの重みが0から8になる
    # ケース名、ドラゴンのHP、期待する重み（ID10, 20, 30の順）
    weight_cases = [
        ("HP満タン", 250, [5, 5, 0]),
        ("ちょうど半分", 125, [5, 5, 0]),
        ("半分を切った", 124, [5, 5, 8]),
        ("瀕死", 1, [5, 5, 8]),
    ]

    for label, hp, expected_weights in weight_cases:
        dragon = game.create_boss_monsters()[0]
        dragon.hp = hp

        with patch.object(
            game.random,
            "choices",
            wraps=game.random.choices,
        ) as choices_mock:
            attack_id = dragon.choose_attack()

        assert attack_id in game.dragon_attacks, label
        choices_mock.assert_called_once()

        weights = choices_mock.call_args[1]["weights"]

        assert weights == expected_weights, label

    # 重みが0の間は、何度選んでも炎のブレスは出ない
    dragon = game.create_boss_monsters()[0]

    for _ in range(100):
        assert dragon.choose_attack() != 30

    # ---------------------------------------------------------------
    # 4. 炎のブレスは、決まった引数でuse_skill()を呼ぶだけ

    dragon = game.create_boss_monsters()[0]
    target = game.Player("対象", 100, 10)

    with patch.object(dragon, "use_skill") as skill_mock:
        result = game.dragon_attacks[30]["function"](dragon, target)

    assert result is skill_mock.return_value
    skill_mock.assert_called_once_with(
        target, "炎のブレス", 1.4, "burn_turn", 3, 0.5
    )
    assert target.hp == 100

    # ---------------------------------------------------------------
    # 5. act()から炎のブレスを使うと、ダメージと火傷が入る

    dragon = game.Monster(
        "ドラゴン",
        250,
        22,
        game.dragon_attacks,
        attack_chooser=lambda attacks, hp_ratio: 30,
    )
    target = game.Player("対象", 100, 10)

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ) as damage_mock, patch.object(
        game.random,
        "random",
        return_value=0.0,
    ), patch.object(game.time, "sleep"), patch(
        "builtins.print"
    ) as print_mock:
        dragon.act(target)

    damage_mock.assert_called_once_with(22)

    # 10 × 1.4 = 14ダメージ
    assert target.hp == 86
    assert target.status == make_status(burn_turn=3)
    assert get_printed_lines(print_mock)[0] == "<ドラゴンの炎のブレス！>"

# =======================================================================
# 連戦の進行


def test_run_adventure():
    def make_stages(count):
        stages = []

        for number in range(1, count + 1):
            if number == 1:
                intro = None
            else:
                intro = f"<第{number}の敵が現れた！>"

            stages.append({
                "intro": intro,
                "monsters": [game.Monster(f"敵{number}", 10, 1, {})],
            })

        return stages

    # ケース名、ステージ数、battle()が返す結果の順番、期待する戻り値、期待する出来事の順番
    # 出来事の数字は、何番目のステージかを表す
    cases = [
        (
            "2戦とも勝つ",
            2,
            ["players", "players"],
            "clear",
            [
                ("battle", 0),
                ("exp", 0),
                ("rest",),
                ("camp",),
                ("print", "次の冒険へ進みます..."),
                ("print", "<第2の敵が現れた！>"),
                ("battle", 1),
                ("exp", 1),
            ],
        ),
        (
            "1戦目で負ける",
            2,
            ["monsters"],
            "monsters",
            [
                ("battle", 0),
            ],
        ),
        (
            "1戦目で引き分け",
            2,
            ["draw"],
            "draw",
            [
                ("battle", 0),
            ],
        ),
        (
            "2戦目で負ける",
            2,
            ["players", "monsters"],
            "monsters",
            [
                ("battle", 0),
                ("exp", 0),
                ("rest",),
                ("camp",),
                ("print", "次の冒険へ進みます..."),
                ("print", "<第2の敵が現れた！>"),
                ("battle", 1),
            ],
        ),
        (
            "3戦とも勝つ",
            3,
            ["players", "players", "players"],
            "clear",
            [
                ("battle", 0),
                ("exp", 0),
                ("rest",),
                ("camp",),
                ("print", "次の冒険へ進みます..."),
                ("print", "<第2の敵が現れた！>"),
                ("battle", 1),
                ("exp", 1),
                ("rest",),
                ("camp",),
                ("print", "次の冒険へ進みます..."),
                ("print", "<第3の敵が現れた！>"),
                ("battle", 2),
                ("exp", 2),
            ],
        ),
        (
            "1ステージだけ",
            1,
            ["players"],
            "clear",
            [
                ("battle", 0),
                ("exp", 0),
            ],
        ),
        (
            "ステージなし",
            0,
            [],
            "clear",
            [],
        ),
    ]

    for label, stage_count, battle_results, expected_result, expected_events in cases:
        players, _ = game.create_battle_members()
        stages = make_stages(stage_count)
        remaining_results = list(battle_results)
        events = []

        def find_stage_index(monsters):
            for index, stage in enumerate(stages):
                if stage["monsters"] is monsters:
                    return index

            raise AssertionError(f"{label}：ステージにない敵の一覧が渡されました")

        def fake_battle(received_players, monsters):
            assert received_players is players, label
            assert remaining_results, f"{label}：battle()が想定より多く呼ばれました"

            events.append(("battle", find_stage_index(monsters)))
            return remaining_results.pop(0)

        def fake_distribute_exp(received_players, monsters):
            assert received_players is players, label

            events.append(("exp", find_stage_index(monsters)))
            return 0

        def fake_rest_party(received_players):
            assert received_players is players, label

            events.append(("rest",))

        def fake_camp_party(received_players):
            assert received_players is players, label

            events.append(("camp",))

        def fake_print(*args, **kwargs):
            text = " ".join(str(arg) for arg in args)

            # 空行のためのprint()は数えない
            if text:
                events.append(("print", text))

        with patch.object(
            game,
            "battle",
            side_effect=fake_battle,
        ), patch.object(
            game,
            "distribute_exp",
            side_effect=fake_distribute_exp,
        ), patch.object(
            game,
            "rest_party",
            side_effect=fake_rest_party,
        ), patch.object(
            game,
            "camp_party",
            side_effect=fake_camp_party,
        ), patch(
            "builtins.print",
            side_effect=fake_print,
        ):
            result = game.run_adventure(players, stages)

        assert result == expected_result, label
        assert events == expected_events, (
            f"{label}\n"
            f"実際：{events}\n"
            f"期待：{expected_events}"
        )

        # 用意した戦闘結果は、すべて使い切っている
        assert remaining_results == [], label

# =======================================================================
# 戦闘の間の休息


def test_hero_rest():
    # ---------------------------------------------------------------
    # 1. 定義データ

    assert game.rest_settings == {"hp_ratio": 0.3, "mp_ratio": 0.5}

    # ---------------------------------------------------------------
    # 2. heal_mp()：実際に回復した量を返し、最大MPを超えない
    # ケース名、現在のMP、回復量、期待する戻り値、期待するMP（最大MPは30）
    mp_cases = [
        ("通常", 10, 5, 5, 15),
        ("上限で止まる", 28, 5, 2, 30),
        ("満タン", 30, 5, 0, 30),
        ("回復量0", 10, 0, 0, 10),
    ]

    for label, mp, amount, expected_return, expected_mp in mp_cases:
        hero = game.Hero("勇者", 100, 30, 10, game.Inventory({}))
        hero.mp = mp

        result = hero.heal_mp(amount)

        assert result == expected_return, label
        assert hero.mp == expected_mp, label

    # ---------------------------------------------------------------
    # 3. rest()：防御・状態異常の解除と、HP・MPの一部回復

    hero = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    hero.hp = 100
    hero.mp = 4
    hero.is_defending = True
    hero.status = make_status(
        paralysis_turn=1,
        poison_turn=2,
        burn_turn=3,
    )
    status_object = hero.status

    with patch("builtins.print") as print_mock:
        result = hero.rest()

    assert result is None

    # HP：100 + round(200 × 0.3) = 160
    # MP：4 + round(30 × 0.5) = 19
    assert hero.hp == 160
    assert hero.mp == 19
    assert hero.is_defending is False
    assert hero.status == make_status()

    # 辞書を作り直さず、中身だけを変える
    assert hero.status is status_object

    assert get_printed_lines(print_mock)[0] == (
        "<勇者は休息した！(HP160/200 MP19/30)>"
    )

    # 上限で止まる
    hero = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    hero.hp = 190
    hero.mp = 29

    with patch("builtins.print"):
        hero.rest()

    assert hero.hp == 200
    assert hero.mp == 30

    # 最大MPが0でも動く
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 50

    with patch("builtins.print"):
        warrior.rest()

    # 50 + round(150 × 0.3) = 95
    assert warrior.hp == 95
    assert warrior.mp == 0

    # ---------------------------------------------------------------
    # 4. 戦闘不能なら何もしない（蘇生しない）

    fallen = game.Hero("倒れた戦士", 150, 0, 40, game.Inventory({}))
    fallen.hp = 0
    fallen.is_defending = True
    fallen.status["poison_turn"] = 2
    status_before = fallen.status.copy()

    with patch("builtins.print") as print_mock:
        fallen.rest()

    assert fallen.hp == 0
    assert fallen.is_defending is True
    assert fallen.status == status_before
    print_mock.assert_not_called()

    # ---------------------------------------------------------------
    # 5. 回復の割合は定義データから読む

    hero = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    hero.hp = 50
    hero.mp = 0

    with patch.dict(
        game.rest_settings,
        {"hp_ratio": 0.5, "mp_ratio": 0.1},
    ), patch("builtins.print"):
        hero.rest()

    # 50 + round(200 × 0.5) = 150、0 + round(30 × 0.1) = 3
    assert hero.hp == 150
    assert hero.mp == 3

    # ---------------------------------------------------------------
    # 6. rest_party()：全員にrest()を呼び、生存者だけが回復する

    alive = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    alive.hp = 100
    alive.status["burn_turn"] = 2

    fallen = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    fallen.hp = 0

    with patch.object(
        alive,
        "rest",
        wraps=alive.rest,
    ) as alive_rest_mock, patch.object(
        fallen,
        "rest",
        wraps=fallen.rest,
    ) as fallen_rest_mock, patch.object(
        game.time,
        "sleep",
    ), patch("builtins.print") as print_mock:
        result = game.rest_party([alive, fallen])

    assert result is None
    alive_rest_mock.assert_called_once_with()
    fallen_rest_mock.assert_called_once_with()

    assert alive.hp == 160
    assert alive.status == make_status()
    assert fallen.hp == 0

    assert get_printed_lines(print_mock)[0] == "<一行は休息をとった>"

# =======================================================================
# 蘇生


def test_revive():
    # ---------------------------------------------------------------
    # 1. 定義データ

    assert game.magic_mpcosts["revive"] == 15

    # ---------------------------------------------------------------
    # 2. revive()：戦闘不能から生き返り、防御と状態異常が解除される

    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 0
    warrior.is_defending = True
    warrior.status = make_status(poison_turn=2, burn_turn=1)
    status_object = warrior.status

    with patch("builtins.print") as print_mock:
        result = warrior.revive(75)

    assert result is True
    assert warrior.hp == 75
    assert warrior.is_defending is False
    assert warrior.status == make_status()

    # 辞書を作り直さず、中身だけを変える
    assert warrior.status is status_object

    # 表示は呼び出す側が担当する
    print_mock.assert_not_called()

    # ---------------------------------------------------------------
    # 3. revive()：成功・失敗のケース
    # ケース名、現在のHP、回復量、期待する戻り値、期待するHP（最大HPは150）
    cases = [
        ("通常", 0, 75, True, 75),
        ("最大HPで止まる", 0, 999, True, 150),
        ("生存している", 50, 75, False, 50),
        ("回復量0", 0, 0, False, 0),
        ("回復量が負", 0, -10, False, 0),
    ]

    for label, hp, healpt, expected_result, expected_hp in cases:
        characters = [
            game.Player("基本キャラ", 150, 10),
            game.Hero("戦士", 150, 0, 40, game.Inventory({})),
            game.Monster("敵", 150, 10, {}),
        ]

        for character in characters:
            context = f"{type(character).__name__}／{label}"
            character.hp = hp
            character.is_defending = True
            character.status["poison_turn"] = 2
            status_before = character.status.copy()

            result = character.revive(healpt)

            assert result is expected_result, context
            assert character.hp == expected_hp, context

            if expected_result:
                assert character.is_defending is False, context
                assert character.status == make_status(), context
            else:
                # 失敗したときは何も変えない
                assert character.is_defending is True, context
                assert character.status == status_before, context

    # ---------------------------------------------------------------
    # 4. revive_magic()：成功

    caster = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    target = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    target.hp = 0
    target.status["burn_turn"] = 2

    with patch.object(
        target,
        "revive",
        wraps=target.revive,
    ) as revive_mock, patch("builtins.print") as print_mock:
        success = caster.revive_magic(target)

    assert success is True
    assert caster.mp == 15

    # round(150 × 0.5) = 75
    revive_mock.assert_called_once_with(75)
    assert target.hp == 75
    assert target.status == make_status()

    printed = " ".join(
        str(arg)
        for call in print_mock.call_args_list
        for arg in call[0]
    )

    assert "<勇者のリザレクトが発動！>" in printed
    assert "<戦士は生き返った！(残HP75/150)>" in printed

    # MPがちょうど足りる
    caster = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    caster.mp = 15
    target = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    target.hp = 0

    with patch("builtins.print"):
        success = caster.revive_magic(target)

    assert success is True
    assert caster.mp == 0
    assert target.hp == 75

    # ---------------------------------------------------------------
    # 5. revive_magic()：失敗するとMPを消費せず、蘇生もしない
    # ケース名、使用者のMP、対象のHP
    fail_cases = [
        ("生存している対象", 30, 100),
        ("MP不足", 14, 0),
        ("生存していてMPも不足", 0, 100),
    ]

    for label, caster_mp, target_hp in fail_cases:
        caster = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
        caster.mp = caster_mp
        target = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
        target.hp = target_hp

        with patch.object(
            target,
            "revive",
            wraps=target.revive,
        ) as revive_mock, patch("builtins.print"):
            success = caster.revive_magic(target)

        assert success is False, label
        assert caster.mp == caster_mp, label
        assert target.hp == target_hp, label
        revive_mock.assert_not_called()

    # 生存している対象は、MPの確認より前に弾く
    caster = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    target = game.Hero("戦士", 150, 0, 40, game.Inventory({}))

    with patch.object(
        caster,
        "use_mp",
        wraps=caster.use_mp,
    ) as use_mp_mock, patch("builtins.print") as print_mock:
        caster.revive_magic(target)

    use_mp_mock.assert_not_called()
    print_mock.assert_called_once_with("<対象は戦闘不能ではありません>")

# =======================================================================
# 蘇生魔法のメニュー


def test_revive_menu():
    def joined_output(print_mock):
        return " ".join(
            str(arg)
            for call in print_mock.call_args_list
            for arg in call[0]
        )

    # ---------------------------------------------------------------
    # 1. メニューの定義

    hero = game.Hero("勇者", 200, 30, 20, game.Inventory({}))
    magic_dict = hero.get_magic_action()

    assert list(magic_dict) == [2, 3, 4, 5, 6]

    revive_entry = magic_dict[6]

    assert revive_entry["label"] == "リザレクト(MP15)"
    assert revive_entry["target_side"] == "ally"
    assert revive_entry["mpcost"] == 15
    assert revive_entry["target_state"] == "fallen"

    # メソッドは呼び出すたびに新しく作られるので、isではなく==で比べる
    assert revive_entry["function"] == hero.revive_magic

    # 既存の魔法には書かない（項目がなければ生存者が対象）
    for magic_id in (2, 3, 4, 5):
        assert "target_state" not in magic_dict[magic_id], magic_id

    # ---------------------------------------------------------------
    # 2. choose_target()：対象の状態による判定

    # 2-1. fallenでは、生存者を弾いて戦闘不能の対象を選べる
    alive = game.Hero("生存者", 100, 0, 10, game.Inventory({}))
    fallen = game.Hero("戦闘不能", 100, 0, 10, game.Inventory({}))
    fallen.hp = 0

    input_mock = Mock(side_effect=[0, 1])
    chooser = game.Hero(
        "選ぶ人", 100, 30, 10, game.Inventory({}), input_func=input_mock
    )

    with patch("builtins.print") as print_mock:
        result = chooser.choose_target([alive, fallen], "fallen")

    assert result == (True, 1)
    assert input_mock.call_count == 2
    assert "<戦闘不能ではない対象は選べません>" in joined_output(print_mock)

    # 2-2. 初期値（alive）では、今までどおり戦闘不能の対象を弾く
    input_mock = Mock(side_effect=[1, 0])
    chooser = game.Hero(
        "選ぶ人", 100, 30, 10, game.Inventory({}), input_func=input_mock
    )

    with patch("builtins.print") as print_mock:
        result = chooser.choose_target([alive, fallen])

    assert result == (True, 0)
    assert input_mock.call_count == 2
    assert "<戦闘不能の対象は選べません>" in joined_output(print_mock)

    # 2-3. fallenでも、範囲外の番号と-1は今までどおり
    input_mock = Mock(side_effect=[5, -1])
    chooser = game.Hero(
        "選ぶ人", 100, 30, 10, game.Inventory({}), input_func=input_mock
    )

    with patch("builtins.print") as print_mock:
        result = chooser.choose_target([alive, fallen], "fallen")

    assert result == (False, -1)
    assert input_mock.call_count == 2
    assert "<対象が存在しません>" in joined_output(print_mock)

    # 2-4. 不正な設定は、入力を求める前に止める
    input_mock = Mock()
    chooser = game.Hero(
        "選ぶ人", 100, 30, 10, game.Inventory({}), input_func=input_mock
    )

    try:
        with patch("builtins.print"):
            chooser.choose_target([alive, fallen], "unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("不正なtarget_stateでValueErrorになりませんでした")

    input_mock.assert_not_called()

    # ---------------------------------------------------------------
    # 3. 魔法メニューからリザレクを使う

    # 3-1. 戦闘不能の仲間を選んで生き返らせる
    # 入力：魔法ID 6、対象 1
    input_mock = Mock(side_effect=[6, 1])
    caster = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 0
    warrior.status["poison_turn"] = 2
    monster = game.Monster("敵", 50, 10, {})

    with patch("builtins.print"):
        success = caster.choose_magic_action([monster], [caster, warrior])

    assert success is True
    assert caster.mp == 15
    assert warrior.hp == 75
    assert warrior.status == make_status()
    assert input_mock.call_count == 2

    # 3-2. 先に生存している自分を選ぶと弾かれ、選び直せる
    # 入力：魔法ID 6、対象 0（生存者なので弾かれる）、対象 1
    input_mock = Mock(side_effect=[6, 0, 1])
    caster = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 0

    with patch.object(
        caster,
        "revive_magic",
        wraps=caster.revive_magic,
    ) as revive_mock, patch("builtins.print"):
        success = caster.choose_magic_action([monster], [caster, warrior])

    assert success is True
    assert input_mock.call_count == 3

    # 生存者は対象選択で弾かれるので、魔法は戦士に1回だけ使われる
    revive_mock.assert_called_once_with(warrior)
    assert warrior.hp == 75

    # 3-3. ヒールは今までどおり、戦闘不能の仲間を選べない
    # 入力：魔法ID 4、対象 1（弾かれる）、-1で魔法選択へ戻る、-1でメニューを閉じる
    input_mock = Mock(side_effect=[4, 1, -1, -1])
    caster = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 0

    with patch("builtins.print") as print_mock:
        success = caster.choose_magic_action([monster], [caster, warrior])

    assert success is False
    assert caster.mp == 30
    assert warrior.hp == 0
    assert input_mock.call_count == 4
    assert "<戦闘不能の対象は選べません>" in joined_output(print_mock)

    # 3-4. MPが足りなければ、対象を選ぶ前に弾く
    # 入力：魔法ID 6（MP不足）、-1でメニューを閉じる
    input_mock = Mock(side_effect=[6, -1])
    caster = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    caster.mp = 14
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 0

    with patch("builtins.print") as print_mock:
        success = caster.choose_magic_action([monster], [caster, warrior])

    assert success is False
    assert caster.mp == 14
    assert warrior.hp == 0
    assert input_mock.call_count == 2
    assert "<MPが足りません！>" in joined_output(print_mock)

    # ---------------------------------------------------------------
    # 4. 行動選択から魔法メニューを通って使える
    # 入力：行動 2（魔法）、魔法ID 6、対象 1

    input_mock = Mock(side_effect=[2, 6, 1])
    caster = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}))
    warrior.hp = 0

    with patch("builtins.print"):
        success = caster.choose_action([monster], [caster, warrior])

    assert success is True
    assert warrior.hp == 75
    assert input_mock.call_count == 3

    # ---------------------------------------------------------------
    # 5. 生き返ると、次に作る行動順に入る

    hero = game.Hero("勇者", 200, 30, 20, game.Inventory({}), speed=15)
    warrior = game.Hero("戦士", 150, 0, 40, game.Inventory({}), speed=8)
    warrior.hp = 0
    monster = game.Monster("敵", 50, 10, {}, speed=10)

    order = game.get_turn_order([hero, warrior], [monster])

    assert order == [hero, monster]

    warrior.revive(75)
    order = game.get_turn_order([hero, warrior], [monster])

    assert order == [hero, monster, warrior]

# =======================================================================
# 出発の準備


def test_camp():
    def joined_output(print_mock):
        return " ".join(
            str(arg)
            for call in print_mock.call_args_list
            for arg in call[0]
        )

    def make_potion_inventory():
        return game.Inventory({
            0: {
                "key": "potion",
                "name": "回復薬",
                "heal": 30,
                "count": 1,
            },
        })

    # ---------------------------------------------------------------
    # 1. choose_magic_action()：表示する魔法を絞り込める

    # 1-1. 味方向けだけに絞ると、ファイアは表示されず選べない
    # 入力：魔法ID 2（ファイア）、-1で閉じる
    input_mock = Mock(side_effect=[2, -1])
    hero = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    monster = game.Monster("敵", 50, 10, {})

    with patch("builtins.print") as print_mock:
        success = hero.choose_magic_action(
            [monster],
            [hero],
            allowed_sides=("ally",),
        )

    output = joined_output(print_mock)

    assert success is False
    assert hero.mp == 30
    assert monster.hp == 50
    assert input_mock.call_count == 2
    assert "ファイア(MP10)" not in output
    assert "ポイズン(MP6)" not in output
    assert "ヒール(MP8)" in output
    assert "<魔法が存在しません>" in output

    # 1-2. 初期値では、今までどおり敵向けの魔法も使える
    # 入力：魔法ID 2（ファイア）、対象 0
    input_mock = Mock(side_effect=[2, 0])
    hero = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    monster = game.Monster("敵", 50, 10, {})

    with patch.object(
        game,
        "calculation_damage",
        return_value=10,
    ), patch.object(
        game.random,
        "random",
        return_value=0.99,
    ), patch.object(game.time, "sleep"), patch("builtins.print"):
        success = hero.choose_magic_action([monster], [hero])

    assert success is True
    assert hero.mp == 20

    # 10 × 1.3 = 13ダメージ
    assert monster.hp == 37

    # ---------------------------------------------------------------
    # 2. choose_camp_action()
    # ケース名、入力の順番、期待する戻り値
    # 勇者はHP100/200、MP30/30、回復薬1個から始まる
    cases = [
        ("すぐに出発", [0], False),
        ("不正な入力の後に出発", [9, 0], False),
        ("回復薬を使う", [1, 0], True),
        ("アイテムから戻って出発", [1, -1, 0], False),
        ("ヒールを使う", [2, 4, 0], True),
        ("ファイアは選べず、戻って出発", [2, 2, -1, 0], False),
    ]

    for label, inputs, expected_result in cases:
        input_mock = Mock(side_effect=list(inputs))
        hero = game.Hero(
            "勇者",
            200,
            30,
            20,
            make_potion_inventory(),
            input_func=input_mock,
        )
        hero.hp = 100

        with patch.object(game.time, "sleep"), patch(
            "builtins.print"
        ) as print_mock:
            result = hero.choose_camp_action([hero])

        assert result is expected_result, label

        # 用意した入力をすべて使い切っている
        assert input_mock.call_count == len(inputs), label

        if label == "不正な入力の後に出発":
            assert "選択肢から選んでください" in joined_output(print_mock), label

        if label == "回復薬を使う":
            assert hero.hp == 130, label
            assert hero.inventory.items[0]["count"] == 0, label
        elif label == "ヒールを使う":
            assert hero.hp == 150, label
            assert hero.mp == 22, label
        else:
            # 何も使っていない
            assert hero.hp == 100, label
            assert hero.mp == 30, label
            assert hero.inventory.items[0]["count"] == 1, label

    # 魔法メニューは、敵なし・味方向けだけで呼ばれる
    input_mock = Mock(side_effect=[2, -1, 0])
    hero = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=input_mock
    )
    allies = [hero]

    with patch.object(
        hero,
        "choose_magic_action",
        wraps=hero.choose_magic_action,
    ) as magic_mock, patch("builtins.print"):
        hero.choose_camp_action(allies)

    magic_mock.assert_called_once_with([], allies, allowed_sides=("ally",))

    # ---------------------------------------------------------------
    # 3. camp_party()

    # 3-1. 勇者がリザレクトで戦士を生き返らせ、生き返った戦士も準備できる
    # 勇者の入力：魔法 2、リザレクト 6、対象 1、出発 0
    # 戦士の入力：出発 0
    hero_input = Mock(side_effect=[2, 6, 1, 0])
    warrior_input = Mock(side_effect=[0])

    hero = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=hero_input
    )
    warrior = game.Hero(
        "戦士", 150, 0, 40, game.Inventory({}), input_func=warrior_input
    )
    warrior.hp = 0

    with patch.object(game.time, "sleep"), patch(
        "builtins.print"
    ) as print_mock:
        result = game.camp_party([hero, warrior])

    assert result is None
    assert get_printed_lines(print_mock)[0] == "<出発の準備をする>"

    assert hero.mp == 15, f"actual_mp = {hero.mp}"

    # round(150 × 0.5) = 75
    assert warrior.hp == 75
    assert hero_input.call_count == 4
    assert warrior_input.call_count == 1

    # 3-2. 戦闘不能の仲間には入力を求めない
    fallen_input = Mock()
    hero_input = Mock(side_effect=[0])

    fallen = game.Hero(
        "戦士", 150, 0, 40, game.Inventory({}), input_func=fallen_input
    )
    fallen.hp = 0
    hero = game.Hero(
        "勇者", 200, 30, 20, game.Inventory({}), input_func=hero_input
    )

    with patch.object(game.time, "sleep"), patch("builtins.print"):
        game.camp_party([fallen, hero])

    fallen_input.assert_not_called()
    assert hero_input.call_count == 1
    assert fallen.hp == 0

# =======================================================================
# テスト実行


def run_tests():
    tests = [
        test_monster_choose_target,
        test_apply_status,
        test_apply_status_rejected,
        test_debuff,
        test_defend,
        test_heal_hp,
        test_use_mp,
        test_heal_magic_self,
        test_heal_magic,
        test_clear_status,
        test_cure_magic,
        test_cure_magic_self,
        test_poison_magic,
        test_monster_poison_turn,
        test_get_battle_result,
        test_battle_already_finished,
        test_get_turn_order,
        test_speed_initialization,
        test_create_battle_members_initial_state,
        test_create_battle_members_independence,
        test_process_turn,
        test_process_turn_no_target,
        test_process_turn_monster_attack,
        test_battle_ends_after_poison,
        test_select_lowest_hp_ratio_target,
        test_select_random_target,
        test_monster_target_selector,
        test_target_selector_initialization,
        test_magic_mpcosts,
        test_monster_attack_chooser,
        test_select_weighted_attack,
        test_hero_input_func,
        test_get_status_text,
        test_inflict_status,
        test_poison_magic_return_value,
        test_create_battle_members_input_func,
        test_full_battle_with_scripted_input,
        test_hero_gain_exp,
        test_distribute_exp,
        test_status_slots_follow_definitions,
        test_burn_status,
        test_monster_use_skill,
        test_boss_dragon,
        test_run_adventure,
        test_hero_rest,
        test_revive,
        test_revive_menu,
        test_camp
    ]

    # 全テストで待ち時間を無効化する。
    # 想定外の入力処理に進んだ場合は、待たずに失敗させる。
    with patch.object(game.time, "sleep"), patch(
        "builtins.input",
        side_effect=AssertionError(
            "テスト中に想定外の入力要求が発生しました"
        ),
    ):
        for test in tests:
            print(f"\n--- {test.__name__} ---")
            test()
            print(f"[成功] {test.__name__}")

    print(
        f"\n<< すべてのテストに成功しました："
        f"{len(tests)}関数 >>"
    )


if __name__ == "__main__":
    run_tests()
