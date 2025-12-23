import math
import os
import random
import sys
import time
import pygame as pg

# =====================
# 基本設定・定数
# =====================
WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# スキル名辞書
SKILL_NAME_MAP = {
    "multi": "連射数UP", 
    "spread": "拡散攻撃", 
    "pierce": "貫通弾", 
    "reflect": "反射弾", 
    "speed": "弾速UP",
    "damage": "攻撃力UP"
}

def get_jp_font(size):
    """日本語フォントを読み込む（環境に合わせてフォールバック）"""
    fonts = ["notosanscjkjp", "meiryo", "yu gothic", "hiraginosans", "msgothic", "arial"]
    return pg.font.SysFont(fonts, size)

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate

def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """orgから見てdstがどこにあるかを計算し、正規化された方向ベクトルを返す"""
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    if norm == 0: return 0, 0
    return x_diff/norm, y_diff/norm

def get_nearest_target(bird, targets):
    """一番近くにあるターゲット（敵または爆弾）を取得する"""
    nearest = None
    min_dist = float('inf')
    for t in targets:
        dx = t.rect.centerx - bird.rect.centerx
        dy = t.rect.centery - bird.rect.centery
        dist = dx*dx + dy*dy
        if dist < min_dist:
            min_dist = dist
            nearest = t
    return nearest

# =====================
# UI クラス・関数
# =====================
def draw_exp_bar(screen, bird):
    """画面上部に経験値バーとレベルを表示"""
    bar_x, bar_y = 20, 20
    bar_w, bar_h = WIDTH - 200, 20
    
    # レベルアップに必要な経験値に対する割合
    ratio = bird.exp / bird.next_exp
    fill_w = int(bar_w * ratio)
    
    pg.draw.rect(screen, (50, 50, 50), [bar_x, bar_y, bar_w, bar_h])
    pg.draw.rect(screen, (0, 200, 255), [bar_x, bar_y, fill_w, bar_h])
    pg.draw.rect(screen, (255, 255, 255), [bar_x, bar_y, bar_w, bar_h], 2)
    
    font = pg.font.Font(None, 40)
    txt = font.render(f"Lv.{bird.level}", True, (255, 255, 255))
    screen.blit(txt, (bar_w + 30, 15))

def draw_skill_select(screen, choices):
    """レベルアップ時のスキル選択画面を描画"""
    overlay = pg.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    font = get_jp_font(30)
    title_font = get_jp_font(60)
    
    title = title_font.render("LEVEL UP!", True, (255, 255, 0))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
    
    msg = font.render("能力を選択してください", True, (200, 200, 200))
    screen.blit(msg, (WIDTH//2 - msg.get_width()//2, 180))

    rects = []
    start_y = 250
    for i, skill_key in enumerate(choices):
        skill_name = SKILL_NAME_MAP.get(skill_key, skill_key)
        rect = pg.Rect(WIDTH//2 - 200, start_y + i * 100, 400, 80)
        
        m_pos = pg.mouse.get_pos()
        # ホバー時の色変化
        if rect.collidepoint(m_pos):
            color = (100, 100, 180) 
            pg.draw.rect(screen, (255, 255, 0), rect, 3, border_radius=10)
        else:
            color = (60, 60, 80)
            pg.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)
            
        pg.draw.rect(screen, color, rect, border_radius=10)
        
        text = font.render(skill_name, True, (255, 255, 255))
        screen.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))
        rects.append((rect, skill_key))
        
    return rects

