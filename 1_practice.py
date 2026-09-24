import random
import time
import sys

#=======================================================================

class Player:

    def __init__(self,name,maxhp,attack_power):
        self.name = name
        self.hp = maxhp
        self.maxhp = maxhp
        self.attack_power = attack_power
        self.is_defending = False
        self.status = {
            "poison_turn": 0,
            "paralysis_turn": 0
        }

    def attack(self, target):
        print(f"{self.name}の攻撃！")

        damage = calculation_damage(self.attack_power)
        target.take_damage(damage)

    def defend(self):
        self.is_defending = True
        print(f"{self.name}は身構えた！")

    def start_turn(self):
        self.is_defending = False

    def take_damage(self, damage):

        if self.is_defending is True:
            damage = (damage+1) // 2

        self.hp = max(self.hp - damage, 0)

        print(f"{self.name}に{damage}のダメージ！(残HP{self.hp}/{self.maxhp})")

    def apply_status(self, debuff_key, turn) -> bool:
        if debuff_key not in self.status:
            return False
        if self.hp <= 0:
            return False
        if turn <= 0:
            return False

        self.status[debuff_key] = max(turn, self.status[debuff_key])
        return True

    def check_debuff(self) -> bool: # Falseでターンが飛ばされる
        can_act = True

        if self.hp <= 0:
            can_act = False
            return can_act

        for key, value in status_definitions.items():
            if self.status[key] > 0:
                print()
                if "-test" not in sys.argv:
                    time.sleep(1)

                if value["blocks_action"]:
                    can_act = False

                print(f"{self.name}は{value['message']}(残り{self.status[key]-1}ターン)")

                self.take_damage(value['damage'])

                self.status[key] -= 1

                if self.hp <= 0:
                    can_act = False
                    return can_act

                print()

        return can_act

    def heal_hp(self, healpt) -> int:

        hp_before = self.hp

        self.hp = min(self.hp + healpt, self.maxhp)

        actual_heal_pt = self.hp - hp_before

        return actual_heal_pt

    def check_down(self):
        if self.hp <= 0:
            print(f"{self.name}は倒れた！")


class Hero(Player):

    def __init__(self, name, maxhp, maxmp, attack_power, inventory):
        super().__init__(name, maxhp, attack_power)
        self.mp = maxmp
        self.maxmp = maxmp
        self.inventory = inventory

    def show_status(self):
        print(f"{self.name} HP: {self.hp}/{self.maxhp} MP: {self.mp}/{self.maxmp}")

    def use_mp(self, mpcost) -> bool:
        if mpcost < 0:
            return False

        if self.mp < mpcost:
            return False

        self.mp -= mpcost
        return True

    def use_item(self, item_id) -> bool:

        heal_pt = self.inventory.use(item_id)

        if heal_pt is  None:
            return False

        actual_heal_pt = self.heal_hp(heal_pt)

        print(f"{self.name}は{actual_heal_pt}の回復！(残HP{self.hp}/{self.maxhp})")

        return True

    def choose_item(self) -> bool:
        while True:

            self.inventory.show_items()
            print("└[-1: 戻る]")

            item_id = input_int("使用するアイテムを選んでください：")

            if item_id == -1:
                return False

            if self.use_item(item_id):
                return True

    def choose_action(self, targets, allies) -> bool:
        while True:

            action = input_int("行動を決めてください\n[0:攻撃 1:アイテム 2:ファイア(MP10) 3:防御 4:ヒール(MP8) 5:キュア(MP5)]:")

            print()

            if action == 0:
                success, selected_id = self.choose_target(targets)
                if not success:
                    continue
                self.attack(targets[selected_id])

                targets[selected_id].check_down()

                return True

            elif action == 1:
                success = self.choose_item()
                if not success:
                    continue
                return True

            elif action == 2:
                success, selected_id = self.choose_target(targets)
                if not success:
                    continue

                success = self.fire_magic(targets[selected_id])
                if not success:
                    continue

                targets[selected_id].check_down()

                return True

            elif action == 3:
                self.defend()
                return True

            elif action == 4:
                success, selected_id = self.choose_target(allies)
                if not success:
                    continue

                success = self.heal_magic(allies[selected_id])
                if not success:
                    continue

                return True

            else:
                print("選択肢から選んでください")
                continue

    def choose_target(self, targets):
        while True:

            n = len(targets)

            for i, target in enumerate(targets):
                print(f"└[{i}: {target.name}(HP{target.hp}/{target.maxhp})]")
            print("└[-1: 戻る]")

            selected_id = input_int("対象を選択してください：")

            if selected_id == -1:
                return False, selected_id
            elif selected_id < 0 or selected_id >= n:
                print("対象が存在しません")
                continue
            elif targets[selected_id].hp <= 0:
                print("戦闘不能の対象は選べません")
                continue

            print()

            return True, selected_id

    def fire_magic(self, target) -> bool:
        mpcost = 10

        success = self.use_mp(mpcost)

        if not success:
            print("MPが足りません！")
            return False
        else:
            print(f"{self.name}のファイアが発動！(残MP{self.mp}/{self.maxmp})")
            damage = calculation_damage(self.attack_power)
            damage = round(damage*1.3)
            target.take_damage(damage)

            return True

    def heal_magic(self, target) -> bool:
        mpcost = 8

        if target.hp <= 0:
            print("戦闘不能キャラです")
            return False

        if target.hp == target.maxhp:
            print("すでにHPは最大です")
            return False

        success = self.use_mp(mpcost)

        if not success:
            print("MPが足りません！")
            return False
        else:
            healpt = 50
            # healpt = calculation_heal_hp(healpt)
            actual_healpt = target.heal_hp(healpt)
            print(f"{self.name}のヒールが発動！\n"
                  f"{target.name}は{actual_healpt}の回復！(残HP{self.hp}/{self.maxhp})")

            return True




