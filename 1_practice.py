import random
import time

#=======================================================================

class Player:

    def __init__(self,name,maxhp,attack_power):
        self.name = name
        self.hp = maxhp
        self.maxhp = maxhp
        self.attack_power = attack_power
        self.status = {
            "poison_turn": 0,
            "paralysis_turn": 0
        }

    def attack(self, target):
        print(f"{self.name}の攻撃！")

        damage = calculation_damage(self.attack_power)
        target.take_damage(damage)

    def take_damage(self, damage):

        self.hp = max(self.hp - damage, 0)

        print(f"{self.name}に{damage}のダメージ！(残HP{self.hp}/{self.maxhp})")

    def apply_status(self,debuff_key, turn) -> bool:
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

        if self.status['paralysis_turn'] > 0:
            print()
            time.sleep(1)
            print(f"{self.name}は痺れている！(残り{self.status['paralysis_turn']-1}ターン)")

            paralysis_damage = 5

            self.take_damage(paralysis_damage)
            self.status['paralysis_turn'] -= 1
            print()

            can_act = False

        if self.status['poison_turn'] > 0:
            print()
            time.sleep(1)
            print(f"{self.name}は毒に侵されている！(残り{self.status['poison_turn']-1}ターン)")

            poison_damage = 15

            self.take_damage(poison_damage)
            self.status['poison_turn'] -= 1
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

    def use_mp(self, mpcost):
        self.mp -= mpcost

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

    def choose_action(self, targets) -> bool:
        while True:

            action = input_int("行動を決めてください\n[0:攻撃 1:アイテム 2:ファイア(MP10)]:")

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

                success = self.fire(targets[selected_id])
                if not success:
                    continue

                targets[selected_id].check_down()

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

            selected_id = input_int("敵を選択してください：")

            if selected_id == -1:
                return False, selected_id
            elif selected_id < 0 or selected_id >= n:
                print("敵が存在しません")
                continue
            elif targets[selected_id].hp <= 0:
                print("すでに倒しています")
                continue

            print()

            return True, selected_id

    def fire(self, target):

        mpcost = 10

        if self.mp >= mpcost:

            self.use_mp(mpcost)
            print(f"{self.name}のファイアが発動！(残MP{self.mp})")
            damage = calculation_damage(self.attack_power)
            damage = round(damage*1.3)
            target.take_damage(damage)

            return True

        else:
            print("MPが足りません！")
            return False


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

            for i, player in enumerate(players):

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

                success = player.choose_action(monsters)

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

def run_tests():
    test_monster_choose_target()
    test_apply_status()
    test_apply_status_rejected()

    print("すべてのテストに成功しました")

#=======================================================================

if __name__ == "__main__":
    # run_tests()
    main()
