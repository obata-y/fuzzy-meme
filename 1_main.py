import random
import time
from copy import deepcopy

#=======================================================================

class Player:

    def __init__(self, name, maxhp, attack_power, speed=10):
        self.name = name
        self.hp = maxhp
        self.maxhp = maxhp
        self.attack_power = attack_power
        self.speed = speed
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
        print(f"<{self.name}は身構えた！>")

    def start_turn(self):
        self.is_defending = False

    def take_damage(self, damage):

        if self.is_defending is True:
            damage = (damage+1) // 2

        self.hp = max(self.hp - damage, 0)

        print(f"<{self.name}に{damage}のダメージ！(残HP{self.hp}/{self.maxhp})>")

    def apply_status(self, debuff_key, turn) -> bool:
        if debuff_key not in self.status:
            return False
        if self.hp <= 0:
            return False
        if turn <= 0:
            return False

        self.status[debuff_key] = max(turn, self.status[debuff_key])
        return True

    def clear_status(self, debuff_key) -> bool:
        if self.hp <= 0:
            return False
        if debuff_key not in self.status:
            return False
        if self.status[debuff_key] <= 0:
            return False

        self.status[debuff_key] = 0
        return True

    def check_debuff(self) -> bool: # Falseでターンが飛ばされる
        can_act = True

        if self.hp <= 0:
            can_act = False
            return can_act

        for key, value in status_definitions.items():
            if self.status[key] > 0:
                print()
                time.sleep(1)

                if value["blocks_action"]:
                    can_act = False

                print(f"<{self.name}は{value['message']}(残り{self.status[key]-1}ターン)>")

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
            time.sleep(1)
            print(f"<{self.name}は倒れた！>")

class Hero(Player):

    def __init__(self, name, maxhp, maxmp, attack_power, inventory, speed=10):
        super().__init__(name, maxhp, attack_power, speed)
        self.mp = maxmp
        self.maxmp = maxmp
        self.inventory = inventory

    def show_status(self):

        is_paralysis = ""
        is_poison = ""
        if self.status['paralysis_turn'] > 0:
            is_paralysis = f"(麻痺{self.status['paralysis_turn']}ターン)"
        if self.status['poison_turn'] > 0:
            is_poison = f"(毒{self.status['poison_turn']})"

        print(f"{self.name} HP: {self.hp}/{self.maxhp} MP: {self.mp}/{self.maxmp}", is_paralysis, is_poison)

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

        print(f"<{self.name}は{actual_heal_pt}の回復！(残HP{self.hp}/{self.maxhp})>")

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

            action = input_int("行動を決めてください\n[0:攻撃 1:アイテム 2:魔法 3:防御]")

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
                success = self.choose_magic_action(targets, allies)
                if not success:
                    continue

                return True

            elif action == 3:
                self.defend()
                return True

            else:
                print("選択肢から選んでください")
                continue

    def choose_magic_action(self, targets, allies) -> bool:

        magic_dict = self.get_magic_action()

        while True:

            for id, value in magic_dict.items():
                print(f"└[{id}: {value['label']}]")
            print("└[-1: 戻る]")

            selected_id = input_int("魔法を選択してください：") # 魔法を選ぶ

            if selected_id == -1:
                return False
            elif selected_id not in magic_dict.keys():
                print("<魔法が存在しません>")
                continue

            else:

                selected_magic = magic_dict[selected_id]

                if self.mp < selected_magic['mpcost']:
                    print("<MPが足りません！>")
                    continue

                if selected_magic["target_side"] == "enemy":
                    candidates = targets
                elif selected_magic["target_side"] == "ally":
                    candidates = allies
                else:
                    raise ValueError("<魔法の対象設定が不正です>")

                success, target_id = self.choose_target(candidates)
                if not success:
                    continue

                target = candidates[target_id]

                success = selected_magic["function"](target)
                if not success:
                    continue

                if selected_magic["target_side"] == "enemy":
                    target.check_down()

                return True

    def choose_target(self, targets):
        while True:

            n = len(targets)

            for i, target in enumerate(targets):
                is_paralysis = ""
                is_poison = ""
                if target.status['paralysis_turn'] > 0:
                    is_paralysis = f"(麻痺{target.status['paralysis_turn']}ターン)"
                if target.status['poison_turn'] > 0:
                    is_poison = f"(毒{target.status['poison_turn']})"
                print(
                    f"└[{i}: {target.name}(HP{target.hp}/{target.maxhp})]", is_paralysis, is_poison)
            print("└[-1: 戻る]")

            selected_id = input_int("対象を選択してください：")

            if selected_id == -1:
                return False, selected_id
            elif selected_id < 0 or selected_id >= n:
                print("<対象が存在しません>")
                continue
            elif targets[selected_id].hp <= 0:
                print("<戦闘不能の対象は選べません>")
                continue

            print()

            return True, selected_id

    def get_magic_action(self):
        magic_dict = {
            2: {
                "label": "ファイア(MP10)",
                "target_side": "enemy",
                "function": self.fire_magic,
                "mpcost": 10
            },
            3: {
                "label": "ポイズン(MP6)",
                "target_side": "enemy",
                "function": self.poison_magic,
                "mpcost": 6
            },
            4: {
                "label": "ヒール(MP8)",
                "target_side": "ally",
                "function": self.heal_magic,
                "mpcost": 8
            },
            5: {
                "label": "キュア(MP5)",
                "target_side": "ally",
                "function": self.cure_magic,
                "mpcost": 5
            },
        }

        return magic_dict

    def fire_magic(self, target) -> bool:
        mpcost = 10

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False

        success = self.use_mp(mpcost)

        if not success:
            print("<MPが足りません！>")
            return False

        else:
            print(f"<{self.name}のファイアが発動！(残MP{self.mp}/{self.maxmp})>")
            damage = calculation_damage(self.attack_power)
            damage = round(damage*1.3)
            target.take_damage(damage)

            return True

    def poison_magic(self, target) -> bool:
        mpcost = 6

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False

        if not self.use_mp(mpcost):
            print("<MPが足りません！>")
            return False

        print(
            f"<{self.name}のポイズンが発動！"
            f"(残MP{self.mp}/{self.maxmp})>"
        )

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.5)
        target.take_damage(damage)

        # この下の処理は分岐がうまく作られてる
        if target.hp > 0:
            status_applied = target.apply_status("poison_turn", 3)

            if status_applied:
                time.sleep(1)

                print(f"<{target.name}は毒にかかった！>")

        return True

    def heal_magic(self, target) -> bool:
        mpcost = 8

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False
        if target.hp == target.maxhp:
            print("<すでにHPは最大です>")
            return False

        success = self.use_mp(mpcost)

        if not success:
            print("<MPが足りません！>")
            return False
        else:
            healpt = 50
            # healpt = calculation_heal_hp(healpt)
            actual_healpt = target.heal_hp(healpt)
            print(
                f"{self.name}のヒールが発動！\n"
                f"{target.name}は{actual_healpt}の回復！(残HP{target.hp}/{target.maxhp})"
            )

            return True

    def cure_magic(self, target) -> bool:
        mpcost = 5

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False
        if target.status['poison_turn'] <= 0:
            print("<対象は毒にかかっていません>")
            return False

        success = self.use_mp(mpcost)

        if not success:
            print("<MPが足りません！>")
            return False
        else:
            target.clear_status('poison_turn')
            print(
                f"<{self.name}のキュアが発動！>\n"
                f"<{target.name}の毒が治癒した！>"
            )
            return True


