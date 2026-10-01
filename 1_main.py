# File: 1_main.py
import random
import time
from copy import deepcopy


# =======================================================================
# キャラクター


class Player:
    def __init__(self, name, maxhp, attack_power, speed=10):
        self.name = name
        self.hp = maxhp
        self.maxhp = maxhp
        self.attack_power = attack_power
        self.speed = speed
        self.is_defending = False
        self.status = {
            key: 0
            for key in status_definitions
        }

    def attack(self, target):
        print(f"{self.name}の攻撃！")

        damage = calculation_damage(self.get_attack_power())
        target.take_damage(damage)

    def defend(self):
        self.is_defending = True
        print(f"<{self.name}は身構えた！>")

    def start_turn(self):
        self.is_defending = False

    def get_attack_power(self) -> int:
        # 状態から攻撃倍率を求める
        multiplier = 1

        for key, definition in status_definitions.items():
            if self.status[key] > 0:
                multiplier *= definition.get('attack_multiplier', 1)

        return round(self.attack_power * multiplier)

    def take_damage(self, damage):
        if self.is_defending:
            damage = (damage + 1) // 2

        self.hp = max(self.hp - damage, 0)

        print(
            f"<{self.name}に{damage}のダメージ！"
            f"(残HP{self.hp}/{self.maxhp})>"
        )

    def apply_status(self, debuff_key, turn) -> bool:
        if debuff_key not in self.status:
            return False
        if self.hp <= 0:
            return False
        if turn <= 0:
            return False

        self.status[debuff_key] = max(
            turn,
            self.status[debuff_key],
        )
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

    def inflict_status(self, debuff_key, turn) -> bool:
        applied = self.apply_status(debuff_key, turn)

        if applied:
            time.sleep(1)
            print(f"<{self.name}は{status_definitions[debuff_key]['label']}にかかった！>")

        return applied

    def get_status_text(self) -> str:

        status_text = ""

        for key, definition in status_definitions.items():
            if self.status[key] > 0:
                status_text += f"({definition['label']}{self.status[key]}ターン)"

        return status_text

    def check_debuff(self) -> bool:
        # Falseなら行動できない
        if self.hp <= 0:
            return False

        can_act = True

        for key, definition in status_definitions.items():
            if self.status[key] <= 0:
                continue

            print()
            time.sleep(1)

            if definition["blocks_action"]:
                can_act = False

            print(
                f"<{self.name}は{definition['message']}"
                f"(残り{self.status[key] - 1}ターン)>"
            )

            self.take_damage(definition["damage"])
            self.status[key] -= 1

            time.sleep(1)

            if self.hp <= 0:
                return False

            print()

        return can_act

    def heal_hp(self, healpt) -> int:
        hp_before = self.hp
        self.hp = min(self.hp + healpt, self.maxhp)

        return self.hp - hp_before

    def check_down(self):
        if self.hp <= 0:
            time.sleep(1)
            print(f"<{self.name}は倒れた！>")

