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

    def check_debuff(self) -> bool: # Falseでターンが飛ばされる
        can_act = True

        if self.status['paralysis_turn'] > 0:
            print()
            print(f"{self.name}は痺れている！(残り{self.status['paralysis_turn']-1}ターン)")

            paralysis_damage = 5

            self.take_damage(paralysis_damage)
            self.status['paralysis_turn'] -= 1
            print()

            can_act = False

        if self.status['poison_turn'] > 0:
            print()
            print(f"{self.name}は毒に侵されている！(残り{self.status['poison_turn']-1}ターン)")

            poison_damage = 15

            self.take_damage(poison_damage)
            self.status['poison_turn'] -= 1
            print()

        return can_act

    def heal_hp(self, healpt):
        self.hp = min(self.hp + healpt, self.maxhp)

    def show_status(self):
        print(f"{self.name} HP: {self.hp}/{self.maxhp}")


class Hero(Player):

    def __init__(self, name, maxhp, maxmp, attack_power):
        super().__init__(name, maxhp, attack_power)
        self.mp = maxmp
        self.maxmp = maxmp

    def use_mp(self, mpcost):
        self.mp -= mpcost

    def use_item(self, item_id) -> bool:

        if item_id not in items:
            print("アイテムが存在しません")
            return False

        item_data = items[item_id]

        if item_data["count"] <= 0:
            print("そのアイテムはもうありません")
            return False

        print(f"{item_data['name']}を使った！")
        self.heal_hp(item_data["heal"])

        item_data['count'] -= 1

        print(f"{self.name}は{item_data['heal']}の回復！(残HP{self.hp}/{self.maxhp})")
        return True

    def choose_item(self) -> bool:
        while True:
            for item_id, item_data in items.items():
                print(f"└[{item_id}: {item_data['name']}(+HP{item_data['heal']}) × {item_data['count']}]")
            print("└[-1: 戻る]")

            try:
                item_id = int(input(
                            "アイテムを選択してください："
                        ))
            except ValueError:
                print("数字を入力してください！")
                continue

            if item_id == -1:
                return False

            if self.use_item(item_id):
                return True

    def choose_action(self, target) -> bool:
        while True:

            try:
                action = int(input(
                    "行動を決めてください\n"
                    "[0:攻撃 1:アイテム 2:ファイア(MP10)]:"
                ))
            except ValueError:
                print("数字を入力してください！")
                return False

            print()

            if action == 0:
                self.attack(target)
                return True
            elif action == 1:
                success = self.choose_item()
                if not success:
                    continue
                return True
            elif action == 2:
                success = self.fire(target)
                if not success:
                    return False
                return True
            else:
                return False

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

    def __init__(self, name, maxhp, attack_power):
        super().__init__(name, maxhp, attack_power)

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
            target.status['poison_turn'] = 3
            print(f"{target.name}は毒にかかった！")

    def paralysis_attack(self, target):
        print(f"{self.name}の電撃！")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.25:
            target.status['paralysis_turn'] = 3
            print(f"{target.name}は麻痺にかかった！")

#=======================================================================

def calculation_damage(attack_power) -> int:

    fluctuation = 25 #ダメージ揺らぎ％

    damage = round(attack_power*(1 + random.randint(-fluctuation,fluctuation)/100))

    p_critical = 25 #クリティカル確率％

    if random.random() < p_critical/100:
        damage = 2*damage
        print("クリティカル！")

    return damage

#=======================================================================

def battle(player:Player, monster:Player):

    print(
        "======================\n"
        "Battle!!\n"
        f"{player.name} vs {monster.name}\n"
        "======================"
    )
    print()

    time.sleep(1)

    turn ="player"

    while True:

        if turn == "player":

            player.show_status()

            success = player.check_debuff()

            if not success:
                turn = "monster"
                continue

            if player.hp <= 0:
                print(f"<< {monster.name}の勝利 >>")
                break

            success = player.choose_action(monster)

            if not success:
                continue

            time.sleep(2)
            print()

            if monster.hp <= 0:
                print(f"<< {player.name}の勝利 >>")
                break

            turn = "monster"

        if turn == "monster":

            monster.show_status()

            p_special = 10 # 特殊攻撃確率％
            p_poison = 10 # 毒攻撃確率％
            p_paralysis = 10 # 麻痺攻撃確率％

            if random.random() < p_special/100:
                monster.special_attack(player)
            elif random.random() < p_poison/100:
                monster.poison_attack(player)
            elif random.random() < p_paralysis/100:
                monster.paralysis_attack(player)
            else:
                monster.attack(player)
            time.sleep(2)
            print()

            if player.hp <= 0:
                print(f"<< {monster.name}の勝利 >>")
                break

            turn = "player"

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

#=======================================================================


def main():

    print(
        "======================\n"
        "RPGゲーム\n"
        "======================\n"
    )

    time.sleep(1)

    player = Hero("勇者", 100, 30, 20)
    slime = Monster("スライム", 100, 18)

    battle(player, slime)

if __name__ == "__main__":
    main()
