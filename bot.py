import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from gtts import gTTS
import os
import asyncio

# 環境変数からトークン取得
TOKEN = os.environ.get("DISCORD_TOKEN")

# インテント設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Botインスタンス生成
bot = commands.Bot(command_prefix="!", intents=intents)

# 定型文リスト
PHRASES = {
    "⚡": "サンダーひきました",
    "🚘": "とげなげて",
    "⭐": "むてきあるよ",
    "💀": "てきサンダーみえた",
}

# VCに誰もいなくなったら自動切断
@bot.event
async def on_voice_state_update(member, before, after):
    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
    if not voice_client or not voice_client.is_connected():
        return
    if before.channel and before.channel == voice_client.channel:
        non_bot_members = [m for m in before.channel.members if not m.bot]
        if len(non_bot_members) == 0:
            await voice_client.disconnect()
            print("👋 誰もいなくなったのでVCから切断しました")

# スラッシュコマンド

@bot.tree.command(name="join", description="ボイスチャンネルに参加します")
@app_commands.describe()
async def join_slash(interaction: discord.Interaction):
    if interaction.user.voice:
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("✅ ボイスチャンネルに参加しました！")
    else:
        await interaction.response.send_message("❌ あなたはボイスチャンネルにいません。")

@bot.tree.command(name="bye", description="ボイスチャンネルから退出します")
@app_commands.describe()
async def bye_slash(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 VCから切断しました")
    else:
        await interaction.response.send_message("❌ BotはVCに入っていません。")

@bot.tree.command(name="menu", description="セリフボタンを表示します")
@app_commands.describe()
async def menu_slash(interaction: discord.Interaction):
    view = PhraseMenuView(timeout=900)  # 15分有効
    await interaction.response.send_message(
        "🗣️ どのセリフを喋らせる？\n⚠️ ボタンが反応しなくなったら、もう一度 `/menu` を使ってね！",
        view=view
    )

    # 15分後に通知（別タスクで実行）
    async def notify_timeout():
        await asyncio.sleep(900)
        await interaction.channel.send("⏰ ボタンの有効時間が切れました。再度 `/menu` を実行してね！")

    asyncio.create_task(notify_timeout())


# ボタン関連

class PhraseMenuView(View):
    def __init__(self, timeout=900):
        super().__init__(timeout=timeout)
        for label, phrase in PHRASES.items():
            self.add_item(PhraseButton(label, phrase))
        self.add_item(RefreshButton())

class PhraseButton(Button):
    def __init__(self, label, phrase):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.phrase = phrase

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.guild.voice_client:
            await interaction.followup.send("❌ BotはまだVCにいないよ！先に `/join` してね。", ephemeral=True)
            return

        tts = gTTS(text=self.phrase, lang="ja")
        filename = "phrase.mp3"
        tts.save(filename)

        vc = interaction.guild.voice_client
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=filename))

        await interaction.followup.send(f"🗣️「{self.phrase}」を読み上げます！", ephemeral=True)

        while vc.is_playing():
            await asyncio.sleep(0.5)

        os.remove(filename)

class RefreshButton(Button):
    def __init__(self):
        super().__init__(label="🆕 最新に表示", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = PhraseMenuView()
        await interaction.response.send_message("🗣️ どのセリフを喋らせる？（再表示）", view=view, ephemeral=True)

# 生存確認コマンド

@bot.tree.command(name="seizon", description="指定したロールのメンバーの生存確認をします")
@app_commands.describe(role="確認するロール")
async def seizon(interaction: discord.Interaction, role: discord.Role):
    guild = interaction.guild
    await interaction.response.defer(thinking=True)

    try:
        members = [
            m async for m in guild.fetch_members(limit=None)
            if role in m.roles and not m.bot
        ]
    except discord.ClientException:
        await interaction.followup.send("⚠ メンバーの取得に失敗しました。BotのIntents設定や権限を確認してください。")
        return

    if not members:
        await interaction.followup.send("そのロールにはBot以外のメンバーがいません。")
        return

    mentions = " ".join(m.mention for m in members)
    msg = await interaction.followup.send(
        f"{role.mention} のメンバーの生存確認です。\n{mentions}"
    )
    await msg.add_reaction("☑")

    await asyncio.sleep(1)  # ← ここでBotの☑リアクション完了を待つ

    reacted_users = set()

    def check(reaction, user):
        return (
            reaction.message.id == msg.id and
            str(reaction.emoji) == "☑" and
            not user.bot and
            user in members and
            user not in reacted_users
        )

    timeout = 300  # 秒（5分）
    elapsed = 0
    interval = 5  # 5秒ごとに反応をチェック

    while elapsed < timeout:
        try:
            reaction_event = await bot.wait_for("reaction_add", timeout=interval, check=check)
            reacted_users.add(reaction_event[1])
            if all(m in reacted_users for m in members):
                await interaction.channel.send(
                    f"{interaction.user.mention}\n✅ 全員の生存が確認できました！\n外交お願いします！"
                )
                return
        except asyncio.TimeoutError:
            elapsed += interval

    not_responded = [m for m in members if m not in reacted_users]
    if not not_responded:
        await interaction.channel.send(
            f"{interaction.user.mention}\n✅ 全員の生存が確認できました！\n外交お願いします！"
        )
    else:
        not_responded_mentions = " ".join(m.mention for m in not_responded)
        await interaction.channel.send(
            f"{interaction.user.mention}\n⚠ 以下のメンバーが未反応です！\n{not_responded_mentions}"
        )


# 起動時イベント
@bot.event
async def on_ready():
    print(f"✅ {bot.user} がオンラインになりました")
    try:
        synced = await bot.tree.sync()
        print(f"✅ スラッシュコマンドを {len(synced)} 件同期しました")
    except Exception as e:
        print(f"❌ スラッシュコマンドの同期に失敗しました: {e}")



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
        

# Bot起動
bot.run(TOKEN)