class Monster(Player):

    def __init__(self, name, maxhp, attack_power, attacks):
        super().__init__(name, maxhp, attack_power)
        self.attacks = attacks

    def show_status(self):
        print(f"{self.name} HP: {self.hp}/{self.maxhp}")

    def special_attack(self, target):
        print(f"{self.name}の体当たり！")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 1.1)
        target.take_damage(damage)

    def poison_attack(self, target):
        print(f"{self.name}の毒液！")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.75:
            success = target.apply_status("poison_turn", 3)
            if success:
                time.sleep(1)
                print(f"{target.name}は毒にかかった！")

    def paralysis_attack(self, target):
        print(f"{self.name}の電撃！")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.25:
            success = target.apply_status("paralysis_turn", 1)
            if success:
                time.sleep(1)
                print(f"{target.name}は麻痺にかかった！")

    def choose_attack(self):

        hp_ratio = self.hp / self.maxhp

        selected_id = random.choices(
            list(self.attacks.keys()), #キー(数字)を返す
            [data["weight"](hp_ratio) for data in self.attacks.values()], # values()で{"name"...}の部分を取得
            k=1
        )[0]

        return selected_id

    def choose_target(self, targets):
        survival_targets = [target for target in targets if target.hp > 0]

        if not survival_targets:
            return None

        return random.choice(survival_targets)

    def act(self, target):

        attack_id = self.choose_attack()

        self.attacks[attack_id]["function"](
            self,
            target
            )

class Inventory:
    def __init__(self, items):
        self.items= items

    def show_items(self):
        for item_id, item_data in self.items.items():
            print(f"└[{item_id}: {item_data['name']}(+HP{item_data['heal']}) × {item_data['count']}]")

    def use(self, item_id):
        if item_id not in self.items.keys():
            print("アイテムが存在しません")
            return None
        elif self.items[item_id]['count'] <= 0:
            print("アイテムが存在しません")
            return None
        else:
            self.items[item_id]['count'] -= 1
            print(f"{self.items[item_id]['name']}を使用した！(残り{self.items[item_id]['count']}個)")
            return self.items[item_id]["heal"]


#=======================================================================

def calculation_damage(attack_power) -> int:

    fluctuation = 25 #ダメージ揺らぎ％

    damage = round(attack_power*(1 + random.randint(-fluctuation,fluctuation)/100))

    p_critical = 20 #クリティカル確率％

    if random.random() < p_critical/100:
        damage = 2*damage
        print("クリティカル！")

    return damage

# def calculation_heal_hp(healpt_hp) -> int:

#     fluctuation = 10 #回復揺らぎ％

#     damage = round(healpt_hp*(1 + random.randint(-fluctuation,fluctuation)/100))

#     return damage

def check_wipedout(group):
    survive = 0
    for player in group:
        if player.hp > 0:
            survive += 1
    if survive == 0:
        return True
    else:
        return False

