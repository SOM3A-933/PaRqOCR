import discord
from discord.ext import commands
import easyocr
import asyncio
import os
import zipfile
import gdown
import re
import shutil
import uuid

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

print("Loading the OCR engine...")
reader = easyocr.Reader(['en', 'ko', 'ja', 'ch_sim', 'ch_tra'], gpu=False)
print("Bot is ready!")

def process_image(image_path):
    results = reader.readtext(
        image_path, 
        detail=0, 
        paragraph=True, 
        contrast_ths=0.1, 
        adjust_contrast=0.5
    )
    return "\n".join(results)

def extract_drive_id(url):
    match = re.search(r"/(?:d|folders)/([a-zA-Z0-9_-]+)", url)
    if match: return match.group(1)
    match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None

@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user}')

@bot.command()
async def extract(ctx, drive_link: str = None):
    await ctx.send("⏳ Extracting text, please wait...")
    
    extracted_texts = []
    session_id = uuid.uuid4().hex
    temp_dir = f"temp_{session_id}"
    os.makedirs(temp_dir, exist_ok=True)
    output_txt_path = os.path.join(temp_dir, "extracted_text.txt")

    try:
        if drive_link:
            file_id = extract_drive_id(drive_link)
            if not file_id:
                await ctx.send("❌ Invalid Google Drive link.")
                return
            
            download_path = os.path.join(temp_dir, "drive_file")
            gdown.download(id=file_id, output=download_path, quiet=True)
            
            if zipfile.is_zipfile(download_path):
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    for file in sorted(zip_ref.namelist()):
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            img_path = os.path.join(temp_dir, file)
                            text = await asyncio.to_thread(process_image, img_path)
                            extracted_texts.append(f"=== {file} ===\n{text}\n")
            else:
                text = await asyncio.to_thread(process_image, download_path)
                extracted_texts.append(f"=== Drive File ===\n{text}\n")

        elif ctx.message.attachments:
            for attachment in ctx.message.attachments:
                file_path = os.path.join(temp_dir, attachment.filename)
                await attachment.save(file_path)

                if attachment.filename.lower().endswith('.zip'):
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                        for file in sorted(zip_ref.namelist()):
                            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                img_path = os.path.join(temp_dir, file)
                                text = await asyncio.to_thread(process_image, img_path)
                                extracted_texts.append(f"=== {file} ===\n{text}\n")
                elif attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    text = await asyncio.to_thread(process_image, file_path)
                    extracted_texts.append(f"=== {attachment.filename} ===\n{text}\n")
        else:
            await ctx.send("❌ Please attach an image, a ZIP file, or provide a Google Drive link.")
            return

        if extracted_texts:
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(extracted_texts))
            await ctx.send("✅ Extraction complete:", file=discord.File(output_txt_path))
        else:
            await ctx.send("⚠️ No text found in the provided files.")

    except Exception as e:
        await ctx.send(f"❌ Error: `{str(e)}`")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# بيسحب التوكن أمان من إعدادات السيرفر
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
