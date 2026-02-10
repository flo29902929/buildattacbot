import discord
from discord.ext import commands

# ---------------- CONFIG ----------------
TOKEN = "MTQ1OTQ4MDQ5NDU4MzMyMDYwOA.GAVCM7.drwBz7aZWsMvpmreeEo3V5MdnRPTsuzlaiW2iY"
GUILD_ID = 1458519099973046517
VERIFY_ROLE_ID = 1458643932631138325
SUPPORT_ROLE_ID = 1458643780721709187
TICKET_CATEGORY_ID = 1470476712310476941
# ---------------------------------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- Helper ----------------
async def precheck():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("❌ Server (Guild) nicht gefunden! Prüfe die GUILD_ID.")
        return None, None, None, None
    verify_role = guild.get_role(VERIFY_ROLE_ID)
    support_role = guild.get_role(SUPPORT_ROLE_ID)
    category = guild.get_channel(TICKET_CATEGORY_ID)
    if not verify_role:
        print("❌ Verify-Rolle nicht gefunden! Prüfe VERIFY_ROLE_ID.")
    if not support_role:
        print("❌ Support-Rolle nicht gefunden! Prüfe SUPPORT_ROLE_ID.")
    if not category:
        print("❌ Ticket-Kategorie nicht gefunden! Prüfe TICKET_CATEGORY_ID.")
    return guild, verify_role, support_role, category

# ---------------- Verify ----------------
@bot.command()
async def verifypanel(ctx):
    embed = discord.Embed(
        title="Willkommen!",
        description="Klicke auf ✅ um dich zu verifizieren!",
        color=discord.Color.green()
    )
    button = discord.ui.Button(label="✅ Verifizieren", style=discord.ButtonStyle.green)

    async def button_callback(interaction):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Du wurdest verifiziert!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Verify-Rolle nicht gefunden!", ephemeral=True)

    button.callback = button_callback
    view = discord.ui.View()
    view.add_item(button)
    await ctx.send(embed=embed, view=view)

# ---------------- Ticket ----------------
class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        button = discord.ui.Button(label="📝 Ticket erstellen", style=discord.ButtonStyle.blurple)
        button.callback = self.create_ticket
        self.add_item(button)

    async def create_ticket(self, interaction: discord.Interaction):
        guild, _, support_role, category = await precheck()
        if not all([guild, support_role, category]):
            await interaction.response.send_message("❌ Fehler: Check CMD-Log.", ephemeral=True)
            return

        ticket_name = f"ticket-{interaction.user.name}".lower()
        existing = discord.utils.get(category.channels, name=ticket_name)
        if existing:
            await interaction.response.send_message(f"Du hast bereits ein Ticket: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await category.create_text_channel(ticket_name, overwrites=overwrites)
        embed = discord.Embed(
            title="Support Ticket",
            description=f"{interaction.user.mention} hat ein Ticket erstellt.\nAktuell: Niemand bearbeitet das Ticket.",
            color=discord.Color.blurple()
        )
        view = TicketButtons(ticket_channel, interaction.user)
        await ticket_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket erstellt: {ticket_channel.mention}", ephemeral=True)

# ---------------- Ticket Buttons ----------------
class TicketButtons(discord.ui.View):
    def __init__(self, channel, owner):
        super().__init__(timeout=None)
        self.channel = channel
        self.owner = owner
        self.claimer = None  # Wer aktuell das Ticket bearbeitet

        claim_button = discord.ui.Button(label="🎫 Claim", style=discord.ButtonStyle.green)
        claim_button.callback = self.claim_ticket
        close_button = discord.ui.Button(label="🔒 Close", style=discord.ButtonStyle.red)
        close_button.callback = self.close_ticket
        transfer_button = discord.ui.Button(label="🔄 Transfer", style=discord.ButtonStyle.gray)
        transfer_button.callback = self.transfer_ticket

        self.add_item(claim_button)
        self.add_item(close_button)
        self.add_item(transfer_button)

    async def update_embed(self):
        desc = f"{self.owner.mention} hat ein Ticket erstellt.\n"
        desc += f"Aktuell: {self.claimer.mention if self.claimer else 'Niemand bearbeitet das Ticket.'}"
        embed = discord.Embed(title="Support Ticket", description=desc, color=discord.Color.blurple())
        await self.channel.purge(limit=10)
        await self.channel.send(embed=embed, view=self)

    async def claim_ticket(self, interaction):
        _, _, support_role, _ = await precheck()
        if support_role and support_role in interaction.user.roles:
            self.claimer = interaction.user
            await self.channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await self.update_embed()
            await interaction.response.send_message(f"✅ {interaction.user.mention} hat das Ticket übernommen!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nur Support-Team kann Tickets claimen!", ephemeral=True)

    async def close_ticket(self, interaction):
        _, _, support_role, _ = await precheck()
        if support_role and (support_role in interaction.user.roles or interaction.user == self.owner):
            await self.channel.delete()
        else:
            await interaction.response.send_message("❌ Nur Support-Team oder Ticket-Ersteller kann schließen!", ephemeral=True)

    async def transfer_ticket(self, interaction):
        _, _, support_role, _ = await precheck()
        if not support_role or support_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Nur Support-Team kann Tickets übertragen!", ephemeral=True)
            return

        await interaction.response.send_message(
            "Bitte gib den Namen oder die ID des Supporters ein, an den du das Ticket übertragen willst. Beispiel: `@Supporter` oder `123456789012345678`",
            ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
        except:
            await interaction.followup.send("❌ Zeit abgelaufen! Übertragung abgebrochen.", ephemeral=True)
            return

        member = None
        if msg.mentions:
            member = msg.mentions[0]
        else:
            try:
                member_id = int(msg.content.strip())
                member = interaction.guild.get_member(member_id)
            except:
                member = discord.utils.get(interaction.guild.members, name=msg.content.strip())

        if not member or support_role not in member.roles:
            await interaction.followup.send("❌ Supporter nicht gefunden oder hat nicht die Support-Rolle!", ephemeral=True)
            return

        self.claimer = member
        await self.channel.set_permissions(member, read_messages=True, send_messages=True)
        await self.update_embed()
        await interaction.followup.send(f"✅ Ticket übertragen an {member.mention}!", ephemeral=True)

# ---------------- Commands ----------------
@bot.command()
async def ticketpanel(ctx):
    if ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Support System",
            description="Klicke auf den Button, um ein Ticket zu erstellen!",
            color=discord.Color.blurple()
        )
        view = TicketPanel()
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send("❌ Du hast keine Rechte dafür.")

# ---------------- Bot starten ----------------
@bot.event
async def on_ready():
    print(f"✅ Bot online! Name: {bot.user}")
    await precheck()

bot.run(TOKEN)


