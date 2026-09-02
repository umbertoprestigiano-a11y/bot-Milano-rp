import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

# Configurazione Intents e Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Banche Italiane Disponibili
BANCHE_DISPONIBILI = [
    "Intesa Sanpaolo",
    "Unicredit",
    "Poste Italiane (Postepay)",
    "Banco BPM",
    "Banca Monte dei Paschi di Siena (MPS)"
]

# Oggetti nel Negozio RP (Personalizzabili per Emergency Hamburg)
NEGOZIO = {
    "kit_riparazione": {"nome": "Kit di Riparazione Veicolo", "prezzo": 500},
    "licenza_armi": {"nome": "Porto d'Armi RP", "prezzo": 5000},
    "tanica_benzina": {"nome": "Tanica di Benzina", "prezzo": 150},
    "radio_rp": {"nome": "Radio Frequenze Forze dell'Ordine", "prezzo": 1200}
}

# Inizializzazione Database SQLite
def init_db():
    conn = sqlite3.connect("periferia_milano.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utenti (
            user_id INTEGER PRIMARY KEY,
            portafoglio INTEGER DEFAULT 1000,
            banca_nome TEXT DEFAULT NULL,
            banca_saldo INTEGER DEFAULT 0,
            numero_conto TEXT DEFAULT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            user_id INTEGER,
            item_id TEXT,
            quantita INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Gestione Connessione Database
def get_user_data(user_id):
    conn = sqlite3.connect("periferia_milano.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utenti WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    if not data:
        cursor.execute("INSERT INTO utenti (user_id, portafoglio) VALUES (?, 1000)", (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM utenti WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()
    conn.close()
    return data

@bot.event
async def on_ready():
    print(f"Bot PERIFERIA MILANO RP operativo come {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi Slash.")
    except Exception as e:
        print(f"Errore nella sincronizzazione comandi: {e}")

# ==================== BANCA ====================

@bot.tree.command(name="apri_conto", description="Apri un conto bancario presso un istituto italiano")
@app_commands.choices(banca=[
    app_commands.Choice(name=b, value=b) for b in BANCHE_DISPONIBILI
])
async def apri_conto(interaction: discord.Interaction, banca: app_commands.Choice[str]):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    
    if data[2] is not None:
        await interaction.response.send_message(f"❌ Hai già un conto aperto presso **{data[2]}** (IBAN: `{data[4]}`).", ephemeral=True)
        return

    iban = f"IT{random.randint(10,99)}P{random.randint(10000,99999)}{random.randint(100000000000,999999999999)}"
    
    conn = sqlite3.connect("periferia_milano.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE utenti SET banca_nome = ?, numero_conto = ? WHERE user_id = ?", (banca.value, iban, user_id))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title="🏦 PERIFERIA MILANO RP - Nuovo Conto Bancario",
        color=discord.Color.green(),
        description=f"Complimenti **{interaction.user.display_name}**, il tuo conto è stato aperto con successo!"
    )
    embed.add_field(name="Banca", value=banca.value, inline=True)
    embed.add_field(name="IBAN / N. Conto", value=f"`{iban}`", inline=True)
    embed.add_field(name="Saldo Iniziale", value="0 €", inline=False)
    embed.set_footer(text="Emergency Hamburg RP - Milano")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposito", description="Deposita contanti sul tuo conto bancario")
async def deposito(interaction: discord.Interaction, importo: int):
    if importo <= 0:
        await interaction.response.send_message("❌ Inserisci un importo valido.", ephemeral=True)
        return
        
    user_id = interaction.user.id
    data = get_user_data(user_id)
    portafoglio = data[1]
    banca_nome = data[2]

    if not banca_nome:
        await interaction.response.send_message("❌ Non possiedi un conto bancario. Usa `/apri_conto` prima di depositare.", ephemeral=True)
        return

    if portafoglio < importo:
        await interaction.response.send_message("❌ Non hai abbastanza contanti in portafoglio.", ephemeral=True)
        return

    conn = sqlite3.connect("periferia_milano.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE utenti SET portafoglio = portafoglio - ?, banca_saldo = banca_saldo + ? WHERE user_id = ?", (importo, importo, user_id))
    conn.commit()
    conn.close()

    await interaction.response.send_message(f"✅ Hai depositato **{importo} €** nel tuo conto **{banca_nome}**.")

@bot.tree.command(name="prelievo", description="Preleva denaro dal tuo conto bancario")
async def prelievo(interaction: discord.Interaction, importo: int):
    if importo <= 0:
        await interaction.response.send_message("❌ Inserisci un importo valido.", ephemeral=True)
        return

    user_id = interaction.user.id
    data = get_user_data(user_id)
    banca_saldo = data[3]

    if banca_saldo < importo:
        await interaction.response.send_message("❌ Saldo bancario insufficiente.", ephemeral=True)
        return

    conn = sqlite3.connect("periferia_milano.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE utenti SET portafoglio = portafoglio + ?, banca_saldo = banca_saldo - ? WHERE user_id = ?", (importo, importo, user_id))
    conn.commit()
    conn.close()

    await interaction.response.send_message(f"✅ Hai prelevato **{importo} €** dal tuo conto.")

# ==================== ECONOMIA & PROFILO ====================

@bot.tree.command(name="saldo", description="Controlla il tuo portafoglio e il tuo conto bancario")
async def saldo(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)

    embed = discord.Embed(
        title=f"💳 Portafoglio RP di {interaction.user.display_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="💵 Contanti in mano", value=f"{data[1]} €", inline=False)
    
    if data[2]:
        embed.add_field(name=f"🏦 Banca ({data[2]})", value=f"{data[3]} €\n*IBAN:* `{data[4]}`", inline=False)
    else:
        embed.add_field(name="🏦 Banca", value="Nessun conto aperto (Usa `/apri_conto`)", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="paga", description="Invia contanti a un altro cittadino di Milano RP")
async def paga(interaction: discord.Interaction, destinatario: discord.Member, importo: int):
    if importo <= 0 or destinatario.bot or destinatario.id == interaction.user.id:
        await interaction.response.send_message("❌ Operazione non valida.", ephemeral=True)
        return

    mittente_data = get_user_data(interaction.user.id)
    if mittente_data[1] < importo:
        await interaction.response.send_message("❌ Non hai abbastanza contanti in mano.", ephemeral=True)
        return

    get_user_data(destinatario.id)  # Assicura la presenza nel DB

    conn = sqlite3.connect("periferia_milano.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE utenti SET portafoglio = portafoglio - ? WHERE user_id = ?", (importo, interaction.user.id))
    cursor.execute("UPDATE utenti SET portafoglio = portafoglio + ? WHERE user_id = ?", (importo, destinatario.id))
    conn.commit()
    conn.close()

    await interaction.response.send_message(f"💸 **{interaction.user.mention}** ha pagato **{importo} €** a **{destinatario.mention}**.")

# ==================== NEGOZIO & VENDITE ====================

@bot.tree.command(name="negozio", description="Visualizza gli oggetti ed i servizi acquistabili")
async def negozio(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 Periferia Milano RP - Listino Vendite",
        description="Usa `/compra <codice_oggetto>` per effettuare un acquisto.",
        color=discord.Color.gold()
    )
    for item_id, info in NEGOZIO.items():
        embed.add_field(name=f"{info['nome']} (Codice: `{item_id}`)", value=f"Prezzo: {info['prezzo']} €", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="compra", description="Acquista un articolo dal negozio RP")
@app_commands.choices(articolo=[
    app_commands.Choice(name=v["nome"], value=k) for k, v in NEGOZIO.items()
])
async def compra(interaction: discord.Interaction, articolo: app_commands.Choice[str]):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    item_info = NEGOZIO[articolo.value]
    prezzo = item_info["prezzo"]

    # Verifica fondi (usa contanti o saldo banca)
    if data[1] >= prezzo:
        # Paga in contanti
        conn = sqlite3.connect("periferia_milano.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE utenti SET portafoglio = portafoglio - ? WHERE user_id = ?", (prezzo, user_id))
    elif data[3] >= prezzo:
        # Paga con banca
        conn = sqlite3.connect("periferia_milano.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE utenti SET banca_saldo = banca_saldo - ? WHERE user_id = ?", (prezzo, user_id))
    else:
        await interaction.response.send_message("❌ Non hai abbastanza fondi (né contanti né in banca) per effettuare l'acquisto.", ephemeral=True)
        return

    # Aggiungi oggetto all'inventario
    cursor.execute('''
        INSERT INTO inventario (user_id, item_id, quantita)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, item_id) DO UPDATE SET quantita = quantita + 1
    ''', (user_id, articolo.value))
    
    conn.commit()
    conn.close()

    await interaction.response.send_message(f"🛍️ Hai acquistato **{item_info['nome']}** per **{prezzo} €**!")

# Inserire il TOKEN del Bot Discord generato dal Developer Portal
bot.run("MTU0MzY2MDg4NTA0NDc1NjYwMw.GEFAlX.qn0I7qlU3deM_EmT5iSkyT_ljBh2Jxv5ApBf04")