class Hero(Player):
    def __init__(
        self,
        name,
        maxhp,
        maxmp,
        attack_power,
        inventory,
        speed=10,
        input_func=None
    ):
        super().__init__(name, maxhp, attack_power, speed)

        self.mp = maxmp
        self.maxmp = maxmp
        self.inventory = inventory
        self.level = 1
        self.exp = 0

        if input_func is None:
            self.input_func = input_int
        else:
            self.input_func = input_func

    def show_status(self):
        print(
            f"{self.name}"
            f"(Lv.{self.level}) "
            f"HP: {self.hp}/{self.maxhp} "
            f"MP: {self.mp}/{self.maxmp}",
            self.get_status_text()
        )

    def gain_exp(self, amount) -> int:
        # 上昇レベルを返す
        if amount <= 0:
            return 0

        before_level = self.level
        self.exp += amount

        while self.exp >= self.level * level_settings["exp_per_level"]:
            self.exp -= self.level * level_settings["exp_per_level"]
            self.level += 1

            self.maxhp += level_settings["maxhp"]
            self.hp += level_settings["maxhp"]
            self.attack_power += level_settings["attack_power"]

            time.sleep(0.5)
            print(f"<{self.name}はレベル{self.level}に上がった！>")

        return self.level - before_level

    def use_mp(self, mpcost) -> bool:
        if mpcost < 0:
            return False
        if self.mp < mpcost:
            return False

        self.mp -= mpcost
        return True

    def use_item(self, item_id) -> bool:
        heal_pt = self.inventory.use(item_id)

        if heal_pt is None:
            return False

        actual_heal_pt = self.heal_hp(heal_pt)

        print(
            f"<{self.name}は{actual_heal_pt}の回復！"
            f"(残HP{self.hp}/{self.maxhp})>"
        )
        return True

    def choose_item(self) -> bool:
        while True:
            self.inventory.show_items()
            print("└[-1: 戻る]")

            item_id = self.input_func(
                "使用するアイテムを選んでください："
            )

            if item_id == -1:
                return False

            if self.use_item(item_id):
                return True

    def choose_action(self, targets, allies) -> bool:
        while True:
            action = self.input_func(
                "行動を決めてください\n"
                "[0:攻撃 1:アイテム 2:魔法 3:防御]："
            )

            print()

            if action == 0:
                success, selected_id = self.choose_target(targets)

                if not success:
                    continue

                target = targets[selected_id]
                self.attack(target)
                target.check_down()

                return True

            elif action == 1:
                if not self.choose_item():
                    continue

                return True

            elif action == 2:
                if not self.choose_magic_action(targets, allies):
                    continue

                return True

            elif action == 3:
                self.defend()
                return True

            else:
                print("選択肢から選んでください")

    def choose_magic_action(self, targets, allies) -> bool:
        magic_dict = self.get_magic_action()

        while True:
            for magic_id, data in magic_dict.items():
                print(f"└[{magic_id}: {data['label']}]")

            print("└[-1: 戻る]")

            selected_id = self.input_func("魔法を選択してください：")

            if selected_id == -1:
                return False

            if selected_id not in magic_dict:
                print("<魔法が存在しません>")
                continue

            selected_magic = magic_dict[selected_id]

            if self.mp < selected_magic["mpcost"]:
                print("<MPが足りません！>")
                continue

            if selected_magic["target_side"] == "enemy":
                candidates = targets
            elif selected_magic["target_side"] == "ally":
                candidates = allies
            else:
                raise ValueError("魔法の対象設定が不正です")

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
            for index, target in enumerate(targets):
                print(
                    f"└[{index}: {target.name}"
                    f"(HP{target.hp}/{target.maxhp})]",
                    target.get_status_text()
                )

            print("└[-1: 戻る]")

            selected_id = self.input_func("対象を選択してください：")

            if selected_id == -1:
                return False, selected_id

            if selected_id < 0 or selected_id >= len(targets):
                print("<対象が存在しません>")
                continue

            if targets[selected_id].hp <= 0:
                print("<戦闘不能の対象は選べません>")
                continue

            print()
            return True, selected_id

    def get_magic_action(self):
        return {
            2: {
                "label": f"ファイア(MP{magic_mpcosts['fire']})",
                "target_side": "enemy",
                "function": self.fire_magic,
                "mpcost": magic_mpcosts["fire"],
            },
            3: {
                "label": f"ポイズン(MP{magic_mpcosts['poison']})",
                "target_side": "enemy",
                "function": self.poison_magic,
                "mpcost": magic_mpcosts["poison"],
            },
            4: {
                "label": f"ヒール(MP{magic_mpcosts['heal']})",
                "target_side": "ally",
                "function": self.heal_magic,
                "mpcost": magic_mpcosts["heal"],
            },
            5: {
                "label": f"キュア(MP{magic_mpcosts['cure']})",
                "target_side": "ally",
                "function": self.cure_magic,
                "mpcost": magic_mpcosts["cure"],
            },
        }

    def fire_magic(self, target) -> bool:
        mpcost = magic_mpcosts["fire"]

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False

        if not self.use_mp(mpcost):
            print("<MPが足りません！>")
            return False

        print(
            f"<{self.name}のファイアが発動！"
            f"(残MP{self.mp}/{self.maxmp})>"
        )

        damage = calculation_damage(self.get_attack_power())
        damage = round(damage * 1.3)
        target.take_damage(damage)

        if target.hp > 0:
            if random.random() <= 0.3:
                target.inflict_status("burn_turn", 3)

        return True

    def poison_magic(self, target) -> bool:
        # 発動の成否がTF
        mpcost = magic_mpcosts["poison"]

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

        damage = calculation_damage(self.get_attack_power())
        damage = round(damage * 0.5)
        target.take_damage(damage)

        if target.hp > 0:
            target.inflict_status("poison_turn", 3)

        return True

    def heal_magic(self, target) -> bool:
        mpcost = magic_mpcosts["heal"]

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False

        if target.hp == target.maxhp:
            print("<すでにHPは最大です>")
            return False

        if not self.use_mp(mpcost):
            print("<MPが足りません！>")
            return False

        actual_heal = target.heal_hp(50)

        print(
            f"{self.name}のヒールが発動！\n"
            f"{target.name}は{actual_heal}の回復！"
            f"(残HP{target.hp}/{target.maxhp})"
        )
        return True

    def cure_magic(self, target) -> bool:
        mpcost = magic_mpcosts["cure"]

        if target.hp <= 0:
            print("<戦闘不能キャラです>")
            return False

        if target.status["poison_turn"] <= 0:
            print("<対象は毒にかかっていません>")
            return False

        if not self.use_mp(mpcost):
            print("<MPが足りません！>")
            return False

        target.clear_status("poison_turn")

        print(
            f"<{self.name}のキュアが発動！>\n"
            f"<{target.name}の毒が治癒した！>"
        )
        return True