def input_int(message="数字を入力してください："):
    while True:
        try:
            number = int(input(message))
            break
        except ValueError:
            print("数字を入力してください!")
            continue
    return number

#=======================================================================

def battle(players, monsters):

    print(
        "======================\n"
        "Battle!!\n"
        f"{', '.join(player.name for player in players)} vs {', '.join(monster.name for monster in monsters)}\n"
        "======================"
    )
    print()

    time.sleep(1)

    turn ="players"

    pl_wipedout = False
    mo_wipedout = False

    while True:

        if turn == "players":

            for player in players:

                player.start_turn()

                print(f"【{player.name}】")

                if player.hp == 0:
                    print(f"{player.name}は倒れている！")
                    continue

                player.show_status()

                can_act = player.check_debuff()

                if player.hp <= 0:
                    print(f"{player.name}は倒れてしまった！")

                    pl_wipedout = check_wipedout(players)

                    if pl_wipedout:
                        print(f"{', '.join(player.name for player in players)}は全滅した")
                        break

                    continue

                if not can_act:
                    continue

                success = player.choose_action(monsters, players)

                if not success:
                    continue

                mo_wipedout = check_wipedout(monsters)

                if mo_wipedout:
                    print()
                    time.sleep(1)
                    print(f"{', '.join(monster.name for monster in monsters)}は全滅した")
                    break

                time.sleep(1)
                print()

            if pl_wipedout:
                print()
                time.sleep(1)
                print(f"<< {', '.join(monster.name for monster in monsters)}の勝利 >>")
                break

            if mo_wipedout:
                print()
                time.sleep(1)
                print(f"<< {', '.join(player.name for player in players)}の勝利 >>")
                break


            turn = "monsters"

        if turn == "monsters":

            for monster in monsters:

                if monster.hp <= 0:
                    continue

                monster.show_status()

                target = monster.choose_target(players)

                if target is None:
                    time.sleep(1)
                    pl_wipedout = True
                    print(f"{', '.join(player.name for player in players)}は全滅した")
                    break

                monster.act(target)

                time.sleep(1)

                if target.hp <= 0:
                    print()
                    print(f"{target.name}は倒れてしまった！")

                pl_wipedout = check_wipedout(players)

                if pl_wipedout:
                    print()
                    time.sleep(1)
                    print(f"{', '.join(player.name for player in players)}は全滅した")
                    break

                print()

            if pl_wipedout:
                print()
                time.sleep(1)
                print(f"<< {', '.join(monster.name for monster in monsters)}の勝利 >>")
                break

            turn = "players"

#=======================================================================

items = {
    0: {
        "key": "potion",
        "name": "回復薬",
        "heal": 30,
        "count": 3
    },

    1: {
        "key": "high_potion",
        "name": "上級回復薬",
        "heal": 60,
        "count": 1
    }
}

slime_attacks = {
    0: {
        "name": "攻撃",
        "function": Player.attack,
        "weight": lambda x: 10
    },
    1: {
        "name": "体当たり",
        "function": Monster.special_attack,
        "weight": lambda x: -10*x+15
    },
    2: {
        "name": "毒液",
        "function": Monster.poison_attack,
        "weight": lambda x: -10*x+15
    },
    3: {
        "name": "電撃",
        "function": Monster.paralysis_attack,
        "weight": lambda x: -10*x+15
    }
}

gobrin_attacks = {
    10: {
        "name": "攻撃",
        "function": Player.attack,
        "weight": lambda x:3
    },
    20: {
        "name": "体当たり",
        "function": Monster.special_attack,
        "weight": lambda x: 7
    }
}

status_definitions = {
    "paralysis_turn": {
        "message":"痺れている!",
        "damage": 5,
        "blocks_action": True
    },
    "poison_turn": {
        "message":"毒に侵されている!",
        "damage": 15,
        "blocks_action": False
    }
}

#=======================================================================

def main():

    print(
        "======================\n"
        "RPGゲーム\n"
        "======================\n"
    )

    time.sleep(1)

    inventory = Inventory(items)

    players = [
        Hero("勇者", 200, 30, 20, inventory),
        Hero("戦士", 150, 0, 40, inventory)
    ]

    monsters = [
        Monster("スライムA", 50, 10, slime_attacks),
        Monster("スライムB", 70, 8, slime_attacks),
        Monster("ゴブリンA", 80, 15, gobrin_attacks)
    ]

    battle(players, monsters)

