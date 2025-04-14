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

bot = commands.Bot(command_prefix="!", intents=intents)

# 定型文リスト
PHRASES = {
    "⚡": "サンダーひきました",
    "🚘": "とげなげて",
    "⭐": "むてきあるよ",
    "💀": "てきサンダーみえた",
}

@bot.event
async def on_ready():
    print(f"✅ ログイン完了：{bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 スラッシュコマンド {len(synced)} 件同期済み")
    except Exception as e:
        print(f"❌ スラッシュコマンド同期失敗: {e}")

# ✅ VCに誰もいなくなったら自動切断
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

# 🎙️ スラッシュコマンド
@bot.tree.command(name="join", description="ボイスチャンネルに参加します")
async def join_slash(interaction: discord.Interaction):
    if interaction.user.voice:
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("✅ ボイスチャンネルに参加しました！")
    else:
        await interaction.response.send_message("❌ あなたはボイスチャンネルにいません。")

@bot.tree.command(name="bye", description="ボイスチャンネルから退出します")
async def bye_slash(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 VCから切断しました")
    else:
        await interaction.response.send_message("❌ BotはVCに入っていません。")

@bot.tree.command(name="menu", description="セリフボタンを表示します")
async def menu_slash(interaction: discord.Interaction):
    view = PhraseMenuView(timeout=900)  # 15分間ボタン有効
    await interaction.response.send_message(
        "🗣️ どのセリフを喋らせる？\n⚠️ ボタンが反応しなくなったら、もう一度 `/menu` を使ってね！",
        view=view
    )

    # 15分後に通知を送信
    await asyncio.sleep(900)
    await interaction.channel.send("⏰ ボタンの有効時間が切れました。再度 `/menu` を実行してね！")


# 🔘 ボタン関連
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
        vc.play(discord.FFmpegPCMAudio(filename))

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

# 🚀 起動
bot.run(TOKEN)
