import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 650  # ゲームウィンドウの幅
HEIGHT = 750  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内にあるか判定し、真理値を返す
    引数：obj_rct (Rect) - 判定するオブジェクトのRect
    戻り値：(横方向, 縦方向) のタプル。画面内ならTrue
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right: yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom: tate = False
    return yoko, tate

def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    ある地点(org)から目標地点(dst)への方向ベクトル（単位ベクトル）を計算する
    引数：org - 出発点Rect, dst - 目標点Rect
    戻り値：(x方向, y方向) の単位ベクトル
    """
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    return x_diff/norm, y_diff/norm

class Bird(pg.sprite.Sprite):
    """
    プレイヤーキャラクター（こうかとん）を制御するクラス
    移動、HP管理、無敵時間の処理を担当する
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_w: (0, -1),
        pg.K_s: (0, +1),
        pg.K_a: (-1, 0),
        pg.K_d: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとんを初期化する
        num: 画像番号, xy: 初期座標
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self.imgs = {
            (+1, 0): img, (+1, -1): pg.transform.rotozoom(img, 45, 0.9),
            (0, -1): pg.transform.rotozoom(img, 90, 0.9), (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),
            (-1, 0): img0, (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),
            (0, +1): pg.transform.rotozoom(img, -90, 0.9), (+1, +1): pg.transform.rotozoom(img, -45, 0.9),
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect(center=xy)
        self.speed = 10
        
        # ステータス設定
        self.hp = 100         # 現在のHP
        self.max_hp = 100     # 最大HP
        self.state = "normal" # 状態（normal/hyper）
        self.hyper_life = 0   # 無敵の残り時間（フレーム数）

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとんの画像を一時的に変更する（喜び・悲しみエフェクト用）
        """
        self.image = pg.transform.rotozoom(
            pg.image.load(f"fig/{num}.png"), 0, 0.9
        )
        screen.blit(self.image, self.rect)

    def draw_hp_bar(self, screen: pg.Surface):
        """こうかとんの頭上にHPバーを描画する"""
        bar_w, bar_h = 80, 10
        # 背面の赤いバー（減少分）
        pg.draw.rect(screen, (255, 0, 0), [self.rect.centerx - bar_w//2, self.rect.top - 20, bar_w, bar_h])
        # 前面の緑バー（現在値）
        if self.hp > 0:
            pg.draw.rect(screen, (0, 255, 0), [self.rect.centerx - bar_w//2, self.rect.top - 20, int(bar_w * (self.hp/self.max_hp)), bar_h])
        # 白い枠線
        pg.draw.rect(screen, (255, 255, 255), [self.rect.centerx - bar_w//2, self.rect.top - 20, bar_w, bar_h], 1)
    
    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        こうかとんの移動と無敵状態の更新を行う
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]; sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        
        # 無敵状態の処理
        if self.state == "hyper":
            self.hyper_life -= 1
            if self.hyper_life % 2 == 0: # 点滅させる
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)
            if self.hyper_life < 0:
                self.state = "normal"
                self.image.set_alpha(255)
        
        screen.blit(self.image, self.rect)
        self.draw_hp_bar(screen)

class Bomb(pg.sprite.Sprite):
    """
    敵が発射する爆弾に関するクラス
    """
    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾を生成し、こうかとんの方向へ飛ばす
        """
        super().__init__()
        rad = random.randint(10, 40)
        self.image = pg.Surface((2*rad, 2*rad), pg.SRCALPHA)
        pg.draw.circle(self.image, (random.randint(50, 255), 0, 0), (rad, rad), rad)
        self.rect = self.image.get_rect(center=emy.rect.center)
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.speed = 6
        self.power = 34 # ダメージ量（34 * 3 = 102 なので3発で死ぬ）

    def update(self):
        """爆弾を移動させ、画面外に出たら削除する"""
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True): self.kill()

class Beam(pg.sprite.Sprite):
    """
    こうかとんが放つビームに関するクラス
    """
    def __init__(self, bird: Bird, dire: tuple[float, float] | None = None):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        引数 dire：発射方向ベクトル (vx, vy)。Noneならbird.direを使う
        """
        super().__init__()

        if dire is None:
            vx, vy = bird.dire
        else:
            vx, vy = dire

        # 正規化（ゼロ除算対策）
        norm = math.sqrt(vx*vx + vy*vy)
        if norm == 0:
            vx, vy = 1.0, 0.0
            norm = 1.0
        self.vx, self.vy = vx / norm, vy / norm

        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/star.png"), angle, 1.0)

        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True): self.kill()

class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()

class DamageText(pg.sprite.Sprite):
    """
    ダメージ値を画面上にポップアップ表示するクラス
    """
    def __init__(self, damage: int, center: tuple[int, int], color=(255, 0, 0)):
        super().__init__()
        self.image = pg.font.Font(None, 40).render(str(damage), True, color)
        self.rect = self.image.get_rect(center=center)
        self.life, self.vy = 30, -2 # 30フレーム表示し、上に移動する
    def update(self):
        self.rect.y += self.vy; self.life -= 1
        if self.life < 0: self.kill()

class Enemy(pg.sprite.Sprite):
    """
    敵機（エイリアン）に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


# class Score:
#     """
#     打ち落とした爆弾，敵機の数をスコアとして表示するクラス
#     爆弾：1点
#     敵機：10点
#     """
#     def __init__(self):
#         self.font = pg.font.Font(None, 50)
#         self.color = (0, 0, 255)
#         self.value = 0
#         self.image = self.font.render(f"Score: {self.value}", 0, self.color)
#         self.rect = self.image.get_rect()
#         self.rect.center = 100, HEIGHT-50

#     def update(self, screen: pg.Surface):
#         self.image = self.font.render(f"Score: {self.value}", 0, self.color)
#         screen.blit(self.image, self.rect)

def nearest_enemy(bird: Bird, emys: pg.sprite.Group) -> Enemy | None:
    """
    最も近い敵を探す関数
    """
    if len(emys) == 0:
        return None
    bx, by = bird.rect.center
    return min(emys, key=lambda e: (e.rect.centerx - bx)**2 + (e.rect.centery - by)**2)

def main():
    pg.display.set_caption("こーかとん伝説")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    # score = Score()

    bird = Bird(3, (330, 600))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    clock = pg.time.Clock()
    tmr = 0
    AUTO_FIRE_INTERVAL = 30  # 発射速度、増やすと発射間隔が開く

    while True:
        key_lst = pg.key.get_pressed()
        manual_input = any(key_lst[k] for k in Bird.delta.keys()) or key_lst[pg.K_SPACE]
        for event in pg.event.get():  # キー入力がないとき弾を発射する
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                manual_input = True
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))

        screen.blit(bg_img, [0, 0])

        # 弾の自動発射
        if not manual_input and tmr % AUTO_FIRE_INTERVAL == 0:
            target = nearest_enemy(bird, emys)
            if target is not None:
                dx = target.rect.centerx - bird.rect.centerx
                dy = target.rect.centery - bird.rect.centery
                beams.add(Beam(bird, (dx, dy)))

        if tmr%50 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.rect.centery >= emy.bound and tmr % emy.interval == 0: 
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            # score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            # score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            # score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        # score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50) # 50 FPSに固定

if __name__ == "__main__":
    pg.init(); main(); pg.quit(); sys.exit()