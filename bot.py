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

# 起動時イベント
@bot.event
async def on_ready():
    try:
        # 拡張機能を読み込む（←これを追加！）
        await bot.load_extension("nickname")

        synced = await bot.tree.sync()
        print(f"✅ {bot.user} がオンラインになりました（{len(synced)}件のスラッシュコマンドを同期）")
    except Exception as e:
        print(f"❌ スラッシュコマンド同期失敗: {e}")

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

    # 15分後に通知
    await asyncio.sleep(900)
    await interaction.channel.send("⏰ ボタンの有効時間が切れました。再度 `/menu` を実行してね！")

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

    reacted_users = set()

    def check(reaction, user):
        return (
            reaction.message.id == msg.id and
            str(reaction.emoji) == "☑" and
            not user.bot and
            user in members
        )

    timeout = 300  # 5分
    while timeout > 0:
        try:
            reaction_event = await bot.wait_for("reaction_add", timeout=1.0, check=check)
            reacted_users.add(reaction_event[1])
            if all(m in reacted_users for m in members):
                await interaction.channel.send(
                    f"{interaction.user.mention}\n✅ 全員の生存が確認できました！\n外交お願いします！"
                )
                return
            timeout -= 1.0
        except asyncio.TimeoutError:
            timeout = 0
            break

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


@bot.tree.command(name="sync", description="Botのスラッシュコマンドを同期します（P専用）")
async def sync_commands(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者専用です。", ephemeral=True)
        return

    await bot.tree.sync()
    await interaction.response.send_message("✅ スラッシュコマンドを同期しました！", ephemeral=True)

        

# Bot起動
bot.run(TOKEN)

