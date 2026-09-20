# 確率で決定される処理をスマートにしたい

## 要件
・A: 80% B: 10% C: 10%のような確率(または比)が決まっている
・Dのようなものが増えても簡単に追加できる処理
・確率がある変数xに対する関数となるような仕様を組み込める

## 自分の考え

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
        "class": "warrior"
    },
    1: {
        "name": "B",
        "prob_ratio": 5,
        "class": "swordman"
    },
    2: {
        "name": "C",
        "prob_ratio": 1,
        "class": "mage"
    },
}

roll = random.random()

for prob in prob:


#
