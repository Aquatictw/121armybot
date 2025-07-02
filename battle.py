import discord
from random import uniform, sample
from discord.ui import View, Button
from PIL import Image, ImageDraw
from io import BytesIO
import requests
from util import resize_and_crop_center

try:
    from PIL import ImageFont
    font = ImageFont.truetype("arial.ttf", 20) # Use a common font, adjust size as needed
except IOError:
    font = ImageFont.load_default()

def create_battle_image(p1_cards, p2_cards):
    background = Image.new('RGBA', (1200, 1200), (0, 0, 0, 0)) # Increased size for text and larger images
    draw = ImageDraw.Draw(background)

    # Player 1 cards on the left
    for i, card in enumerate(p1_cards):
        name, _, _, img_url, _, tier = card[:6] # Extract name and other details
        try:
            response = requests.get(img_url)
            card_img = Image.open(BytesIO(response.content)).convert("RGBA")
            card_img = resize_and_crop_center(card_img)
            card_img.thumbnail((200, 200)) # Increased thumbnail size
            
            # Calculate position for image and text
            img_x = 20
            img_y = i * 220 + 10 # Adjusted spacing for larger images
            text_x = img_x + card_img.width + 10 # Text to the right of the image
            text_y = img_y + (card_img.height - font.getbbox(name)[3]) // 2 # Center text vertically

            background.paste(card_img, (img_x, img_y), card_img)
            draw.text((text_x, text_y), name, font=font, fill=(255, 255, 255, 255)) # White text
        except Exception as e:
            print(f"Error processing image for p1: {img_url} - {e}")


    # Player 2 cards on the right
    for i, card in enumerate(p2_cards):
        name, _, _, img_url, _, tier = card[:6] # Extract name and other details
        try:
            response = requests.get(img_url)
            card_img = Image.open(BytesIO(response.content)).convert("RGBA")
            card_img = resize_and_crop_center(card_img)
            card_img.thumbnail((200, 200)) # Increased thumbnail size

            # Calculate position for image and text
            img_x = 1200 - card_img.width - 20 # Right aligned
            img_y = i * 220 + 10 # Adjusted spacing for larger images
            text_x = img_x - 10 - font.getbbox(name)[2] # Text to the left of the image
            text_y = img_y + (card_img.height - font.getbbox(name)[3]) // 2 # Center text vertically

            background.paste(card_img, (img_x, img_y), card_img)
            draw.text((text_x, text_y), name, font=font, fill=(255, 255, 255, 255)) # White text
        except Exception as e:
            print(f"Error processing image for p2: {img_url} - {e}")

    buffer = BytesIO()
    background.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(fp=buffer, filename="battle.png")

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
    def __init__(self, player1, player2, p1_inventory, p2_inventory):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.p1_cards = sample(p1_inventory, 5) #隨機抽取5張卡排
        self.p2_cards = sample(p2_inventory, 5)
        self.max_health = 114
        self.health1 = self.max_health
        self.round = 1
        self.health2 = self.max_health
        self.turn = player1

    def create_embed(self):
        health_bar1_blocks = round((self.health1 / self.max_health) * 10) if self.health1 > 0 else 0
        health_bar1 = "🟥" * health_bar1_blocks + "⬛" * (10 - health_bar1_blocks)
        
        health_bar2_blocks = round((self.health2 / self.max_health) * 10) if self.health2 > 0 else 0
        health_bar2 = "🟥" * health_bar2_blocks + "⬛" * (10 - health_bar2_blocks)
        
        embed = discord.Embed(title=f"🛡️ 回合 {self.round} -  輪到{self.turn.display_name}",
                      url="https://laxd.com",
                      colour=0x000000)
        embed.set_author(name=f"Homo戰鬥開始🗡️ {self.player1.display_name} v.s. {self.player2.display_name}")
        embed.add_field(name=f"{self.player1.display_name}", value=health_bar1, inline=True)
        embed.add_field(name=f"{self.player2.display_name}", value=health_bar2, inline=True)
        embed.add_field(name="📊 狀態",
                value=f"{self.player1.display_name} {round(self.health1, 1)}/{self.max_health} ⚔️ {self.player2.display_name} {round(self.health2, 1)}/{self.max_health}",
                inline=False)

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
        
        if self.health1 <= 0: # player1 dead
            self.health1 = 0
            self.stop()
            await interaction.response.edit_message(embed=self.create_embed(), view=None)
            await interaction.followup.send(f"{self.player2.mention} 獲勝！")
            return
        
        if self.health2 <= 0: #player2 dead 
            self.health2 = 0
            self.stop()
            await interaction.response.edit_message(embed=self.create_embed(), view=None)
            await interaction.followup.send(f"{self.player1.mention} 獲勝！")
            return

        self.round += 1
        battle_image = create_battle_image(self.p1_cards, self.p2_cards)
        await interaction.response.edit_message(embed=self.create_embed())
        await interaction.followup.send(file=battle_image)
