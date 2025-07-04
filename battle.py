import discord
from random import uniform, sample
from discord.ui import View, Button
from image_util import create_table_image, create_hand_image


class HandView(View):
    def __init__(self, hand, battle_view, original_interaction):
        super().__init__()
        self.hand = hand
        self.battle_view = battle_view
        self.original_interaction = original_interaction
        self.deploying_player = self.battle_view.turn
        self.show_draw_phase_buttons()

    def show_draw_phase_buttons(self):  # draw card buttons
        self.clear_items()
        draw_button = Button(
            label="抽卡", style=discord.ButtonStyle.success, custom_id="draw_card"
        )
        draw_button.callback = self.draw_card_action
        self.add_item(draw_button)

        skip_button = Button(
            label="不抽卡", style=discord.ButtonStyle.danger, custom_id="skip_draw"
        )
        skip_button.callback = self.skip_draw_action
        self.add_item(skip_button)

    def show_deployment_phase_buttons(self):  # deploy card buttons
        self.clear_items()
        current_hand = (
            self.battle_view.p1_hand
            if self.deploying_player == self.battle_view.player1
            else self.battle_view.p2_hand
        )

        for i, card in enumerate(current_hand):
            _, card_name, _, _, _, tier, _ = card
            button = Button(
                label=f"部屬 {card_name[:10]}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"{card_name}_{tier["text"]}",
                row=i // 5,
            )
            button.callback = self.deploy_card
            self.add_item(button)

        done_button = Button(
            label="完成部屬",
            style=discord.ButtonStyle.success,
            custom_id="done_deploying",
            row=4,
        )
        done_button.callback = self.finish_deployment
        self.add_item(done_button)

    async def draw_card_action(self, interaction: discord.Interaction):
        await interaction.response.defer()

        inventory = (
            self.battle_view.p1_inventory
            if self.deploying_player == self.battle_view.player1
            else self.battle_view.p2_inventory
        )
        hand = (
            self.battle_view.p1_hand
            if self.deploying_player == self.battle_view.player1
            else self.battle_view.p2_hand
        )

        if inventory:  # draw a card from inventory and remove it
            new_card = sample(inventory, 1)[0]
            inventory.remove(new_card)
            hand.append(new_card)

        self.show_deployment_phase_buttons()
        hand_image = create_hand_image(hand)
        await interaction.edit_original_response(  # after draw, change to deployment phase
            content="請選擇你要部屬的卡片:", view=self, attachments=[hand_image]
        )

    async def skip_draw_action(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.show_deployment_phase_buttons()
        hand = (
            self.battle_view.p1_hand
            if self.deploying_player == self.battle_view.player1
            else self.battle_view.p2_hand
        )
        hand_image = create_hand_image(hand)
        await interaction.edit_original_response(  # change to deployment phase
            content="請選擇你要部屬的卡片:", view=self, attachments=[hand_image]
        )

    async def deploy_card(self, interaction: discord.Interaction):
        await interaction.response.defer()
        interact_card_name, interact_card_tier = interaction.data["custom_id"].split(
            "_"
        )

        hand = (
            self.battle_view.p1_hand
            if self.deploying_player == self.battle_view.player1
            else self.battle_view.p2_hand
        )
        card_to_move = None
        for card in hand:
            if card[1] == interact_card_name and card[5]["text"] == interact_card_tier:
                card_to_move = card
                break

        if card_to_move:
            if (
                self.deploying_player == self.battle_view.player1
            ):  # remove from hand and add on table
                self.battle_view.p1_table.append(card_to_move)
                self.battle_view.p1_hand.remove(card_to_move)
            else:
                self.battle_view.p2_table.append(card_to_move)
                self.battle_view.p2_hand.remove(card_to_move)

            for item in self.children:  # disable button
                if (
                    isinstance(item, Button)
                    and item.custom_id == interaction.data["custom_id"]
                ):
                    item.disabled = True
                    break

            hand_image = create_hand_image(hand)

            await interaction.edit_original_response(
                content=f"你已部屬 。", view=self, attachments=[hand_image]
            )

    async def finish_deployment(self, interaction: discord.Interaction):
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True

        await interaction.response.edit_message(
            content=f"你已完成部屬。", view=self, attachments=[]
        )

        if self.battle_view.turn == self.battle_view.player1:
            self.battle_view.turn = self.battle_view.player2
        else:
            self.battle_view.turn = self.battle_view.player1
            self.battle_view.round += 1

        battle_image = create_table_image(
            self.battle_view.p1_table,
            self.battle_view.p2_table,
            self.battle_view.player1.display_name,
            self.battle_view.player2.display_name,
        )
        await self.original_interaction.edit_original_response(
            embed=self.battle_view.create_embed(),
            attachments=[battle_image],
            view=self.battle_view,
        )


class BattleConfirmation(View):
    def __init__(self, challenger, challenged):
        super().__init__()
        self.challenger = challenger
        self.challenged = challenged
        self.battle_accepted = False
        self.interaction = None

    @discord.ui.button(label="接受", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message(
                "這不是給你的按鈕。", ephemeral=True
            )
            return

        self.battle_accepted = True
        self.interaction = interaction
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="拒絕", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.challenged:
            await interaction.response.send_message("阿你是在按三小。", ephemeral=True)
            return

        self.stop()
        await interaction.response.send_message(
            f"{self.challenged.mention} 拒絕了 {self.challenger.mention} 的挑戰。"
        )


class BattleView(View):
    def __init__(self, player1, player2, p1_inventory, p2_inventory):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.p1_table = []
        self.p2_table = []

        # Store inventories
        self.p1_inventory = p1_inventory
        self.p2_inventory = p2_inventory

        # Draw initial hands and remove from inventories
        self.p1_hand = sample(self.p1_inventory, 5)
        for card in self.p1_hand:
            self.p1_inventory.remove(card)

        self.p2_hand = sample(self.p2_inventory, 5)
        for card in self.p2_hand:
            self.p2_inventory.remove(card)

        self.max_health = 114
        self.health1 = self.max_health
        self.round = 1
        self.health2 = self.max_health
        self.turn = player1
        self.original_interaction = None

    def create_embed(self):
        health_bar1_blocks = (
            round((self.health1 / self.max_health) * 10) if self.health1 > 0 else 0
        )
        health_bar1 = "🟥" * health_bar1_blocks + "⬛" * (10 - health_bar1_blocks)

        health_bar2_blocks = (
            round((self.health2 / self.max_health) * 10) if self.health2 > 0 else 0
        )
        health_bar2 = "🟥" * health_bar2_blocks + "⬛" * (10 - health_bar2_blocks)

        embed = discord.Embed(
            title=f"🛡️ 回合 {self.round} - 請{self.turn.display_name}部屬",
            url="https://laxd.com",
            colour=0x000000,
        )
        embed.set_author(
            name=f"Homo戰鬥開始🗡️ {self.player1.display_name} v.s. {self.player2.display_name}"
        )
        embed.add_field(
            name=f"{self.player1.display_name}", value=health_bar1, inline=True
        )
        embed.add_field(
            name=f"{self.player2.display_name}", value=health_bar2, inline=True
        )
        embed.add_field(
            name="📊 狀態",
            value=f"{self.player1.display_name} {round(self.health1, 1)}/{self.max_health} ⚔️ {self.player2.display_name} {round(self.health2, 1)}/{self.max_health}",
            inline=False,
        )

        embed.set_footer(
            text=f"{self.player1.display_name}把他的雞巴，放進了{self.player2.display_name}的皮炎裡面",
            icon_url="https://wiki.yjsnpi.nu/w/images/b/b7/%E3%83%89%E3%83%A4%E9%A1%94%E5%85%88%E8%BC%A9.jpg",
        )

        return embed

    @discord.ui.button(label="檢視卡片及部屬", style=discord.ButtonStyle.secondary)
    async def view_and_deploy(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.turn:
            await interaction.response.send_message(
                "現在不是你的回合。", ephemeral=True
            )
            return

        if (
            not self.original_interaction
        ):  # pass to hand_view to interact with current interaction
            self.original_interaction = interaction

        await interaction.response.defer(ephemeral=True)

        current_hand = self.p1_hand if self.turn == self.player1 else self.p2_hand

        hand_image = create_hand_image(current_hand)
        hand_view = HandView(current_hand, self, self.original_interaction)

        await interaction.followup.send(  # webhook style ephemeral message (requires button interaction)
            content="你要抽一張新的卡嗎?",
            view=hand_view,
            files=[hand_image],
            ephemeral=True,
        )
