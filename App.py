import discord
from discord.ext import tasks, commands
import nest_asyncio
import random
import datetime
import os


nest_asyncio.apply()


TOKEN = os.environ.get("TOKEN")

intents = discord.Intents.all()
client = discord.Client(intents=intents)

# Store server variables globally
@client.event
async def on_ready():
    global CHANNEL, ADMIN, BOT, SERVER, ROLE
    CHANNEL = client.get_channel(int(os.environ.get("CHANNEL")))
    ADMIN = client.get_user(int(os.environ.get("ADMIN")))
    BOT = client.get_user(int(os.environ.get("BOT")))
    SERVER = client.get_guild(int(os.environ.get("SERVER")))
    ROLE = SERVER.get_role(int(os.environ.get("ROLE")))
    shuffler_loop.start()
    print(f"Cornlius Prime Activated. Server : {str(SERVER)}, Channel : {str(CHANNEL)}")


# Function to replace the current goody-hut occupant.
async def shuffle_occupant():
    occupants = [
        member for member in CHANNEL.members if member != BOT and member != ADMIN
    ]
    for occupant in occupants:
        await CHANNEL.set_permissions(occupant, view_channel=False)
        print(f"Previous occupant removed: {occupant}")

    if len(occupants) == 1:
        previous_occupant = occupants[0]
    else:
        previous_occupant = None

    # Determine a new goody-hut occupant, different to prior occupant (if exists).
    new_occupant = random.choice(ROLE.members)
    if previous_occupant:
        while new_occupant == previous_occupant:
            new_occupant = random.choice(ROLE.members)
    print(f"New occupant added: {new_occupant}")

    await CHANNEL.set_permissions(new_occupant, view_channel=True)


# Changes the occupant once per day.
# Loops every 60 seconds, checks whether the time is midnight.
@tasks.loop(seconds=60)
async def shuffler_loop():
    await client.wait_until_ready()
    current_time = datetime.datetime.now()

    if current_time.hour == 00 and current_time.minute == 00:
        await shuffle_occupant()
        await CHANNEL.send(f"You have found the goody hut.")


# Allows admin to start and stop the shuffler.
async def handle_admin_message(message, content):

    # Initialise the shuffler loop.
    if content.lower() == "begin the hut":
        shuffler_loop.start()
        print("loop Started")
        await message.delete()

    # Stops the shuffler loop.
    if content.lower() == "stop the hut":
        shuffler_loop.stop()
        print("loop Stopped")
        await message.delete()

    # Calls the shuffler once.
    if content.lower() == "shuffle the hut":
        await shuffle_occupant()
        await CHANNEL.send(f"**You have found the goody hut.**")
        print("channel Shuffled")
        await message.delete()


# Change server name if message contains "new server name" and "(<newname>)".
async def change_server_name(content):
    server_name = content[content.find("(") + 1 : content.rfind(")")]
    if len(server_name) > 0:
        await SERVER.edit(name=server_name)


# Change server icon if valid image is attached to message.
async def change_server_icon(message):
    if message.attachments[0].content_type in (
        "image/jpeg",
        "image/jpg",
        "image/png",
    ):
        await message.attachments[0].save(f"icon.png")
        with open("icon.png", "rb") as f:
            await SERVER.edit(icon=f.read())


# Duplicates messages which contain an attachment.
async def copy_message_with_attachments(message, content):
    reference = None
    file = await message.attachments[0].to_file(spoiler=False)
    embed = discord.Embed()
    embed.set_image(url=f"attachment://{file.filename}")

    if message.reference is not None:
        message_replied = await CHANNEL.fetch_message(message.reference.message_id)
        await message_replied.reply(content, file=file)
    else:
        await CHANNEL.send(content, file=file, reference=reference)


# Duplicates messages which do not contain an attachment.
async def copy_message(message, content):
    reference = None
    if message.reference is not None:
        message_replied = await CHANNEL.fetch_message(message.reference.message_id)
        await message_replied.reply(content)
    else:
        await CHANNEL.send(content, reference=reference)


# Replaces messages if message author is not BOT or ADMIN
# Copy messages, repost them as BOT, delete the original message.
@client.event
async def on_message(message):
    content = str(message.content)
    author = message.author
    channel = message.channel

    if channel == CHANNEL:

        # Ignore all messages from self.
        if author == BOT:
            return

        # Handle messages from admin.
        elif author == ADMIN:
            await handle_admin_message(message, content)
            return

        # Handles messages from occupant.
        print(f"Message: {str(author)}: {content}")

        if all(str in content.lower() for str in ["new server name", "(", ")"]):
            if content.find("(") < content.rfind(")"):
                await change_server_name(content)

        if message.attachments:
            if "new server icon" in content.lower():
                await change_server_icon(message)
            await copy_message_with_attachments(message, content)
        else:
            await copy_message(message, content)

        await client.wait_until_ready()
        await message.delete()


client.run(TOKEN)
