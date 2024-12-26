import pygame
import sys
import os
import time
import json
from pygame.locals import *

# 初期化
pygame.init()

# 画面サイズ
CELL_SIZE = 40
MAZE_WIDTH = 10
MAZE_HEIGHT = 10
STATUS_HEIGHT = 50
BUTTON_HEIGHT = 30
BUTTON_WIDTH = 100
BUTTON_MARGIN = 10
SCREEN_WIDTH = CELL_SIZE * MAZE_WIDTH
SCREEN_HEIGHT = CELL_SIZE * MAZE_HEIGHT + STATUS_HEIGHT

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("動的迷路ゲーム")

# 色定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
YELLOW = (255, 255, 0)  # 特殊マスのメッセージ用

# 画像フォルダ
ImageFolder = "Images/"

# 画像の読み込み（画像がない場合は色で代用）
def load_image(path, fallback_color):
    try:
        image = pygame.image.load(os.path.join(ImageFolder, path)).convert_alpha()
        image = pygame.transform.scale(image, (CELL_SIZE, CELL_SIZE))
    except:
        image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        image.fill(fallback_color)
    return image

# 画像の読み込み
player_img = load_image('player.png', BLUE)
wall_img = load_image('wall.png', BLACK)
goal_img = load_image('goal.png', GREEN)
floor_img = load_image('floor.png', WHITE)
plus_img = load_image('plus.png', (255, 215, 0))   # 金色
minus_img = load_image('minus.png', (128, 128, 128))  # グレー

# フォント設定（日本語対応）
def get_japanese_font(size):
    try:
        # 日本語フォントのパスを指定（システムにインストールされている日本語フォントを使用）
        font_path = pygame.font.match_font('msgothic')  # Windowsの場合 "msgothic"
        return pygame.font.Font(font_path, size)
    except:
        # フォールバックフォント
        return pygame.font.SysFont(None, size)

font = get_japanese_font(24)

# ステージの保存ファイル
SAVE_FILE = "save.json"

# ステージのロードと保存
def load_save():
    if not os.path.exists(SAVE_FILE):
        return {"unlocked_stage": 1}
    with open(SAVE_FILE, "r", encoding='utf-8') as f:
        return json.load(f)