class Monster(Player):

    def __init__(self, name, maxhp, attack_power, attacks, speed=10, target_selector=None):
        super().__init__(name, maxhp, attack_power, speed)
        self.attacks = attacks
        if target_selector is None:
            self.target_selector = select_random_target
        else:
            self.target_selector = target_selector

    def show_status(self):
        print(f"{self.name} HP: {self.hp}/{self.maxhp}")

    def special_attack(self, target):
        print(f"<{self.name}の体当たり！>")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 1.1)
        target.take_damage(damage)

    def poison_attack(self, target):
        print(f"<{self.name}の毒液！>")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.75:
            success = target.apply_status("poison_turn", 3)
            if success:
                time.sleep(1)
                print(f"<{target.name}は毒にかかった！>")

    def paralysis_attack(self, target):
        print(f"{self.name}の電撃！")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.25:
            success = target.apply_status("paralysis_turn", 1)
            if success:
                time.sleep(1)
                print(f"<{target.name}は麻痺にかかった！>")

    def choose_attack(self):

        hp_ratio = self.hp / self.maxhp

        selected_id = random.choices(
            list(self.attacks.keys()), #キー(数字)を返す
            [data["weight"](hp_ratio) for data in self.attacks.values()], # values()で{"name"...}の部分を取得
            k=1
        )[0]

        return selected_id

    def choose_target(self, targets):
        living_targets = [target for target in targets if target.hp > 0]

        if not living_targets:
            return None

        return self.target_selector(living_targets)

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
            print("<アイテムが存在しません>")
            return None
        elif self.items[item_id]['count'] <= 0:
            print("<アイテムが存在しません>")
            return None
        else:
            self.items[item_id]['count'] -= 1
            print(f"<{self.items[item_id]['name']}を使用した！(残り{self.items[item_id]['count']}個)>")
            return self.items[item_id]["heal"]


