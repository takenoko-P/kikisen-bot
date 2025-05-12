import os
import random
from PIL import Image, ImageDraw, ImageFont

# 使用する背景画像のフォルダ
BG_FOLDER = r"B:\写真\集計用"

LOGO_PATH = "pロゴ.png"
FONT_PATH = "fonts/NotoSansJP-Regular.otf"
OUTPUT_PATH = "result_image.png"

# メイン関数
def generate_result_image(
    our_team_name: str,
    opponent_team_name: str,
    our_members: dict,
    opponent_members: dict,
):
    # 合計点
    our_score = sum(our_members.values())
    opp_score = sum(opponent_members.values())
    diff = our_score - opp_score
    result_text = f"{'勝利！' if diff > 0 else '敗北…'} {abs(diff)}点差"

    # 指定したフォルダから画像ファイルをランダムに選ぶ
    bg_files = [f for f in os.listdir(BG_FOLDER) if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
    if not bg_files:
        print("フォルダ内に画像が見つかりませんでした。")
        return
    
    bg_file = random.choice(bg_files)
    bg = Image.open(os.path.join(BG_FOLDER, bg_file)).convert("RGBA")
    draw = ImageDraw.Draw(bg)
    W, H = bg.size

    # フォント設定
    font_large = ImageFont.truetype(FONT_PATH, size=64)
    font_med = ImageFont.truetype(FONT_PATH, size=36)
    font_small = ImageFont.truetype(FONT_PATH, size=28)

    # 結果テキストを中央上部に描画
    draw.text((W // 2, 50), result_text, font=font_large, anchor="mm", fill="white")

    # チームスコアとメンバー
    y_start = 150
    spacing = 45

    def draw_team(name, members, x, anchor):
        draw.text((x, y_start), f"[{name}]", font=font_med, fill="white", anchor=anchor)
        for i, (member, score) in enumerate(members.items()):
            draw.text((x, y_start + spacing * (i + 1)), f"{member} {score}", font=font_small, fill="white", anchor=anchor)

    draw_team(our_team_name, our_members, x=W * 0.25, anchor="lm")
    draw_team(opponent_team_name, opponent_members, x=W * 0.75, anchor="rm")

    # スコア合計
    draw.text((W // 2, H - 200), f"{our_team_name}: {our_score}   {opponent_team_name}: {opp_score}",
              font=font_med, fill="white", anchor="mm")

    # チームロゴを右下に合成
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((100, 100))
    bg.paste(logo, (W - 110, H - 110), logo)

    # 保存
    bg.save(OUTPUT_PATH)
    print(f"✅ 保存完了: {OUTPUT_PATH}")