# =====================
# ゲームオブジェクト
# =====================
class Bird(pg.sprite.Sprite):
    """ゲームキャラクター（こうかとん）に関するクラス"""
    delta = {
        pg.K_UP: (0, -1), pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0), pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
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
        
        # --- スキル・ステータス関連 ---
        self.level = 1
        self.exp = 0
        self.next_exp = 100
        # スキルレベル管理
        self.skill = {
            "multi": 0, "spread": 0, "pierce": 0, "reflect": 0,
            "speed": 0, "damage": 0
        }
        
        self.attack_interval = 40  # 攻撃間隔（フレーム）
        self.timer = 0
        
        # 攻撃の狙いを定めるためのベクトル（オートエイム用）
        self.aim_vec = (1, 0)

    def gain_exp(self, amount):
        """経験値を獲得し、レベルアップ判定を行う"""
        self.exp += amount
        if self.exp >= self.next_exp:
            self.exp -= self.next_exp
            self.level += 1
            self.next_exp = int(self.next_exp * 1.2) + 50
            return True # レベルアップした
        return False

    def change_img(self, num: int, screen: pg.Surface):
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, targets: pg.sprite.Group):
        # 移動処理
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
            
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        # --- オートエイム & 攻撃準備 ---
        nearest = get_nearest_target(self, targets)
        if nearest:
            # 敵がいればそちらを向くベクトルを計算
            self.aim_vec = calc_orientation(self.rect, nearest.rect)
        elif not (sum_mv[0] == 0 and sum_mv[1] == 0):
            # 敵がいなくて移動していれば、移動方向を向く
            norm = math.sqrt(sum_mv[0]**2 + sum_mv[1]**2)
            self.aim_vec = (sum_mv[0]/norm, sum_mv[1]/norm)

        self.timer += 1
        screen.blit(self.image, self.rect)

    def shoot(self, beams_group):
        """現在のスキル状況に応じてビームを発射する"""
        if self.timer < max(5, self.attack_interval - self.skill["speed"] * 2):
            return

        self.timer = 0
        
        n = 1 + self.skill["multi"]
        spread_val = self.skill["spread"]
        
        base_angle = math.degrees(math.atan2(-self.aim_vec[1], self.aim_vec[0]))
        
        # 拡散角度計算
        spread_angle = 10 + (spread_val * 5)
        
        if n == 1:
            beams_group.add(Beam(self, base_angle))
        else:
            # 奇数・偶数弾数に応じて角度を分散
            total_angle = spread_angle * (n - 1)
            start_angle = base_angle - (total_angle / 2)
            for i in range(n):
                angle = start_angle + (spread_angle * i)
                beams_group.add(Beam(self, angle))


class Beam(pg.sprite.Sprite):
    """スキル強化対応ビームクラス"""
    def __init__(self, bird: Bird, angle: float):
        super().__init__()
        self.angle = angle
        self.rad = math.radians(angle)
        self.vx = math.cos(self.rad)
        self.vy = -math.sin(self.rad)
        
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, 1.0)
        self.rect = self.image.get_rect()
        
        # 発射位置を中心に設定
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx * 0.5
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy * 0.5
        
        # スキル値の反映
        self.speed = 10 + bird.skill["speed"]
        self.damage = 1 + bird.skill["damage"]
        self.reflect_count = bird.skill["reflect"]
        self.pierce_count = bird.skill["pierce"]
        
        # 多段ヒット防止用セット
        self.hit_enemies = set()

    def update(self):
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        
        # 画面端での判定（反射 or 消滅）
        yoko, tate = check_bound(self.rect)
        if not yoko:
            if self.reflect_count > 0:
                self.vx *= -1
                self.reflect_count -= 1
                # 画像の回転は複雑になるので今回は省略するか、簡易的に反転
                self.angle = 180 - self.angle
                self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, 1.0)
            else:
                self.kill()
        
        if not tate:
            if self.reflect_count > 0:
                self.vy *= -1
                self.reflect_count -= 1
                self.angle = -self.angle
                self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), self.angle, 1.0)
            else:
                self.kill()


class Enemy(pg.sprite.Sprite):
    """敵機クラス（HP制）"""
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self, level=1):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +random.randint(3, 6)
        self.bound = random.randint(50, HEIGHT//2)
        self.state = "down"
        self.interval = random.randint(50, 300)

        self.max_hp = 1
        self.hp = self.max_hp

    def update(self):
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)

    def draw_hp(self, screen):
        """簡易HPバー描画"""
        if self.hp < self.max_hp:
            bar_w = self.rect.width
            fill = (self.hp / self.max_hp) * bar_w
            pg.draw.rect(screen, (255,0,0), [self.rect.left, self.rect.top-5, fill, 4])


class Bomb(pg.sprite.Sprite):
    """爆弾クラス"""
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: Enemy, bird: Bird):
        super().__init__()
        rad = random.randint(10, 50)
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery + emy.rect.height//2
        self.speed = 6
        self.hp = 1 # 爆弾は1発で壊れる

    def update(self):
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """爆発クラス"""
    def __init__(self, obj, life: int):
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Score:
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