#=======================================================================
# グローバル関数

def create_battle_members() -> tuple[list, list]:
    init_items = deepcopy(items)
    inventory = Inventory(init_items)

    pl1 = Hero("勇者", 200, 30, 20, inventory, speed=15)
    pl2 = Hero("戦士", 150, 0, 40, inventory, speed=8)

    mo1 = Monster("スライムA", 50, 10, slime_attacks, speed=10)
    mo2 = Monster("スライムB", 70, 8, slime_attacks, speed=6)
    mo3 = Monster("ゴブリンA", 80, 15, gobrin_attacks, speed=18, target_selector=select_lowest_hp_ratio_target)

    players = [
        pl1,
        pl2
    ]

    monsters = [
        mo1,
        mo2,
        mo3
    ]

    return players, monsters

def calculation_damage(attack_power) -> int:

    fluctuation = 25 #ダメージ揺らぎ％

    damage = round(attack_power*(1 + random.randint(-fluctuation,fluctuation)/100))

    p_critical = 20 #クリティカル確率％

    if random.random() < p_critical/100:
        damage = 2*damage
        print("<クリティカル！>")

    return damage

# def calculation_heal_hp(healpt_hp) -> int:

#     fluctuation = 10 #回復揺らぎ％

#     damage = round(healpt_hp*(1 + random.randint(-fluctuation,fluctuation)/100))

#     return damage

def get_battle_result(players, monsters):
    # 勝利したチームを返す
    pl_alive = False
    mo_alive = False

    for player in players:
        if player.hp > 0:
            pl_alive = True
    for monster in monsters:
        if monster.hp > 0:
            mo_alive = True

    if pl_alive and mo_alive:
        return None
    elif pl_alive and not mo_alive:
        return "players"
    elif not pl_alive and mo_alive:
        return "monsters"
    else:
        return "draw"

def show_battle_result(win:str, players, monsters):
    time.sleep(1)
    if win == "players":
        print(f"{', '.join(player.name for player in players)}の勝利！")
    elif win == "monsters":
        print(f"{', '.join(monster.name for monster in monsters)}の勝利！")
    elif win == "draw":
        print("引き分け！")

def input_int(message="数字を入力してください：") -> int:
    while True:
        try:
            number = int(input(message))
            break
        except ValueError:
            print("数字を入力してください!")
            continue
    return number

def get_turn_order(players, monsters):
    living_characters = [
        character
        for character in players + monsters
        if character.hp > 0
    ]

    return sorted(
        living_characters,
        key=lambda character: character.speed,
        reverse=True,
    )

def select_random_target(candidates):
    return random.choice(candidates)

def select_lowest_hp_ratio_target(candidates):
    lowest_hp_target = min(candidates, key=lambda x: x.hp / x.maxhp)
    return lowest_hp_target

#=======================================================================
# 戦闘の進行処理

def battle(players, monsters):

    print(
        "==============================================\n"
        "Battle!!\n"
        f"{', '.join(player.name for player in players)} vs {', '.join(monster.name for monster in monsters)}\n"
        "=============================================="
    )
    print()

    time.sleep(1)

    win = get_battle_result(players, monsters)
    if win is not None:
        show_battle_result(win, players, monsters)
        return win

    nround = 1

    while True:

        print(f"ROUND{nround}")
        nround += 1

        order = get_turn_order(players, monsters)
        print(f"[ {' -> '.join(character.name for character in order)} ]")
        time.sleep(1)
        print()

        for character in order:

            process_turn(character, players, monsters)

            win = get_battle_result(players, monsters)
            if win is not None:
                show_battle_result(win, players, monsters)
                return win

            time.sleep(1)
            print()

def process_turn(character, players, monsters):
    character.start_turn()

    print(f"【{character.name}のターン】")

    if character.hp <= 0:
        print(f"<{character.name}は倒れている！>")
        return

    character.show_status()

    can_act = character.check_debuff()

    if character.hp <= 0:
        character.check_down()
        return

    if not can_act:
        return

    if character in players:

        success = character.choose_action(monsters, players)

        if not success:
            return

    elif character in monsters:
        target = character.choose_target(players)

        if target is None:
            return

        character.act(target)
        target.check_down()

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
        "============\n"
        "| RPGゲーム|\n"
        "============\n"
    )

    time.sleep(1)

    players, monsters = create_battle_members()

    win = battle(players, monsters)

    time.sleep(1)

    if win == "players":
        print("次の冒険へ進みます...")
    elif win == "monsters":
        print("ゲームオーバー")
    elif win == "draw":
        print("戦闘は引き分けでした")

#=======================================================================

if __name__ == "__main__":
    main()
