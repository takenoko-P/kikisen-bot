import pytesseract
from PIL import Image, ImageDraw, ImageFont
import random, os, datetime
import cv2
import numpy as np

# --- パス設定 ---
INPUT_IMAGE = "input/input_result.png"
P_LOGO_PATH = "assets/p_logo.png"
BACKGROUND_DIR = "assets/backgrounds"
OUTPUT_IMAGE = "output_result.png"

# --- OCR設定 ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # 適宜変更

# --- チーム名識別 ---
def extract_scores(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    
    # OCR 実行
    text = pytesseract.image_to_string(thresh, lang='eng+jpn')
    lines = text.split("\n")
    
    team_scores = {}
    for line in lines:
        if any(char.isdigit() for char in line):
            parts = line.strip().split()
            if len(parts) >= 2:
                name = parts[0]
                score = int(parts[-1]) if parts[-1].isdigit() else 0
                team = "BRZ" if "BRZ" in name else "Pizz."
                team_scores.setdefault(team, []).append((name, score))
    return team_scores

# --- ランダム背景読み込み ---
def get_random_background():
    bg_files = os.listdir(BACKGROUND_DIR)
    bg_path = os.path.join(BACKGROUND_DIR, random.choice(bg_files))
    return Image.open(bg_path).resize((1280, 720))

# --- 結果描画 ---
def draw_result(team_scores):
    bg = get_random_background().convert("RGBA")
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype("arial.ttf", 30)

    date_str = datetime.datetime.now().strftime("%d %b %Y")
    draw.text((40, 20), f"{date_str}", fill="black", font=font)

    y_offset = 100
    scores = {}
    for team, members in team_scores.items():
        team_total = sum(score for _, score in members)
        scores[team] = team_total
        draw.text((40, y_offset), f"{team} - {team_total}", fill="black", font=font)
        y_offset += 40
        for name, score in sorted(members, key=lambda x: -x[1]):
            draw.text((60, y_offset), f"{name:15} {score:3}", fill="black", font=font)
            y_offset += 30
        y_offset += 20

    diff = abs(scores.get("BRZ", 0) - scores.get("Pizz.", 0))
    draw.text((1000, 30), f"±{diff}", fill="red", font=font)

    # Pロゴ配置
    logo = Image.open(P_LOGO_PATH).convert("RGBA").resize((120, 120))
    bg.paste(logo, (bg.width - 130, bg.height - 130), logo)

    bg.save(OUTPUT_IMAGE)
    print(f"✅ 出力完了: {OUTPUT_IMAGE}")

# --- 実行 ---
if __name__ == "__main__":
    scores = extract_scores(INPUT_IMAGE)
    draw_result(scores)


