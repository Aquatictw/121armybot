
import discord
from discord.ui import View, Button

class BattleConfirmation(View):
    def __init__(self, challenger, challenged):
        super().__init__()
        self.challenger = challenger
        self.challenged = challenged
        self.battle_accepted = False

    @discord.ui.button(label="接受", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message("這不是給你的按鈕。", ephemeral=True)
            return

        self.battle_accepted = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="拒絕", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message("阿你是在按三小。", ephemeral=True)
            return

        self.stop()
        await interaction.response.send_message(f"{self.challenged.mention} 拒絕了 {self.challenger.mention} 的挑戰。")

class BattleView(View):
    def __init__(self, player1, player2):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.health1 = 10
        self.health2 = 10
        self.turn = player1

    def create_embed(self):
        health_bar1 = "🟥" * self.health1 + "⬛" * (10 - self.health1)
        health_bar2 = "🟥" * self.health2 + "⬛" * (10 - self.health2)
        
        embed = discord.Embed(title=f"⚔️戰鬥開始⚔️ - 輪到{self.turn.display_name}")
        embed.add_field(name=f"{self.player1.display_name}", value=health_bar1, inline=False)
        embed.add_field(name=f"{self.player2.display_name}", value=health_bar2, inline=False)
        embed.set_footer(text=f"輪到 {self.turn.display_name} 的回合")
        return embed

    @discord.ui.button(label="攻擊", style=discord.ButtonStyle.primary)
    async def attack(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn:
            await interaction.response.send_message("阿你是在按三小。", ephemeral=True)
            return

        if self.turn == self.player1:
            self.health2 -= 1
            self.turn = self.player2
        else:
            self.health1 -= 1
            self.turn = self.player1
        
        if self.health1 == 0:
            self.stop()
            await interaction.response.edit_message(embed=self.create_embed(), view=None)
            await interaction.followup.send(f"{self.player2.mention} 獲勝！")
            return
        
        if self.health2 == 0:
            self.stop()
            await interaction.response.edit_message(embed=self.create_embed(), view=None)
            await interaction.followup.send(f"{self.player1.mention} 獲勝！")
            return

        await interaction.response.edit_message(embed=self.create_embed())
