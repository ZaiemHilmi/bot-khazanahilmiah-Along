import os
import csv
import requests
from datetime import datetime
import telebot
from newspaper import Article
from groq import Groq

# ===== KONFIGURASI =====
# Hardcode token terus (sebab environment variables tak jalan)
BOT_TOKEN = "8260030414:AAF2tlpIrsJN2QRyO265T6xhfge7jyOEZfg"
GROQ_API_KEY = "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"

# Check token wujud
if not BOT_TOKEN or not GROQ_API_KEY:
    raise Exception("Token atau API Key tak boleh kosong.")

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

# Fail CSV untuk simpan artikel
CSV_FILE = "artikel.csv"

# Pastikan header CSV wujud
if not os.path.isfile(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Tarikh", "URL", "Tajuk", "Ringkasan", "Tema", "Penuh"])

# Fungsi untuk ekstrak artikel dari URL
def extract_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return {
            "title": article.title,
            "text": article.text,
            "success": True
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Fungsi untuk ringkasan guna Groq
def summarize_with_groq(text, title):
    prompt = f"""Tajuk: {title}

Teks: {text[:4000]}

Buat ringkasan dalam Bahasa Melayu dalam 3-5 ayat. Kemudian berikan tema utama (contoh: Palestin, Geopolitik, Ekonomi, Sosial, dll.) dalam satu perkataan atau frasa pendek.

Format jawapan:
RINGKASAN: [ringkasan]
TEMA: [tema]
"""
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        result = response.choices[0].message.content
        # Asingkan ringkasan dan tema
        lines = result.strip().split('\n')
        summary = ""
        theme = "Umum"
        for line in lines:
            if line.startswith("RINGKASAN:"):
                summary = line.replace("RINGKASAN:", "").strip()
            elif line.startswith("TEMA:"):
                theme = line.replace("TEMA:", "").strip()
        return summary, theme
    except Exception as e:
        return f"Error: {str(e)}", "Error"

# Simpan ke CSV
def save_to_csv(url, title, summary, theme, full_text):
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), url, title, summary, theme, full_text[:500]])

# Handler untuk mesej
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith("http"):
        bot.reply_to(message, "Sila hantar link yang sah (mesti bermula dengan http)")
        return

    # Hantar feedback awal
    bot.reply_to(message, "⏳ Sedang proses link...")
    
    # Ekstrak artikel
    article_data = extract_article(url)
    if not article_data["success"]:
        bot.reply_to(message, f"❌ Gagal ekstrak artikel: {article_data['error']}")
        return
    
    title = article_data["title"]
    full_text = article_data["text"]
    
    if not full_text:
        bot.reply_to(message, "❌ Artikel tiada kandungan teks.")
        return
    
    # Ringkasan guna AI
    summary, theme = summarize_with_groq(full_text, title)
    
    # Simpan dalam CSV
    save_to_csv(url, title, summary, theme, full_text)
    
    # Balas ke pengguna
    reply = f"""
✅ **Artikel disimpan!**
📌 *Tajuk:* {title}
📝 *Ringkasan:* {summary}
🏷️ *Tema:* {theme}

💾 Disimpan dalam pangkalan data.
"""
    bot.reply_to(message, reply, parse_mode="Markdown")

# Mulakan bot
print("Bot sedang berjalan...")
bot.infinity_polling()
