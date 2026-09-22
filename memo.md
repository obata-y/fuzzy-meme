# 確率で決定される処理をスマートにしたい

## 要件
・A: 80% B: 10% C: 10%のような確率(または比)が決まっている
・Dのようなものが増えても簡単に追加できる処理
・確率がある変数xに対する関数となるような仕様を組み込める

## 案

①確率をきっちり守る
p_a = 10
p_b = 10

roll = random.random() * 100

if roll <= p_a:
    action_a()
elif roll <= p_a + p_b:
    action_b()
else:
    action_else()

問題点：追加がちょっとめんどい

②比で確率を設定
probs = {
    0: {
        "name": "A",
        "prob_ratio": 3,
        "function": "action_a"
    },
    1: {
        "name": "B",
        "prob_ratio": 5,
        "function": "action_b"
    },
    2: {
        "name": "C",
        "prob_ratio": 1,
        "function": "action_c"
    },
}

roll = random.random()
total_ratio = sum(prob["prob_ratio"] for prob in prpbs)

for prob in prob:
    accum_p += prob["prob_ratio"]/total_ratio
    if roll <= accum_p:
        action...

## AIの答え
②の改善: random.choice()という便利なのがある

probs = {
    0: {
        "name": "A",
        "prob_ratio": 3,
        "function": action_a # 関数を入れてもOK
    },
    1: {
        "name": "B",
        "prob_ratio": 1,
        "function": action_b
    },
    2: {
        "name": "C",
        "prob_ratio": 1,
        "function": action_c
    }
}

actions = list(probs.values())

selected = random.choices(　# -> listで返す
    actions, # 抽選候補のリスト
    weights=[action["prob_ratio"] for action in actions], # 重み([3, 1, 1])
    k=1 # 一個選ぶ
)[0] # 選んだものから0個目を返す(一個しか選んでないのでそも0個目しかない)

selected["function"]()

## random.choice()の注意点

for id in slime_attacks で書いたときは「キー」が返る（イテレートの挙動）
slime_attacks[idx] で書いたときは「値（辞書）」が返る（インデックスアクセスの挙動）<- random.choice()はこの方法で第一引数にアクセスしている


# lambdaの使い方を学ぼう

## 例

probs = {
    0: {
        "name": "通常攻撃",
        "prob_wt": lambda hp_ratio: 10,
        "function": action_attack
    },

    1: {
        "name": "特殊攻撃",
        "prob_wt": lambda hp_ratio: 10 * hp_ratio^2 + 20 * hp_ratio + 15,
        "function": action_special
    },

    2: {
        "name": "回復",
        "prob_wt": lambda hp: 10 * hp_ratio^2 + 20 * hp_ratio + 15,
        "function": action_heal
    }
}

hp_ratio = 0.7

actions = list(probs.values())

weights = [
    action["prob_ratio"](x)
    for action in actions
]

print(weights)

selected = random.choices(
    actions,
    weights=weights,
    k=1
)[0]

print(selected["name"])


