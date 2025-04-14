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

    @discord.app_commands.command(name="setnickname", description="ユーザーのニックネームを設定します（管理者専用）")
    @discord.app_commands.describe(member="ニックネームを登録したいユーザー", nickname="登録するニックネーム")
    async def setnickname(self, interaction: discord.Interaction, member: discord.Member, nickname: str):
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみ実行できます。", ephemeral=True)
            return

        nicknames = load_nicknames()
        nicknames[str(member.id)] = nickname
        save_nicknames(nicknames)

        await interaction.response.send_message(f"{member.mention} のニックネームを `{nickname}` に設定しました！")

async def setup(bot):
    await bot.add_cog(Nickname(bot))
