import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))
class EMP(pg.sprite.Sprite):
    """
    電磁パルス（EMP）に関するクラス
    """
    def __init__(self, enemies: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        """
        EMPエフェクトを生成し、敵機と爆弾を無効化する
        引数1 enemies: Enemyインスタンスのグループ
        引数2 bombs: Bombインスタンスのグループ
        引数3 screen: 画面Surface
        """
        super().__init__()
        # EMPの見た目
        self.image = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA) # SRCALPHAで透明度を扱う
        self.color = (255, 255, 0, 128) # 黄色で透明度50%
        pg.draw.rect(self.image, self.color, self.image.get_rect())
        self.rect = self.image.get_rect()
        
        # EMPの表示時間 (0.05秒)
        # main関数のFPS (50FPS) を考慮してフレーム数を設定
        self.life = 0.05 * 50 

        # 敵機と爆弾の無効化
        for enemy in enemies:
            enemy.interval = math.inf # 爆弾投下できなくなる
            enemy.image = pg.transform.laplacian(enemy.original_image) # 見た目をラプラシアンフィルタ
        
        for bomb in bombs:
            bomb.speed /= 2 # 動きが鈍くなる
            bomb.state = "inactive" # ぶつかったら起爆せずに消滅

    def update(self):
        """
        EMPエフェクトの表示時間を管理する
        """
        self.life -= 1
        if self.life < 0:
            self.kill()


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"  # こうかとんの状態（normal or hyper）
        self.hyper_life = 0    # 無敵状態の持続時間

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    # メソッドの定義を変更
    def update(self, key_lst: list[bool], screen: pg.Surface, score: "Score"):
        # 無敵状態発動のロジックを追加
        if key_lst[pg.K_RSHIFT] and score.value > 100 and self.state == "normal":
            score.value -= 100
            self.state = "hyper"
            self.hyper_life = 500

        # （移動処理は変更なし）
       
        
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        
        is_arrow_pressed = key_lst[pg.K_UP] or key_lst[pg.K_DOWN] or key_lst[pg.K_LEFT] or key_lst[pg.K_RIGHT]

        # 左SHIFTキーと矢印キーが同時に押されている場合にスピードブーストを適用
        if key_lst[pg.K_LSHIFT] and is_arrow_pressed:
            self.speed = 20 # スピードアップ
        else:
            self.speed = 10 # 通常速度に戻す

        self.rect.move_ip(self.speed * sum_mv[0], self.speed * sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed * sum_mv[0], -self.speed * sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)

        # 画像切り替えロジックを修正
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.imgs[self.dire])
            self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"
        else:
            self.image = self.imgs[self.dire]

        screen.blit(self.image, self.rect)



class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle0: float = 0):
        """
        ビーム画像Surfaceを生成する
        引数1 bird：ビームを放つこうかとん
        引数2 angle0：追加の回転角度（デフォルト0）
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        self.state = "active"

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        if self.state == "active": # active状態の場合のみ移動
            self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
            if check_bound(self.rect) != (True, True):
                self.kill()
       
        


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


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.original_image = self.image.copy()
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


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
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

class gravity(pg.sprite.Sprite):
    def __init__(self, life: int):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.fill((0, 0, 0))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()
        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()

class NeoBeam:
    """
    弾幕（複数方向ビーム）に関するクラス
    """
    def __init__(self, bird: Bird, num: int):
        """
        弾幕を生成する
        引数1 bird：ビームを放つこうかとん
        引数2 num：ビーム数
        """
        self.bird = bird
        self.num = num
        
    def gen_beams(self) -> list[Beam]:
        """
        指定されたビーム数分のBeamインスタンスを生成し、リストで返す
        -50°～+50°の角度範囲で等間隔に配置
        戻り値：Beamインスタンスのリスト
        """
        beams = []
        if self.num == 1:
            # ビーム数が1の場合は角度0
            beams.append(Beam(self.bird, 0))
        else:
            # ステップを計算：100度を(num-1)で割る
            step = 100 // (self.num - 1)
            for angle in range(-50, 51, step):
                beams.append(Beam(self.bird, angle))
        return beams



class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス
    """
    def __init__(self, bird: Bird, life: int):
        super().__init__()
        self.life = life

        Shield_width = 20
        Shield_height = bird.rect.height * 2
        self.image = pg.Surface((Shield_width, Shield_height), pg.SRCALPHA)

        pg.draw.rect(self.image,(0, 0, 255), (0, 0, Shield_width, Shield_height))

        vx, vy = bird.dire
        
        angle = math.degrees(math.atan2(-vy, vx))
        
        self.image = pg.transform.rotozoom(self.image, angle, 1.0)

        self.rect = self.image.get_rect()
        offset_x = bird.rect.width * vx
        offset_y = bird.rect.height * vy
        self.rect.centerx = bird.rect.centerx + offset_x
        self.rect.centery = bird.rect.centery + offset_y
        
    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.kill()

def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    Shields = pg.sprite.Group()

    gravity_fields = pg.sprite.Group()
    emps = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:  # 左Shift + スペースキーで弾幕発射
                    neo = NeoBeam(bird, 5)
                    for beam in neo.gen_beams():
                        beams.add(beam)
                else:  # スペースキーのみで通常ビーム発射
                    beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
                if score.value >= 200:
                    score.value -= 200
                    gravity_fields.add(gravity(400))
                beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_s:
                # 防御壁発動条件：スコア50以上、かつ防御壁が存在しない
                if score.value >= 50 and len(Shields) == 0:
                    Shields.add(Shield(bird, 400))  # 400フレーム持続
                    score.value -= 50  # スコア50消費
            if event.type == pg.KEYDOWN and event.key == pg.K_e: # 'e' キーの押下を検出
                if score.value >= 20: # スコアが20より大かチェック
                    score.value -= 20 # スコアを20消費
                    emps.add(EMP(emys, bombs, screen)) # EMPインスタンスを生成し、グループに追加
        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            if bomb.state == "active":
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1  # 1点アップ

        # このforループ全体を差し替える
        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                score.value += 1  # 1点アップ
            else:
                if bomb.state == "active":
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    pg.display.update( )
                    time.sleep(2)
                    return

        pg.sprite.groupcollide(bombs, Shields, True, False)
        bird.update(key_lst, screen, score)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        emps.update()
        emps.draw(screen)
        exps.update()
        exps.draw(screen)
        Shields.update()
        Shields.draw(screen)
        score.update(screen)
        gravity_fields.update()
        for grav in gravity_fields:
            for bomb in pg.sprite.spritecollide(grav, bombs, True):
                exps.add(Explosion(bomb, 30))
        gravity_fields.draw(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