class Monster(Player):

    def __init__(
        self,
        name,
        maxhp,
        attack_power,
        attacks,
        speed=10,
        target_selector=None,
        attack_chooser=None,
        exp=0,
    ):
        super().__init__(name, maxhp, attack_power, speed)

        self.attacks = attacks
        self.exp = exp

        if target_selector is None:
            self.target_selector = select_random_target
        else:
            self.target_selector = target_selector

        if attack_chooser is None:
            self.attack_chooser = select_weighted_attack
        else:
            self.attack_chooser = attack_chooser

    def show_status(self):
        print(f"{self.name} HP: {self.hp}/{self.maxhp}", self.get_status_text())

    def special_attack(self, target):
        print(f"<{self.name}の体当たり！>")

        damage = calculation_damage(self.get_attack_power())
        damage = round(damage * 1.1)
        target.take_damage(damage)

    def poison_attack(self, target):
        print(f"<{self.name}の毒液！>")

        damage = calculation_damage(self.get_attack_power())
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.75:
            target.inflict_status("poison_turn", 3)

    def paralysis_attack(self, target):
        print(f"{self.name}の電撃！")

        damage = calculation_damage(self.get_attack_power())
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.25:
            target.inflict_status("paralysis_turn", 1)

    def choose_attack(self) -> int:
        # attacksのidを返す
        hp_ratio = self.hp / self.maxhp

        attack_id = self.attack_chooser(self.attacks, hp_ratio)

        return attack_id

    def choose_target(self, targets):
        living_targets = [
            target for target in targets if target.hp > 0
        ]

        if not living_targets:
            return None

        return self.target_selector(living_targets)

    def act(self, target):
        attack_id = self.choose_attack()
        self.attacks[attack_id]["function"](self, target)


# =======================================================================
# 所持品


class Inventory:
    def __init__(self, items):
        self.items = items

    def show_items(self):
        for item_id, data in self.items.items():
            print(
                f"└[{item_id}: {data['name']}"
                f"(+HP{data['heal']}) × {data['count']}]"
            )

    def use(self, item_id):
        if item_id not in self.items:
            print("<アイテムが存在しません>")
            return None

        if self.items[item_id]["count"] <= 0:
            print("<アイテムが存在しません>")
            return None

        data = self.items[item_id]
        data["count"] -= 1

        print(
            f"<{data['name']}を使用した！"
            f"(残り{data['count']}個)>"
        )
        return data["heal"]


# =======================================================================
# グローバル関数


def create_battle_members(input_func=None) -> tuple[list, list]:
    inventory = Inventory(deepcopy(items))

    players = [
        Hero(
            "勇者",
            200,
            30,
            20,
            inventory,
            speed=15,
            input_func=input_func
        ),
        Hero(
            "戦士",
            150,
            0,
            40,
            inventory,
            speed=8,
            input_func=input_func
        ),
    ]

    monsters = [
        Monster(
            "スライムA",
            50,
            10,
            slime_attacks,
            speed=10,
            exp=8,
        ),
        Monster(
            "スライムB",
            70,
            8,
            slime_attacks,
            speed=6,
            exp=10,
        ),
        Monster(
            "ゴブリンA",
            80,
            15,
            gobrin_attacks,
            speed=18,
            target_selector=select_lowest_hp_ratio_target,
            exp=20,
        ),
    ]

    return players, monsters


def calculation_damage(attack_power) -> int:
    fluctuation = 25

    damage = round(
        attack_power
        * (1 + random.randint(-fluctuation, fluctuation) / 100)
    )

    critical_percent = 20

    if random.random() < critical_percent / 100:
        damage *= 2
        print("<クリティカル！>")

    return damage


def distribute_exp(players, monsters) -> int:
    total_exp = sum(monster.exp for monster in monsters if monster.hp <= 0)

    time.sleep(1)
    print(f"{total_exp}経験値を獲得！")

    for player in players:
        if player.hp > 0:
            player.gain_exp(total_exp)

    return total_exp