#=======================================================================

def test_monster_choose_target():
    fallen = Player("戦闘不能のキャラクター", 100, 10)
    fallen.hp = 0

    survivor = Player("生存者", 100, 10)

    # 対象選択だけをテストするので、攻撃データは空でよい
    monster = Monster("テスト用モンスター", 50, 10, {})

    # 生存者が1体だけ
    targets = [fallen, survivor]

    target = monster.choose_target(targets)

    assert target is survivor, "生存者が選ばれていません"

    print("生存者1体のテスト成功")

def test_apply_status():
    # 現在の残りターン数、付与ターン数、期待する残りターン数
    cases = [
        (0, 3, 3),
        (1, 3, 3),
        (5, 3, 5),
        (3, 3, 3),
    ]

    for current_turns, added_turns, expected_turns in cases:
        player = Player("テスト用", 100, 10)
        player.status["poison_turn"] = current_turns

        success = player.apply_status("poison_turn", added_turns)

        assert success is True
        assert player.status["poison_turn"] == expected_turns, (
            f"残り{current_turns}ターンに{added_turns}ターン付与："
            f"期待値{expected_turns}、"
            f"実際は{player.status['poison_turn']}"
        )

    print("状態異常のテスト成功")

def test_apply_status_rejected():
    # HP、状態異常のキー、付与ターン数
    cases = [
        (0, "poison_turn", 3),
        (100, "unknown_status", 3),
        (100, "poison_turn", 0),
        (100, "poison_turn", -1),
    ]

    for hp, key, turns in cases:
        player = Player("テスト用", 100, 10)
        player.hp = hp
        player.status["poison_turn"] = 2
        player.status["paralysis_turn"] = 1

        status_before = player.status.copy()

        success = player.apply_status(key, turns)

        assert success is False, (
            f"拒否されるはずです：HP={hp}, key={key}, turns={turns}"
        )
        assert player.status == status_before, (
            f"拒否したのに状態が変わりました：key={key}, turns={turns}"
        )

    print("状態異常拒否のテスト成功")

def test_debuff():

    cases = [
        (100, 0, 0),
        (100, 0, 3),
        (100, 1, 0),
        (100, 1, 3),
        (5, 1, 3),
        (0, 3, 3)
    ]

    case = 0

    for hp, paralysis_turns, poison_turns in cases:
        player = Player("テスト用", 100, 10)
        player.hp = hp
        player.status["paralysis_turn"] = paralysis_turns
        player.status["poison_turn"] = poison_turns

        success = player.check_debuff()

        if case == 0:
            print("case", case)
            assert success is True, "boolが正しくありません"
            assert player.hp == 100, "hpが正しくありません"
        if case == 1:
            print("case", case)
            assert success is True, "boolが正しくありません"
            assert player.hp == 85, "hpが正しくありません"
            assert player.status['poison_turn'] == 2, "毒ターンが正しくありません"
        if case == 2:
            print("case", case)
            assert success is False, "boolが正しくありません"
            assert player.hp == 95, "hpが正しくありません"
            assert player.status['paralysis_turn'] == 0, "麻痺ターンが正しくありません"
        if case == 3:
            print("case", case)
            assert success is False, "boolが正しくありません"
            assert player.hp == 80, "hpが正しくありません"
            assert player.status['poison_turn'] == 2, "毒ターンが正しくありません"
            assert player.status['paralysis_turn'] == 0, "麻痺ターンが正しくありません"
        if case == 4:
            print("case", case)
            assert success is False, "boolが正しくありません"
            assert player.hp == 0, "hpが正しくありません"
            assert player.status['poison_turn'] == 3, "毒ターンが正しくありません"
            assert player.status['paralysis_turn'] == 0, "麻痺ターンが正しくありません"
        if case == 5:
            print("case", case)
            assert success is False, "boolが正しくありません"
            assert player.hp == 0, "hpが正しくありません"
            assert player.status['poison_turn'] == 3, "毒ターンが正しくありません"
            assert player.status['paralysis_turn'] == 3, "麻痺ターンが正しくありません"

        case += 1

    print("状態異常反映のテスト成功")

