import discord
from discord.ext import commands
import json
import os

NICKNAME_FILE = "nicknames.json"

def load_nicknames():
    if not os.path.exists(NICKNAME_FILE):
        return {}
    with open(NICKNAME_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_nicknames(nicknames):
    with open(NICKNAME_FILE, "w", encoding="utf-8") as f:
        json.dump(nicknames, f, ensure_ascii=False, indent=2)

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="setnickname", description="ユーザーのニックネームを設定します（P専用）")
    @discord.app_commands.describe(user_id="ニックネームを登録したいユーザーのID", nickname="登録するニックネーム")
    async def setnickname(self, interaction: discord.Interaction, user_id: str, nickname: str):
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ このコマンドは管理者専用です。", ephemeral=True)
            return

        # IDが数値かチェック
        if not user_id.isdigit():
            await interaction.response.send_message("⚠️ ユーザーIDは数字で指定してください。", ephemeral=True)
            return

        nicknames = load_nicknames()
        nicknames[user_id] = nickname
        save_nicknames(nicknames)

        await interaction.response.send_message(f"📝 ユーザーID `{user_id}` にニックネーム `{nickname}` を設定しました！", ephemeral=True)

    @discord.app_commands.command(name="listnicknames", description="登録済みのニックネーム一覧を表示します")
    async def listnicknames(self, interaction: discord.Interaction):
        nicknames = load_nicknames()

        if not nicknames:
            await interaction.response.send_message("まだ登録されたニックネームはありません。", ephemeral=True)
            return

        lines = []
        for user_id, nickname in nicknames.items():
            mention = f"<@{user_id}>"
            lines.append(f"{mention}：`{nickname}`")

        text = "\n".join(lines)
        await interaction.response.send_message(f"📋 登録済みのニックネーム一覧：\n{text}")

async def setup(bot):
    await bot.add_cog(Nickname(bot))