def save_game(data):
    with open(SAVE_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ステージと世界の読み込み
def load_stages(worlds_folder="Worlds"):
    stages = []
    if not os.path.exists(worlds_folder):
        print(f"{worlds_folder}フォルダが存在しません。")
        pygame.quit()
        sys.exit()
    stage_names = sorted([d for d in os.listdir(worlds_folder) if os.path.isdir(os.path.join(worlds_folder, d))])
    for stage_name in stage_names:
        stage_path = os.path.join(worlds_folder, stage_name)
        world_files = sorted([f for f in os.listdir(stage_path) if f.startswith('world') and f.endswith('.txt')])
        worlds = []
        for world_file in world_files:
            world_path = os.path.join(stage_path, world_file)
            with open(world_path, "r", encoding='utf-8') as wf:
                lines = wf.readlines()
                if not lines:
                    print(f"{world_path} は空です。")
                    pygame.quit()
                    sys.exit()
                try:
                    change_interval = int(lines[0].strip())
                except ValueError:
                    print(f"{world_path} の一行目は整数でなければなりません。")
                    pygame.quit()
                    sys.exit()
                maze = [list(line.strip()) for line in lines[1:]]
                # Pad maze to MAZE_HEIGHT and MAZE_WIDTH if necessary
                while len(maze) < MAZE_HEIGHT:
                    maze.append(['1'] * MAZE_WIDTH)
                for row in maze:
                    while len(row) < MAZE_WIDTH:
                        row.append('1')
                worlds.append({"maze": maze, "change_interval": change_interval})
        stages.append({"name": stage_name, "worlds": worlds})
    return stages

# 迷路の描画
def draw_maze(screen, maze):
    for y in range(MAZE_HEIGHT):
        for x in range(MAZE_WIDTH):
            if y >= len(maze) or x >= len(maze[y]):
                continue  # 範囲外のセルは無視
            cell = maze[y][x]
            pos = (x * CELL_SIZE, y * CELL_SIZE)
            if cell == '1':
                screen.blit(wall_img, pos)
            elif cell == '0' or cell == 'S':
                screen.blit(floor_img, pos)
            elif cell == 'G':
                screen.blit(goal_img, pos)
            elif cell == '+':
                screen.blit(plus_img, pos)
            elif cell == '-':
                screen.blit(minus_img, pos)
            else:
                screen.blit(floor_img, pos)  # 未定義のセルは床として描画

# スタート位置の検索
def find_start(maze):
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            if cell == 'S':
                return x, y
    return None

# リセット関数
def reset_game():
    global current_stage_index, current_world_index, move_count, player_x, player_y, undo_stack, redo_stack, game_clear, change_interval, is_stuck, special_message, special_message_timer
    current_stage_index = 0
    current_world_index = 0
    current_stage = stages[current_stage_index]
    current_world = current_stage["worlds"][current_world_index]
    start_pos = find_start(current_world["maze"])
    if start_pos is None:
        print(f"{current_stage['name']}のworld{current_world_index +1}.txtにスタート位置 'S' が見つかりません。")
        pygame.quit()
        sys.exit()
    player_x, player_y = start_pos
    move_count = 0
    undo_stack = []
    redo_stack = []
    game_clear = False
    change_interval = current_world["change_interval"]
    is_stuck = False
    special_message = ""
    special_message_timer = 0

# UndoとRedoのスタック
undo_stack = []
redo_stack = []

# ステージ選択画面の状態
stage_selection = True

# ゲームの状態
game_running = False

# ゲームクリアフラグ
game_clear = False

# 移動アニメーション用
is_moving = False
move_start_time = 0
move_duration = 0.3  # 0.3秒
start_pos_anim = (0, 0)
end_pos_anim = (0, 0)
current_pos_anim = (0, 0)
display_x = 0
display_y = 0

# 世界の変化アニメーション用
is_transitioning = False
transition_start_time = 0
transition_duration = 0.3  # 0.3秒
current_maze_surface = None
next_maze_surface = None
alpha = 0

# リセットボタンの設定（ゲーム中）
def create_reset_button():
    button_font = get_japanese_font(24)
    button_text = "リセット"
    button_color = GRAY
    # リセットボタンを画面下部に配置
    button_rect = pygame.Rect(SCREEN_WIDTH - BUTTON_WIDTH - BUTTON_MARGIN, SCREEN_HEIGHT - BUTTON_HEIGHT - BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT)
    return button_text, button_color, button_rect

button_text, button_color, button_rect = create_reset_button()

# ステージクリア時のステージアンロック
def unlock_next_stage():
    global unlocked_stage
    if current_stage_index + 1 > unlocked_stage and current_stage_index + 1 <= len(stages):
        unlocked_stage += 1
        save_game({"unlocked_stage": unlocked_stage})
        print(f"ステージ {current_stage['name']} をクリアしました！次のステージが解放されました。")

# 特殊マス到達時のメッセージ
special_message = ""
special_message_timer = 0  # メッセージの表示時間（秒）

# ゲーム状態を保存
def save_game_state():
    return {
        "player_x": player_x,
        "player_y": player_y,
        "current_stage_index": current_stage_index,
        "current_world_index": current_world_index,
        "move_count": move_count,
        "change_interval": change_interval,
        "is_stuck": is_stuck
    }

# ゲーム状態を復元
def load_game_state(state):
    global player_x, player_y, current_stage_index, current_world_index, move_count, change_interval, is_stuck, current_stage, current_world
    player_x = state.get("player_x", player_x)
    player_y = state.get("player_y", player_y)
    current_stage_index = state.get("current_stage_index", current_stage_index)
    current_world_index = state.get("current_world_index", current_world_index)
    move_count = state.get("move_count", move_count)
    change_interval = state.get("change_interval", change_interval)
    is_stuck = state.get("is_stuck", is_stuck)
    
    # 現在のステージと世界を更新
    if 0 <= current_stage_index < len(stages):
        current_stage = stages[current_stage_index]
        if 0 <= current_world_index < len(current_stage["worlds"]):
            current_world = current_stage["worlds"][current_world_index]
        else:
            print(f"無効な世界インデックス: {current_world_index}")
            pygame.quit()
            sys.exit()
    else:
        print(f"無効なステージインデックス: {current_stage_index}")
        pygame.quit()
        sys.exit()

# ロード
stages = load_stages()
save_data = load_save()
unlocked_stage = save_data.get("unlocked_stage", 1)

# ステージをロードして初期化
current_stage_index = 0
current_world_index = 0
current_stage = stages[current_stage_index]
current_world = current_stage["worlds"][current_world_index]
start_pos = find_start(current_world["maze"])
if start_pos is None:
    print(f"{current_stage['name']}のworld{current_world_index +1}.txtにスタート位置 'S' が見つかりません。")
    pygame.quit()
    sys.exit()
player_x, player_y = start_pos
move_count = 0

# change_intervalの定義
change_interval = current_world["change_interval"]

# is_stuckの定義
is_stuck = False

# メインループ
clock = pygame.time.Clock()

while True:
    dt = clock.tick(60) / 1000  # 秒単位
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game({"unlocked_stage": unlocked_stage})
            pygame.quit()
            sys.exit()

        if stage_selection:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                for idx, stage in enumerate(stages):
                    stage_num = idx + 1
                    if stage_num > unlocked_stage:
                        continue  # ロックされているステージは無視
                    stage_rect = pygame.Rect(50, 80 + idx * 60, SCREEN_WIDTH - 100, 50)
                    if stage_rect.collidepoint(mouse_pos):
                        # ステージを選択
                        current_stage_index = idx
                        current_stage = stages[current_stage_index]
                        current_world_index = 0
                        current_world = current_stage["worlds"][current_world_index]
                        start_pos = find_start(current_world["maze"])
                        if start_pos is None:
                            print(f"{current_stage['name']}のworld{current_world_index +1}.txtにスタート位置 'S' が見つかりません。")
                            pygame.quit()
                            sys.exit()
                        player_x, player_y = start_pos
                        move_count = 0
                        undo_stack = []
                        redo_stack = []
                        game_clear = False
                        stage_selection = False
                        game_running = True
                        change_interval = current_world["change_interval"]
                        is_stuck = False
                        special_message = ""
                        special_message_timer = 0
                        break

            # ステージ選択中は他のイベントを無視
            continue

        elif game_running:
            if not game_clear and not is_moving and not is_transitioning:
                if event.type == pygame.KEYDOWN:
                    dx, dy = 0, 0
                    if event.key == pygame.K_w:
                        dy = -1
                    elif event.key == pygame.K_s:
                        dy = 1
                    elif event.key == pygame.K_a:
                        dx = -1
                    elif event.key == pygame.K_d:
                        dx = 1
                    elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        # Ctrl+ZでUndo
                        if undo_stack:
                            last_state = undo_stack.pop()
                            redo_stack.append(save_game_state())
                            load_game_state(last_state)
                            print(f"Undo: ステージ {stages[current_stage_index]['name']}, 世界 {current_world_index +1}, プレイヤー位置 ({player_x}, {player_y})")
                    elif event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                        # Ctrl+YでRedo
                        if redo_stack:
                            next_state = redo_stack.pop()
                            undo_stack.append(save_game_state())
                            load_game_state(next_state)
                            print(f"Redo: ステージ {stages[current_stage_index]['name']}, 世界 {current_world_index +1}, プレイヤー位置 ({player_x}, {player_y})")

                    if dx != 0 or dy != 0:
                        if is_stuck:
                            print("プレイヤーが埋まっているため、移動できません。UndoまたはRedoを使用してください。")
                            continue  # 移動をブロック
                        new_x = player_x + dx
                        new_y = player_y + dy

                        # 境界チェック
                        if new_y < 0 or new_y >= MAZE_HEIGHT or new_x < 0 or new_x >= MAZE_WIDTH:
                            print("その方向には進めません。")
                        else:
                            cell = current_world["maze"][new_y][new_x]
                            if cell != '1':
                                # スタート位置の制約（ステージ1のみ）
                                if current_stage_index != 0 and cell == 'S':
                                    print("スタート位置に戻ることはできません。")
                                else:
                                    # 移動履歴を保存
                                    undo_stack.append(save_game_state())
                                    redo_stack.clear()

                                    # 移動アニメーション開始
                                    is_moving = True
                                    move_start_time = time.time()
                                    start_pos_anim = (player_x, player_y)
                                    end_pos_anim = (new_x, new_y)
                                    print(f"移動開始: ステージ {stages[current_stage_index]['name']}, 世界 {current_world_index +1}, プレイヤー位置 ({player_x}, {player_y}) -> ({new_x}, {new_y})")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_game({"unlocked_stage": unlocked_stage})
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if button_rect.collidepoint(mouse_pos):
                    reset_game()
                    game_running = True  # ゲームを再開

    # アニメーションと描画処理
    if stage_selection:
        # ステージ選択画面の描画
        screen.fill(BLACK)
        title_text = font.render("ステージ選択", True, WHITE)
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 20))

        # 各ステージボタンの描画
        for idx, stage in enumerate(stages):
            stage_num = idx + 1
            stage_name = stage["name"]
            if stage_num <= unlocked_stage:
                button_color_stage = GREEN
                clickable = True
            else:
                button_color_stage = GRAY
                clickable = False

            stage_rect_stage = pygame.Rect(50, 80 + idx * 60, SCREEN_WIDTH - 100, 50)
            pygame.draw.rect(screen, button_color_stage, stage_rect_stage)
            stage_text = f"{stage_name} {'(解放済み)' if stage_num <= unlocked_stage else '(ロック中)'}"
            stage_text_surface = font.render(stage_text, True, BLACK)
            text_rect = stage_text_surface.get_rect(center=stage_rect_stage.center)
            screen.blit(stage_text_surface, text_rect)

        pygame.display.flip()

    elif game_running:
        # 移動アニメーションの処理
        if is_moving:
            elapsed = time.time() - move_start_time
            t = min(elapsed / move_duration, 1)  # 0 <= t <= 1
            interp_x = start_pos_anim[0] + (end_pos_anim[0] - start_pos_anim[0]) * t
            interp_y = start_pos_anim[1] + (end_pos_anim[1] - start_pos_anim[1]) * t

            # 更新された位置
            display_x = interp_x
            display_y = interp_y

            if t >= 1:
                # 移動完了
                is_moving = False
                player_x, player_y = end_pos_anim
                move_count += 1
                print(f"移動完了: ステージ {stages[current_stage_index]['name']}, 世界 {current_world_index +1}, プレイヤー位置 ({player_x}, {player_y})")

                # ゴールチェック
                current_maze = current_world["maze"]
                cell = current_maze[player_y][player_x]
                if cell == 'G':
                    game_clear = True
                    print("ゴールに到達しました！")

                # 新しいマスのチェック
                if cell == '+':
                    change_interval += 1
                    special_message = "+マスに到達！世界変化までのカウントが1増加しました。"
                    special_message_timer = 2  # 2秒間表示
                    print("+マスに到達しました！世界変化までのカウントが1増加しました。")
                elif cell == '-':
                    if change_interval > 1:
                        change_interval -= 1
                        special_message = "−マスに到達！世界変化までのカウントが1減少しました。"
                        special_message_timer = 2  # 2秒間表示
                        print("−マスに到達しました！世界変化までのカウントが1減少しました。")
                    else:
                        special_message = "−マスに到達しましたが、カウントはこれ以上減少できません。"
                        special_message_timer = 2  # 2秒間表示
                        print("−マスに到達しましたが、カウントはこれ以上減少できません。")

                # 世界の変化チェック
                if move_count >= change_interval and not game_clear:
                    move_count = 0
                    # 世界の変化を開始
                    is_transitioning = True
                    transition_start_time = time.time()

                    # 現在の迷路を描画したSurfaceを作成
                    current_maze_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - STATUS_HEIGHT))
                    draw_maze(current_maze_surface, current_maze)
                    current_maze_surface.set_alpha(255)

                    # 次の世界を決定
                    current_world_index = (current_world_index + 1) % len(current_stage["worlds"])
                    current_world = current_stage["worlds"][current_world_index]
                    change_interval = current_world["change_interval"]

                    # 新しい迷路を描画したSurfaceを作成
                    next_maze_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT - STATUS_HEIGHT))
                    draw_maze(next_maze_surface, current_world["maze"])
                    next_maze_surface.set_alpha(0)

                    print(f"世界が変化しました。ステージ {stages[current_stage_index]['name']}, 世界 {current_world_index +1}")

                    # 新しい世界でのプレイヤー位置チェック
                    new_cell = current_world["maze"][player_y][player_x]
                    if new_cell == '1':
                        is_stuck = True
                        print("変化後、プレイヤーが壁に埋まってしまいました。移動が制限されます。")
                    else:
                        is_stuck = False

        elif is_transitioning:
            elapsed = time.time() - transition_start_time
            t = min(elapsed / transition_duration, 1)  # 0 <= t <= 1

            # フェードアウト
            current_maze_surface.set_alpha(max(255 - int(255 * t), 0))
            # フェードイン
            next_maze_surface.set_alpha(min(int(255 * t), 255))

            if t >= 1:
                is_transitioning = False
                current_maze_surface = None
                next_maze_surface = None
                print(f"世界の変化が完了しました。ステージ {stages[current_stage_index]['name']}, 世界 {current_world_index +1}")

        # 画面描画
        if not is_transitioning and game_running:
            screen.fill(BLACK)

            current_maze = current_world["maze"]
            draw_maze(screen, current_maze)

            # プレイヤー描画（アニメーション中は補間位置）
            if is_moving:
                screen.blit(player_img, (display_x * CELL_SIZE, display_y * CELL_SIZE))
            else:
                screen.blit(player_img, (player_x * CELL_SIZE, player_y * CELL_SIZE))

            # ステータス表示（画面上部）
            status_text = f"{current_stage['name']}|世界{current_world_index +1}|次の変化まで:{change_interval - move_count}回"
            text_surface = font.render(status_text, True, BLACK)
            screen.blit(text_surface, (10, BUTTON_MARGIN))

            # リセットボタン描画（画面下部）
            pygame.draw.rect(screen, button_color, button_rect)
            button_text_surface = font.render(button_text, True, BLACK)
            text_rect = button_text_surface.get_rect(center=button_rect.center)
            screen.blit(button_text_surface, text_rect)

            # ゲームクリアメッセージ
            if game_clear:
                clear_text = "クリア！おめでとうございます！"
                clear_surface = font.render(clear_text, True, GREEN)
                screen.blit(clear_surface, (SCREEN_WIDTH // 2 - clear_surface.get_width() // 2, SCREEN_HEIGHT // 2 - clear_surface.get_height() // 2))
                unlock_next_stage()

            # 特殊マス到達メッセージの描画
            if special_message:
                special_surface = font.render(special_message, True, YELLOW)
                screen.blit(special_surface, (SCREEN_WIDTH // 2 - special_surface.get_width() // 2, SCREEN_HEIGHT - STATUS_HEIGHT + 10))

        elif is_transitioning and game_running:
            # アニメーション中の描画
            if current_maze_surface and next_maze_surface:
                screen.blit(current_maze_surface, (0, 0))
                screen.blit(next_maze_surface, (0, 0))

            # プレイヤー描画（アニメーション中は補間位置）
            screen.blit(player_img, (player_x * CELL_SIZE, player_y * CELL_SIZE))

            # ステータス表示（画面上部）
            status_text = f"{current_stage['name']}|世界{current_world_index +1}|次の変化まで:{change_interval - move_count}回"
            text_surface = font.render(status_text, True, BLACK)
            screen.blit(text_surface, (10, BUTTON_MARGIN))

            # リセットボタン描画（画面下部）
            pygame.draw.rect(screen, button_color, button_rect)
            button_text_surface = font.render(button_text, True, BLACK)
            text_rect = button_text_surface.get_rect(center=button_rect.center)
            screen.blit(button_text_surface, text_rect)

        # メッセージタイマーの更新
        if special_message:
            special_message_timer -= dt
            if special_message_timer <= 0:
                special_message = ""

        pygame.display.flip()

    # フレームレート
    pygame.time.Clock().tick(60)
