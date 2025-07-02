import discord
from random import uniform 
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
        self.health1 = 114
        self.round = 1
        self.health2 = 114
        self.turn = player1

    def create_embed(self):
        health_bar1 = "🟥" * int(self.health1) + "⬛" * (10 - int(self.health1))
        health_bar2 = "🟥" * int(self.health2) + "⬛" * (10 - int(self.health2))
        
        embed = discord.Embed(title=f"🛡️ 回合 {self.round} -  輪到{self.turn.display_name}",
                      url="https://laxd.com",
                      colour=0x000000)
        embed.set_author(name=f"Homo戰鬥開始🗡️ {self.player1.display_name} v.s. {self.player2.display_name}")
        embed.add_field(name=f"{self.player1.display_name}", value=health_bar1, inline=True)
        embed.add_field(name=f"{self.player2.display_name}", value=health_bar2, inline=True)

        embed.add_field(name="📊 狀態",
                value=f"{self.player1.display_name} {round(self.health1, 1)}/114 ⚔️ {self.player2.display_name} {round(self.health2, 1)}/114",
                inline=False)

        embed.set_image(url="https://media.discordapp.net/attachments/1043107075758231625/1385835502665728060/2025-06-21_12.15.25.png?ex=686603e3&is=6864b263&hm=bf3fb754652cb34e5e1ab7d4de4e86c92c42e41c63127a92f20b3dc6e3bbca17&=&format=webp&quality=lossless&width=926&height=505")

        embed.set_footer(
                 text=f"{self.player1.display_name}把他的雞巴，放進了{self.player2.display_name}的皮炎裡面",
                 icon_url="https://wiki.yjsnpi.nu/w/images/b/b7/%E3%83%89%E3%83%A4%E9%A1%94%E5%85%88%E8%BC%A9.jpg")

        return embed

    @discord.ui.button(label="攻擊", style=discord.ButtonStyle.primary)
    async def attack(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn:
            await interaction.response.send_message("阿你是在按三小。", ephemeral=True)
            return

        random_float = uniform(0.8, 2.5)
        damage = round(random_float, 1)

        if self.turn == self.player1:
            self.health2 -= damage
            self.turn = self.player2
        else:
            self.health1 -= damage 
            self.turn = self.player1
        
        if self.health1 <= 0:
            self.stop()
            await interaction.response.edit_message(embed=self.create_embed(), view=None)
            await interaction.followup.send(f"{self.player2.mention} 獲勝！")
            return
        
        if self.health2 <= 0:
            self.stop()
            await interaction.response.edit_message(embed=self.create_embed(), view=None)
            await interaction.followup.send(f"{self.player1.mention} 獲勝！")
            return

        self.round += 1
        await interaction.response.edit_message(embed=self.create_embed())
