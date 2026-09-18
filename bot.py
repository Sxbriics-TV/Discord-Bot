import discord
import random
import json
from discord.ext import commands
from discord import app_commands
from ticket_system import TicketView, CloseView, TicketSetupModal

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):
    titel_eingabe = discord.ui.TextInput(label="Titel", placeholder="z.B. Voice-Support")
    text_eingabe = discord.ui.TextInput(
        label="Nachricht",
        style=discord.TextStyle.paragraph,
        placeholder="Beschreibe hier den Inhalt...",
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.titel_eingabe.value, description=self.text_eingabe.value, color=discord.Color.blue())
        embed.set_footer(text=interaction.client.user.name, icon_url=interaction.client.user.display_avatar.url)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Embed gepostet!", ephemeral=True)

def lade_einstellungen():
    try:
        with open("einstellungen.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def speichere_einstellungen(einstellungen):
    with open("einstellungen.json", "w") as f:
        json.dump(einstellungen, f)

einstellungen = lade_einstellungen()

@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user}")
    bot.add_view(TicketView(einstellungen))
    bot.add_view(CloseView(einstellungen))
    await bot.tree.sync()
    print("Slash-Commands synchronisiert")
    aktivitaet = discord.Game("spielt Python 🐍")
    await bot.change_presence(activity=aktivitaet)

@bot.event
async def on_member_join(member):
    server_id = str(member.guild.id)
    if server_id in einstellungen:
        server_einstellungen = einstellungen[server_id]

        if "kanal_id" in server_einstellungen:
            kanal = member.guild.get_channel(server_einstellungen["kanal_id"])
            if kanal:
                await kanal.send(f"Willkommen auf dem Server, {member.mention}! 🎉")

        if "rolle_id" in server_einstellungen:
            rolle = member.guild.get_role(server_einstellungen["rolle_id"])
            if rolle:
                try:
                    await member.add_roles(rolle)
                except discord.Forbidden:
                    print("Fehler: Rollen-Hierarchi prüfen")

