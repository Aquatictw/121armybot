import discord
from random import sample, choice
from discord.ui import View, Button
from image_util import create_table_image, create_hand_image


class AttackView(View):
    def __init__(self, battle_view, first_attacker):
        super().__init__()
        self.battle_view = battle_view
        self.first_attacker = first_attacker
        self.second_attacker = (
            self.battle_view.player2
            if self.first_attacker == self.battle_view.player1
            else self.battle_view.player1
        )
        self.current_attacker = self.first_attacker
        self.attack_pairs = {self.first_attacker.id: [], self.second_attacker.id: []}
        self.used_attackers = {self.first_attacker.id: [], self.second_attacker.id: []}
        self.show_attacker_selection()

    def get_attacking_cards(self):
        return (
            self.battle_view.p1_table
            if self.current_attacker == self.battle_view.player1
            else self.battle_view.p2_table
        )

    def get_defending_cards(self):
        return (
            self.battle_view.p2_table
            if self.current_attacker == self.battle_view.player1
            else self.battle_view.p1_table
        )

    def show_attacker_selection(self):
        self.clear_items()
        attacking_cards = self.get_attacking_cards()
        for i, card in enumerate(attacking_cards):
            _, card_name, _, _, _, _, _ = card
            if card_name[:10] not in self.used_attackers[self.current_attacker.id]:
                button = Button(
                    label=f"選擇 {card_name[:10]}",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"attacker_{card_name[:10]}",
                    row=i // 5,
                )
                button.callback = self.select_attacker
                self.add_item(button)

        finish_button = Button(
            label="結束攻擊",
            style=discord.ButtonStyle.danger,
            custom_id="finish_attacking",
            row=4,
        )
        finish_button.callback = self.finish_attacking
        self.add_item(finish_button)

    def show_target_selection(self):
        self.clear_items()
        defending_cards = self.get_defending_cards()
        if not defending_cards:
            opponent = (
                self.battle_view.player2
                if self.current_attacker == self.battle_view.player1
                else self.battle_view.player1
            )
            button = Button(
                label=f"攻擊 {opponent.display_name}",
                style=discord.ButtonStyle.danger,
                custom_id=f"target_{opponent.display_name}",
            )
            button.callback = self.select_target
            self.add_item(button)
        else:
            for i, card in enumerate(defending_cards):
                _, card_name, _, _, _, _, _ = card
                button = Button(
                    label=f"攻擊 {card_name[:10]}",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"target_{card_name[:10]}",
                    row=i // 5,
                )
                button.callback = self.select_target
                self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.current_attacker:
            await interaction.response.send_message(
                "現在不是你的回合。", ephemeral=True
            )
            return False
        return True

    async def select_attacker(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.attacking_card_index = interaction.data["custom_id"].split("_")[1]
        self.show_target_selection()
        await interaction.edit_original_response(view=self)

    async def select_target(self, interaction: discord.Interaction):
        await interaction.response.defer()
        target_card_index = interaction.data["custom_id"].split("_")[1]
        self.attack_pairs[self.current_attacker.id].append(
            (self.attacking_card_index, target_card_index)
        )
        self.used_attackers[self.current_attacker.id].append(self.attacking_card_index)
        self.show_attacker_selection()
        await interaction.edit_original_response(view=self)

    async def finish_attacking(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.current_attacker == self.first_attacker:
            self.current_attacker = self.second_attacker
            self.show_attacker_selection()
            embed = interaction.message.embeds[0]
            embed.title = f"⚔️ 回合 {self.battle_view.round} 戰鬥階段 - {self.current_attacker.display_name} 攻擊！"

            await self.battle_view.process_attacks(self.attack_pairs)
            await interaction.edit_original_response(embed=embed, view=self)
        else:  # both players finish attacking
            self.battle_view.round += 1
            self.battle_view.turn = self.battle_view.player1
            await self.battle_view.process_attacks(self.attack_pairs)


class HandView(View):
    # Processing information regard the private hand views
    def __init__(self, hand, battle_view, original_interaction):
        super().__init__()
        self.hand = hand
        self.battle_view = battle_view
        self.original_interaction = original_interaction
        self.deploying_player = self.battle_view.turn
        self.show_draw_phase_buttons()

    def show_draw_phase_buttons(self):  # draw card buttons
        self.clear_items()
        is_p1_turn = self.deploying_player == self.battle_view.player1
        skipped_draw_flag = (
            self.battle_view.p1_skipped_draw
            if is_p1_turn
            else self.battle_view.p2_skipped_draw
        )

        draw_button = Button(
            label="抽卡", style=discord.ButtonStyle.success, custom_id="draw_card_1"
        )
        draw_button.callback = self.draw_card_action
        self.add_item(draw_button)

        if skipped_draw_flag:
            draw_2_button = Button(
                label="抽卡*2",
                style=discord.ButtonStyle.success,
                custom_id="draw_card_2",
            )
            draw_2_button.callback = self.draw_card_action
            self.add_item(draw_2_button)

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
                custom_id=f"{card_name}_{tier['text']}",
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
        draw_count = int(interaction.data["custom_id"].split("_")[2])

        is_p1_turn = self.deploying_player == self.battle_view.player1
        inventory = (
            self.battle_view.p1_inventory
            if is_p1_turn
            else self.battle_view.p2_inventory
        )
        hand = self.battle_view.p1_hand if is_p1_turn else self.battle_view.p2_hand

        if inventory:
            drawn_cards = sample(inventory, min(draw_count, len(inventory)))
            for card in drawn_cards:
                inventory.remove(card)
                hand.append(card)

        if is_p1_turn:
            self.battle_view.p1_skipped_draw = False
        else:
            self.battle_view.p2_skipped_draw = False

        self.show_deployment_phase_buttons()
        hand_image = create_hand_image(hand)
        await interaction.edit_original_response(
            content="請選擇你要部屬的卡片:", view=self, attachments=[hand_image]
        )

    async def skip_draw_action(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.deploying_player == self.battle_view.player1:
            self.battle_view.p1_skipped_draw = True
        else:
            self.battle_view.p2_skipped_draw = True

        self.show_deployment_phase_buttons()
        hand = (
            self.battle_view.p1_hand
            if self.deploying_player == self.battle_view.player1
            else self.battle_view.p2_hand
        )
        hand_image = create_hand_image(hand)
        await interaction.edit_original_response(
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
            content="你已完成部屬。", view=self, attachments=[]
        )

        is_p1_turn = self.battle_view.turn == self.battle_view.player1

        if is_p1_turn:  # change side
            self.battle_view.turn = self.battle_view.player2
        else:
            self.battle_view.turn = self.battle_view.player1

        battle_image = create_table_image(
            self.battle_view.p1_table,
            self.battle_view.p2_table,
            self.battle_view.player1.display_name,
            self.battle_view.player2.display_name,
        )

        if is_p1_turn:
            embed = self.battle_view.create_embed()
            view = self.battle_view
        else:
            if self.battle_view.round >= 2:
                # Battle phase when two player finishes deployment and round is 1 or more
                attacker = choice([self.battle_view.player1, self.battle_view.player2])
                embed = discord.Embed(
                    title=f"⚔️ 回合 {self.battle_view.round} 戰鬥階段 - 由 {attacker.display_name} 先攻！",
                    url="https://laxd.com",
                    colour=0xFF0000,
                )
                original_embed = self.battle_view.create_embed()
                embed.set_author(name=original_embed.author.name)
                embed.add_field(
                    name=f"{self.battle_view.player1.display_name}",
                    value=original_embed.fields[0].value,
                    inline=True,
                )
                embed.add_field(
                    name=f"{self.battle_view.player2.display_name}",
                    value=original_embed.fields[1].value,
                    inline=True,
                )
                embed.add_field(
                    name="📊 狀態", value=original_embed.fields[2].value, inline=False
                )
                embed.set_footer(
                    text=original_embed.footer.text,
                    icon_url=original_embed.footer.icon_url,
                )
                view = AttackView(self.battle_view, attacker)
            else:
                self.battle_view.round += 1
                embed = self.battle_view.create_embed()
                view = self.battle_view

        await self.original_interaction.edit_original_response(
            embed=embed,
            attachments=[battle_image],
            view=view,
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
    # For proccessing information of the table
    def __init__(self, player1, player2, p1_inventory, p2_inventory):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.p1_table = []
        self.p2_table = []
        self.attack_pairs = {}

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
        self.p1_skipped_draw = False
        self.p2_skipped_draw = False

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
            colour=0x00C7FF,
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

    async def process_attacks(self, attack_pairs):
        self.attack_pairs = attack_pairs

        # We will implement the logic to update the board, table, and hands here in the future.
        await self.original_interaction.followup.send(f"Attack details: {attack_pairs}")

        await self.original_interaction.edit_original_response(
            embed=self.create_embed(), view=self
        )

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
