import discord
import asyncio


class TicketErstellenModal(discord.ui.Modal, title="Neues Ticket erstellen"):
    def __init__(self, einstellungen):
        super().__init__()
        self.einstellungen = einstellungen

    anliegen_eingabe = discord.ui.TextInput(
        label="Anliegen",
        style=discord.TextStyle.paragraph,
        placeholder="Bitte beschreibe dein Anliegen so genau wie möglich"
    )

    async def on_submit(self, interaction: discord.Interaction):
        kanal_name = f"ticket-{interaction.user.name}"

        vorhandener_kanal = discord.utils.get(interaction.guild.text_channels, name=kanal_name)
        if vorhandener_kanal:
            await interaction.response.send_message(f"Du hast bereits ein offenes Ticket: {vorhandener_kanal.mention}", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        server_id = str(interaction.guild_id)
        if server_id in self.einstellungen and "ticket_rollen" in self.einstellungen[server_id]:
            for rollen_id in self.einstellungen[server_id]["ticket_rollen"]:
                rolle = interaction.guild.get_role(rollen_id)
                if rolle:
                    overwrites[rolle] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        kanal = await interaction.guild.create_text_channel(name=kanal_name, overwrites=overwrites)

        embed = discord.Embed(
            title="Ticket erstellt",
            description=f"Willkommen {interaction.user.mention}!"
        )
        embed.add_field(name="Anliegen:", value=self.anliegen_eingabe.value, inline=False)
        embed.set_footer(text=interaction.client.user.name, icon_url=interaction.client.user.display_avatar.url)
        await kanal.send(embed=embed, view=CloseView(self.einstellungen))
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {kanal.mention}", ephemeral=True)


class CloseView(discord.ui.View):
    def __init__(self, einstellungen):
        super().__init__(timeout=None)
        self.einstellungen = einstellungen

    @discord.ui.button(label="Ticket schließen", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_button")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket wird geschlossen in 5 Sekunden...")
        nachricht = await interaction.original_response()

        for sekunde in range(4, 0, -1):
            await asyncio.sleep(1)
            await nachricht.edit(content=f"Ticket wird geschlossen in {sekunde} Sekunden...")

        await asyncio.sleep(1)
        await interaction.channel.delete()

    @discord.ui.button(label="Ticket übernehmen", style=discord.ButtonStyle.success, emoji="🙋", custom_id="claim_button")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        server_id = str(interaction.guild_id)
        ticket_rollen = []
        if server_id in self.einstellungen:
            ticket_rollen = self.einstellungen[server_id].get("ticket_rollen", [])

        nutzer_rollen_ids = [rolle.id for rolle in interaction.user.roles]
        hat_berechtigung = any(rid in nutzer_rollen_ids for rid in ticket_rollen)

        if not hat_berechtigung and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Du hast keine Berechtigung, Tickets zu übernehmen.", ephemeral=True)
            return

        button.label = f"Übernommen von {interaction.user.name}"
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"🙋 {interaction.user.mention} kümmert sich jetzt um dieses Ticket.")


class TicketView(discord.ui.View):
    def __init__(self, einstellungen):
        super().__init__(timeout=None)
        self.einstellungen = einstellungen

    @discord.ui.button(label="Ticket erstellen", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket_button")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketErstellenModal(self.einstellungen))


class TicketSetupModal(discord.ui.Modal, title="Ticket-System einrichten"):
    def __init__(self, einstellungen):
        super().__init__()
        self.einstellungen = einstellungen

    titel_eingabe = discord.ui.TextInput(label="Titel", placeholder="z.B. Support")
    text_eingabe = discord.ui.TextInput(
        label="Beschreibung",
        style=discord.TextStyle.paragraph,
        placeholder="z.B. Klick den Button, um ein Ticket zu erstellen."
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.titel_eingabe.value, description=self.text_eingabe.value, color=discord.Color.blue())
        embed.set_footer(text=interaction.client.user.name, icon_url=interaction.client.user.display_avatar.url)
        await interaction.channel.send(embed=embed, view=TicketView(self.einstellungen))
        await interaction.response.send_message("Ticket-Nachricht gepostet!", ephemeral=True)