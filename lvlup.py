import discord
from util import tiers, get_card_by_name


class LvlupView(discord.ui.View):
    def __init__(self, ctx, inventory, save_callback):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.inventory = inventory
        self.save_callback = save_callback
        self.eligible_cards = self.get_eligible_cards()
        self.add_item(self.create_card_select())
        self.add_item(self.create_lvlup_button())

    def get_eligible_cards(self):
        eligible = []
        promotion_order = list(tiers.keys())
        for card in self.inventory:
            tier_text = card[5]["text"]
            current_tier_key = next(
                (key for key, value in tiers.items() if value["text"] == tier_text),
                None,
            )
            if not current_tier_key:
                continue

            current_tier_index = promotion_order.index(current_tier_key)
            if current_tier_index == len(promotion_order) - 1:
                continue  # Skip max tier

            lvlup_req = tiers[current_tier_key].get("lvlup_req")
            if lvlup_req and card[6] >= lvlup_req:
                eligible.append(card)
        return eligible

    def create_card_select(self):
        options = []
        if not self.eligible_cards:
            return discord.ui.Select(
                placeholder="沒有可以升級的卡片。",
                options=[discord.SelectOption(label="No eligible cards", value="none")],
                disabled=True,
            )

        for card in self.eligible_cards:
            card_name = card[1]
            tier_name = card[5]["text"]
            count = card[6]
            options.append(
                discord.SelectOption(
                    label=f"{card_name} ({tier_name}) x{count}",
                    value=f"{card_name}|{tier_name}",
                )
            )
        return discord.ui.Select(
            placeholder="選擇要升級的卡片...",
            min_values=1,
            max_values=len(options),
            options=options,
        )

    def create_lvlup_button(self):
        button = discord.ui.Button(label="升級", style=discord.ButtonStyle.success)
        button.callback = self.lvlup_callback
        return button

    async def lvlup_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_options = self.children[0].values
        if not selected_options or selected_options[0] == "none":
            await interaction.followup.send("請選擇要升級的卡片。")
            return

        upgraded_summary = {}
        promotion_order = list(tiers.keys())

        for option_value in selected_options:
            card_name, tier_name_text = option_value.split("|")

            card_to_lvlup = next(
                (
                    c
                    for c in self.inventory
                    if c[1] == card_name and c[5]["text"] == tier_name_text
                ),
                None,
            )

            if not card_to_lvlup:
                continue

            current_tier_key = next(
                (
                    key
                    for key, value in tiers.items()
                    if value["text"] == tier_name_text
                ),
                None,
            )
            if not current_tier_key:
                continue

            lvlup_req = tiers[current_tier_key].get("lvlup_req")
            if not lvlup_req or card_to_lvlup[6] < lvlup_req:
                continue

            num_new_cards = card_to_lvlup[6] // lvlup_req
            remaining_cards = card_to_lvlup[6] % lvlup_req

            current_tier_index = promotion_order.index(current_tier_key)
            next_tier_key = promotion_order[current_tier_index + 1]
            next_tier_info = tiers[next_tier_key]

            if remaining_cards > 0:
                card_to_lvlup[6] = remaining_cards
            else:
                self.inventory.remove(card_to_lvlup)

            higher_tier_card = next(
                (
                    c
                    for c in self.inventory
                    if c[1] == card_name and c[5]["text"] == next_tier_info["text"]
                ),
                None,
            )

            if higher_tier_card:
                higher_tier_card[6] += num_new_cards
            else:
                corp, _, desc, img, movies = get_card_by_name(card_name)
                new_card = [
                    corp,
                    card_name,
                    desc,
                    img,
                    movies,
                    next_tier_info,
                    num_new_cards,
                ]
                self.inventory.append(new_card)

            summary_key = (card_name, current_tier_key, next_tier_key)
            upgraded_summary[summary_key] = (
                upgraded_summary.get(summary_key, 0) + num_new_cards
            )

        if not upgraded_summary:
            await interaction.followup.send("沒有可以升級的卡片。")
        else:
            self.save_callback()
            summary_lines = [
                f"將 {tiers[old_tier]["lvlup_req"] * new_cards} 張 **{name} ({old_tier})** 合成為 {new_cards} 張 **{name} ({new_tier})**"
                for (name, old_tier, new_tier), new_cards in upgraded_summary.items()
            ]
            await interaction.followup.send(
                "✨ 升級完畢！\n" + "\n".join(summary_lines)
            )