def get_battle_result(players, monsters):
    player_alive = False
    monster_alive = False

    for player in players:
        if player.hp > 0:
            player_alive = True

    for monster in monsters:
        if monster.hp > 0:
            monster_alive = True

    if player_alive and monster_alive:
        return None
    elif player_alive:
        return "players"
    elif monster_alive:
        return "monsters"
    else:
        return "draw"


def show_battle_result(win: str, players, monsters):
    time.sleep(1)

    if win == "players":
        names = ", ".join(player.name for player in players)
        print(f"{names}の勝利！")
    elif win == "monsters":
        names = ", ".join(monster.name for monster in monsters)
        print(f"{names}の勝利！")
    elif win == "draw":
        print("引き分け！")


def input_int(message="数字を入力してください：") -> int:
    while True:
        try:
            return int(input(message))
        except ValueError:
            print("数字を入力してください!")


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
    return min(
        candidates,
        key=lambda character: character.hp / character.maxhp,
    )


def select_weighted_attack(attacks, hp_ratio) -> int:
    # 攻撃idを返す
    return random.choices(
        list(attacks.keys()),
        weights=[
            data["weight"](hp_ratio)
            for data in attacks.values()
        ],
        k=1,
    )[0]

# =======================================================================
# 戦闘進行


def battle(players, monsters):
    player_names = ", ".join(player.name for player in players)
    monster_names = ", ".join(monster.name for monster in monsters)

    print(
        "==============================================\n"
        "Battle!!\n"
        f"{player_names} vs {monster_names}\n"
        "=============================================="
    )
    print()
    time.sleep(1)

    win = get_battle_result(players, monsters)

    if win is not None:
        show_battle_result(win, players, monsters)
        return win

    round_number = 1

    while True:
        print(f"ROUND{round_number}")
        round_number += 1

        order = get_turn_order(players, monsters)
        order_names = " -> ".join(
            character.name for character in order
        )

        print(f"[ {order_names} ]")
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


def process_turn(character, players, monsters) -> None:
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
        character.choose_action(monsters, players)

    elif character in monsters:
        target = character.choose_target(players)

        if target is None:
            return

        character.act(target)
        target.check_down()


# =======================================================================
# 定義データ
# itemsは初期定義として扱い、ゲーム開始時にdeepcopyする。


items = {
    0: {
        "key": "potion",
        "name": "回復薬",
        "heal": 30,
        "count": 3,
    },
    1: {
        "key": "high_potion",
        "name": "上級回復薬",
        "heal": 60,
        "count": 1,
    },
}

slime_attacks = {
    0: {
        "name": "攻撃",
        "function": Player.attack,
        "weight": lambda hp_ratio: 10,
    },
    1: {
        "name": "体当たり",
        "function": Monster.special_attack,
        "weight": lambda hp_ratio: -10 * hp_ratio + 15,
    },
    2: {
        "name": "毒液",
        "function": Monster.poison_attack,
        "weight": lambda hp_ratio: -10 * hp_ratio + 15,
    },
    3: {
        "name": "電撃",
        "function": Monster.paralysis_attack,
        "weight": lambda hp_ratio: -10 * hp_ratio + 15,
    },
}

gobrin_attacks = {
    10: {
        "name": "攻撃",
        "function": Player.attack,
        "weight": lambda hp_ratio: 3,
    },
    20: {
        "name": "体当たり",
        "function": Monster.special_attack,
        "weight": lambda hp_ratio: 7,
    },
}

status_definitions = {
    "paralysis_turn": {
        "label": "麻痺",
        "message": "痺れている!",
        "damage": 5,
        "blocks_action": True,
    },
    "poison_turn": {
        "label": "毒",
        "message": "毒に侵されている!",
        "damage": 15,
        "blocks_action": False,
    },
    "burn_turn": {
        "label": "火傷",
        "message": "火傷が痛む!",
        "damage": 8,
        "blocks_action": False,
        "attack_multiplier": 0.5
    },
}

magic_mpcosts = {
    "fire": 10,
    "poison":6,
    "heal":8,
    "cure": 5
}

level_settings = {
    "exp_per_level": 30,
    "maxhp": 20,
    "attack_power": 4,
}

# =======================================================================
# 起動処理


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
        distribute_exp(players, monsters)
        time.sleep(1)
        print("次の冒険へ進みます...")
    elif win == "monsters":
        print("ゲームオーバー")
    elif win == "draw":
        print("戦闘は引き分けでした")


if __name__ == "__main__":
    main()