def test_defend():

    for case in range(6):
        player = Player("テスト用", 100, 10)
        assert player.is_defending is False, "初期状態で防御しています"
        print("case", case)
        if case == 0:
            player.take_damage(10)
            assert player.hp == 90, "hpが正しくありません"
        if case == 1:
            player.defend()
            player.take_damage(10)
            assert player.hp == 95, "hpが正しくありません"
        if case == 2:
            player.defend()
            player.take_damage(5)
            assert player.hp == 97, "hpが正しくありません"
        if case == 3:
            player.defend()
            player.take_damage(10)
            assert player.is_defending is True, "被弾で防御が解除されています"
            player.take_damage(10)
            assert player.is_defending is True, "被弾で防御が解除されています"
            assert player.hp == 90, "hpが正しくありません"
        if case == 4:
            player.defend()
            player.start_turn()
            assert player.is_defending is False, "ターン開始時に防御が解除されていません"
            player.take_damage(10)
            assert player.hp == 90, "hpが正しくありません"
        if case == 5:
            player.hp = 2
            player.defend()
            player.take_damage(10)
            assert player.hp == 0, "hpが正しくありません"

def test_use_mp():
    # 消費MP、期待する戻り値、期待する残MP
    cases = [
        (0, True, 10),
        (8, True, 2),
        (10, True, 0),
        (11, False, 10),
        (-1, False, 10),
    ]

    for cost, expected_success, expected_mp in cases:
        player = Hero("テスト用", 200, 10, 10, Inventory({}))

        success = player.use_mp(cost)

        assert success is expected_success, (
            f"消費MP={cost}：戻り値が正しくありません"
        )
        assert player.mp == expected_mp, (
            f"消費MP={cost}："
            f"期待MP={expected_mp}、実際のMP={player.mp}"
        )

def test_heal_magic_self():
    # 開始HP、開始MP、期待する戻り値、期待HP、期待MP
    cases = [
        (100, 8, True, 150, 0),
        (190, 8, True, 200, 0),
        (200, 8, False, 200, 8),
        (100, 7, False, 100, 7),
    ]

    for hp, mp, expected_success, expected_hp, expected_mp in cases:
        player = Hero("自分への回復テスト", 200, 10, 10, Inventory({}))
        player.hp = hp
        player.mp = mp

        success = player.heal_magic(player)

        assert success is expected_success, "自分へのヒールの成否が違います"
        assert player.hp == expected_hp, (
            f"期待HP={expected_hp}、実際のHP={player.hp}"
        )
        assert player.mp == expected_mp, (
            f"期待MP={expected_mp}、実際のMP={player.mp}"
        )

def test_heal_magic():
    # 使用者のhp、使用者のmp, 対象者のhp、対象者のmp, 期待する戻り値, 期待される使用者のhp、期待される使用者のmp、期待される対象者のhp、期待される対象者のmp
    cases = [
        (120, 8, 100, 0, True, 120, 0, 150, 0),
        (200, 8, 200, 0, False, 200, 8, 200, 0),
        (200, 8, 0, 0, False, 200, 8, 0, 0),
        (200, 7, 100, 0, False, 200, 7, 100, 0)
    ]


    for hp1, mp1, hp2, mp2, exp_success, exp_hp1, exp_mp1, exp_hp2, exp_mp2 in cases:
        players = [
            Hero("テスト用1", 200, 10, 10, Inventory({})),
            Hero("テスト用2", 200, 10, 10, Inventory({}))
        ]

        players[0].hp = hp1
        players[0].mp = mp1
        players[1].hp = hp2
        players[1].mp = mp2

        success = players[0].heal_magic(players[1])

        assert success is exp_success, (
            f"期待する成否={exp_success}、実際の成否={success}"
        )
        assert players[0].hp == exp_hp1, (
            f"使用者HP：期待={exp_hp1}、実際={players[0].hp}"
        )
        assert players[0].mp == exp_mp1, (
            f"使用者MP：期待={exp_mp1}、実際={players[0].mp}"
        )
        assert players[1].hp == exp_hp2, (
            f"対象HP：期待={exp_hp2}、実際={players[1].hp}"
        )
        assert players[1].mp == exp_mp2, (
            f"対象MP：期待={exp_mp2}、実際={players[1].mp}"
        )

def run_tests():
    test_monster_choose_target()
    test_apply_status()
    test_apply_status_rejected()
    test_debuff()
    test_defend()
    test_use_mp()
    test_heal_magic_self()
    test_heal_magic()

    print("すべてのテストに成功しました")

#=======================================================================

if __name__ == "__main__":
    if "-test" in sys.argv:
        run_tests()
    else:
        main()
