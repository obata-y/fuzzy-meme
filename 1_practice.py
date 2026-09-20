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

    def heal_hp(self, healpt):
        self.hp = min(self.hp + healpt, self.maxhp)

    def check_down(self):
        if self.hp <= 0:
            print(f"{self.name}は倒れた！")


class Hero(Player):

    def __init__(self, name, maxhp, maxmp, attack_power):
        super().__init__(name, maxhp, attack_power)
        self.mp = maxmp
        self.maxmp = maxmp

    def show_status(self):
        print(f"{self.name} HP: {self.hp}/{self.maxhp} MP: {self.mp}/{self.maxmp}")

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

    def choose_action(self, targets) -> bool:
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
                return False

    def choose_target(self, targets):
        while True:

            n = len(targets)

            for i, target in enumerate(targets):
                print(f"└[{i}: {target.name}(HP{target.hp}/{target.maxhp})]")
            print("└[-1: 戻る]")

            try:
                selected_id = int(input(
                            "敵を選択してください："
                        ))
            except ValueError:
                print("数字を入力してください！")
                continue

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

    def __init__(self, name, maxhp, attack_power):
        super().__init__(name, maxhp, attack_power)

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
            time.sleep(1)
            target.status['poison_turn'] = 3
            print(f"{target.name}は毒にかかった！")

    def paralysis_attack(self, target):
        print(f"{self.name}の電撃！")

        damage = calculation_damage(self.attack_power)
        damage = round(damage * 0.7)
        target.take_damage(damage)

        if random.random() <= 0.25:
            time.sleep(1)
            target.status['paralysis_turn'] = 1
            print(f"{target.name}は麻痺にかかった！")

    def choose_target(self, targets):
        n = len(targets)

        while True:
            selected_id = random.randrange(0, n)
            if targets[selected_id].hp == 0:
                continue
            break

        return selected_id


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

                p_special = 10 # ％
                p_poison = 10
                p_paralysis = 10

                selected_id = monster.choose_target(players)

                if random.random() < p_special/100:
                    monster.special_attack(players[selected_id])
                elif random.random() < p_poison/100:
                    monster.poison_attack(players[selected_id])
                elif random.random() < p_paralysis/100:
                    monster.paralysis_attack(players[selected_id])
                else:
                    monster.attack(players[selected_id])

                time.sleep(1)

                if players[selected_id].hp <= 0:
                    print()
                    print(f"{players[selected_id].name}は倒れてしまった！")

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

#=======================================================================


def main():

    print(
        "======================\n"
        "RPGゲーム\n"
        "======================\n"
    )

    time.sleep(1)

    players = [
        Hero("勇者", 200, 30, 20),
        Hero("戦士", 150, 0, 40)
    ]

    slimes = [
        Monster("スライムA", 50, 10),
        Monster("スライムB", 70, 8),
        Monster("スライムC", 40, 12)
    ]

    battle(players, slimes)

if __name__ == "__main__":
    main()