@bot.tree.command(name="setup_ticket", description="Richtet das Ticket-System ein (nur Admins)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    await interaction.response.send_modal(TicketSetupModal(einstellungen))

@bot.tree.command(name="setup_ticket_rolle", description="Fügt eine Rolle hinzu, die Tickets sehen kann (nur Admins)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket_rolle(interaction: discord.Interaction, rolle: discord.Role):
    server_id = str(interaction.guild_id)
    if server_id not in einstellungen:
        einstellungen[server_id] = {}
    
    einstellungen[server_id].setdefault("ticket_rollen", [])
    
    if rolle.id not in einstellungen[server_id]["ticket_rollen"]:
        einstellungen[server_id]["ticket_rollen"].append(rolle.id)
        speichere_einstellungen(einstellungen)
        
        aktualisiert = 0
        for kanal in interaction.guild.text_channels:
            if kanal.name.startswith("ticket-"):
                await kanal.set_permissions(rolle, view_channel=True, send_messages=True)
                aktualisiert += 1
        
        await interaction.response.send_message(f"{rolle.mention} kann jetzt Tickets sehen. {aktualisiert} bestehende Tickets wurden aktualisiert.")
    else:
        await interaction.response.send_message(f"{rolle.mention} hat bereits Zugriff auf Tickets.")

@bot.tree.command(name="setup_willkommen", description="Legt den Willkommenskanal fest (nur Admins)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_willkommen(interaction: discord.Interaction, kanal: discord.TextChannel):
    server_id = str(interaction.guild_id)
    if server_id not in einstellungen:
        einstellungen[server_id] = {}
    einstellungen[server_id]["kanal_id"] = kanal.id
    speichere_einstellungen(einstellungen)
    await interaction.response.send_message(f"Willkommenskanal gesetzt auf: {kanal.mention}")

@bot.tree.command(name="setup_rolle", description="Legt die Beitritts-Rolle fest (nur Admins)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_rolle(interaction: discord.Interaction, rolle: discord.Role):
    server_id = str(interaction.guild_id)
    if server_id not in einstellungen:
        einstellungen[server_id] = {}
    einstellungen[server_id]["rolle_id"] = rolle.id
    speichere_einstellungen(einstellungen)
    await interaction.response.send_message(f"Rolle gesetzt auf: {rolle.mention}")

@bot.tree.command(name="reaction_role", description="Erstellt eine Reaction Role Nachricht (nur Admins)")
@app_commands.checks.has_permissions(administrator=True)
async def reaction_role(interaction: discord.Interaction, rolle: discord.Role, emoji: str, text: str):
    nachricht = await interaction.channel.send(f"{text}\n\nKlicke  -  {emoji}  für  {rolle.mention}")
    await nachricht.add_reaction(emoji)

    nachricht_id = str(nachricht.id)
    einstellungen.setdefault("reaction_roles", {})
    einstellungen["reaction_roles"][nachricht_id] = {emoji: rolle.id}
    speichere_einstellungen(einstellungen)

    await interaction.response.send_message("Reaction-Role-Nachricht erstellt!", ephemeral=True)

@bot.tree.command(name="setup_avatar_kanal", description="Legt den Kanal für Profilbilder fest (nur admins)")
@app_commands.checks.has_permissions(administrator=True)
async def setup_avatar_kanal(interaction: discord.Interaction, kanal: discord.TextChannel):
    server_id = str(interaction.guild_id)
    if server_id not in einstellungen:
        einstellungen[server_id] = {}
    einstellungen[server_id]["avatar_kanal_id"] = kanal.id
    speichere_einstellungen(einstellungen)
    await interaction.response.send_message(f"Avatar-Kanal gesetzt auf: {kanal.mention}")

@bot.tree.command(name="avatar", description="Postet das Profilbild eines Nutzers")
async def avatar(interaction: discord.Interaction, nutzer: discord.User):
    server_id = str(interaction.guild_id)

    if server_id not in einstellungen or "avatar_kanal_id" not in einstellungen[server_id]:
        await interaction.response.send_message("Es wurde noch kein Avatar-Kanal festgelegt")
        return

    kanal_id = einstellungen[server_id]["avatar_kanal_id"]
    kanal = interaction.guild.get_channel(kanal_id)

    if kanal:
        embed = discord.Embed(title=f"Profilbild von {nutzer.name}")
        embed.set_image(url=nutzer.display_avatar.url)
        await kanal.send(embed=embed)
        await interaction.response.send_message("Profilbild gepostet!", ephemeral=True)
    else:
        await interaction.response.send_message("Der festgelegte Kanal existiert nicht mehr.", ephemeral=True)

@bot.tree.command(name="embed", description="Erstellt eine Embed Nachricht")
@app_commands.checks.has_permissions(administrator=True)
async def embed(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())

@bot.tree.command(name="clear", description="Löscht Nachrichten (nur Admins)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, anzahl: int):
    await interaction.response.defer(ephemeral=True)
    geloescht = await interaction.channel.purge(limit=anzahl)
    await interaction.followup.send(f"{len(geloescht)} Nachrichten gelöscht.", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return

    nachricht_id = str(payload.message_id)
    reaction_roles = einstellungen.get("reaction_roles", {})

    if nachricht_id in reaction_roles:
        emoji_rollen = reaction_roles[nachricht_id]
        emoji_str = str(payload.emoji)
        if emoji_str in emoji_rollen:
            rolle_id = emoji_rollen[emoji_str]
            rolle = payload.member.guild.get_role(rolle_id)
            if rolle:
                await payload.member.add_roles(rolle)

@bot.event
async def on_raw_reaction_remove(payload):
    nachricht_id = str(payload.message_id)
    reaction_roles = einstellungen.get("reaction_roles", {})

    if nachricht_id in reaction_roles:
        emoji_rollen = reaction_roles[nachricht_id]
        emoji_str = str(payload.emoji)
        if emoji_str in emoji_rollen:
            rolle_id = emoji_rollen[emoji_str]
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            rolle = guild.get_role(rolle_id)
            if rolle and member:
                await member.remove_roles(rolle)

@bot.tree.command(name="würfel", description="Du kannst würfeln")
async def würfel(interaction: discord.Interaction):
    zahl = random.randint(1, 6)
    await interaction.response.send_message(f"Du hast die {zahl} gewürfelt 🎲")

@bot.tree.command(name="echo", description="Gibt ein Echo aus")
async def echo(interaction: discord.Interaction, nachricht: str):
    await interaction.response.send_message(nachricht)

bot.run("MTU0OTg2MDkwNjEyMzY2MTQ2Mw.GyyB8x.D2WuhvUVGjjCAhT1nFY65Scdtm-IGVJnNde2JQ")