# =====================
# メインループ
# =====================
def main():
    pg.display.set_caption("真！こうかとん無双 - Survivor Mode")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    
    # ゲーム状態管理: PLAY, SELECT, GAMEOVER
    game_state = "PLAY"
    skill_choices = []
    choice_rects = []

    while True:
        # イベント処理
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            
            # スキル選択時のクリック処理
            if game_state == "SELECT" and event.type == pg.MOUSEBUTTONDOWN:
                m_pos = pg.mouse.get_pos()
                for rect, key in choice_rects:
                    if rect.collidepoint(m_pos):
                        bird.skill[key] += 1
                        game_state = "PLAY"
                        break

        # 背景描画
        screen.blit(bg_img, [0, 0])

        # === ゲームプレイ中 ===
        if game_state == "PLAY":
            key_lst = pg.key.get_pressed()

            # 敵の出現
            if tmr % 10 == 0:
                # 時間経過で敵が少し強くなる
                difficulty = 1 + (tmr // 1000)
                emys.add(Enemy(level=difficulty))

            # 爆弾投下
            for emy in emys:
                if emy.state == "stop" and tmr % emy.interval == 0:
                    bombs.add(Bomb(emy, bird))
            
            # ビーム発射（オート）
            # ターゲット候補：敵と爆弾の全グループ
            targets = pg.sprite.Group()
            targets.add(emys)
            targets.add(bombs)
            bird.shoot(beams)

            # --- 当たり判定処理 ---
            
            # ビーム vs 敵 (貫通処理対応)
            # groupcollideは使わず、貫通制御のためループで処理
            hits = pg.sprite.groupcollide(emys, beams, False, False)
            for emy, hit_beams in hits.items():
                for beam in hit_beams:
                    if emy not in beam.hit_enemies:
                        emy.hp -= beam.damage
                        beam.hit_enemies.add(emy)
                        
                        # 貫通力消費
                        if beam.pierce_count > 0:
                            beam.pierce_count -= 1
                        else:
                            beam.kill()
                            
                        if emy.hp <= 0:
                            exps.add(Explosion(emy, 100))
                            score.value += 10
                            emy.kill()
                            # 経験値ゲット & レベルアップ判定
                            if bird.gain_exp(30):
                                game_state = "SELECT"
                                # ランダムに3つのスキルを提示
                                all_skills = list(bird.skill.keys())
                                skill_choices = random.sample(all_skills, 3)
                            break # 同フレームで多重ヒット防止

            # ビーム vs 爆弾
            for bomb in pg.sprite.groupcollide(bombs, beams, False, False).keys():
                # 爆弾は貫通関係なく当たれば爆発
                exps.add(Explosion(bomb, 50))
                score.value += 1
                bomb.kill()
                if bird.gain_exp(10):
                    game_state = "SELECT"
                    skill_choices = random.sample(list(bird.skill.keys()), 3)

            # プレイヤー被弾判定（即ゲームオーバー）
            if len(pg.sprite.spritecollide(bird, bombs, True)) > 0 or \
               len(pg.sprite.spritecollide(bird, emys, True)) > 0:
                bird.change_img(8, screen)
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return

            # 更新と描画
            bird.update(key_lst, screen, targets)
            beams.update()
            beams.draw(screen)
            emys.update()
            emys.draw(screen)
            for emy in emys:
                emy.draw_hp(screen) # HPバー描画
            bombs.update()
            bombs.draw(screen)
            exps.update()
            exps.draw(screen)
            score.update(screen)
            
            # UI描画
            draw_exp_bar(screen, bird)

            tmr += 1

        # === スキル選択画面 ===
        elif game_state == "SELECT":
            # プレイ画面は止まったまま描画だけ残す
            bird.change_img(6, screen) # レベルアップ時は喜ぶ
            beams.draw(screen)
            emys.draw(screen)
            bombs.draw(screen)
            exps.draw(screen)
            score.update(screen)
            draw_exp_bar(screen, bird)
            
            # 選択画面オーバーレイ
            choice_rects = draw_skill_select(screen, skill_choices)

        pg.display.update()
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()