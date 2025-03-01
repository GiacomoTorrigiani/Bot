import requests
import json
import telegram
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import os
import pytz
from xml.etree import ElementTree as ET
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
import html

# Configurazione
TOKEN = "7609784527:AAELMoW2E9Mw5DqJzKN2ySy-WRUZYDN5osw"
#OPENWEATHER_API_KEY = "73b7736ba768a47617e5cf52f93fdb76"
OPENWEATHER_API_KEY = "5796abbde9106b7da4febfae8c44c232"
FILE_STAZIONI = "stazioni.txt"
FILE_ITALO = "stazioni_mappate.txt"

# Variabili globali
DEBUG_MODE = True
favorite_cities = []
WEATHER_EMOJI = {
    '01d': '☀️', '01n': '🌙',
    '02d': '⛅', '02n': '⛅',
    '03d': '☁️', '03n': '☁️',
    '04d': '☁️', '04n': '☁️',
    '09d': '🌧️', '09n': '🌧️',
    '10d': '🌦️', '10n': '🌦️',
    '11d': '⛈️', '11n': '⛈️',
    '13d': '❄️', '13n': '❄️',
    '50d': '🌫️', '50n': '🌫️'
}

def generate_date_buttons():
    # Ottieni l'ora italiana corretta
    rome_tz = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(rome_tz)  # <--- Modifica qui
    
    buttons = []
    month_names = {
        1: 'Gen', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mag', 6: 'Giu',
        7: 'Lug', 8: 'Ago', 9: 'Set', 10: 'Ott', 11: 'Nov', 12: 'Dic'
    }
    for i in range(8):
        date = now + datetime.timedelta(days=i)
        month = month_names[date.month]
        label = f"{date.day} {month}"
        if i == 0:
            label = f"☀️ Oggi - {label}"
        elif i == 1:
            label = f"🌙 Domani - {label}"
        buttons.append(KeyboardButton(label))
    return buttons










def log_debug(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {datetime.datetime.now().strftime('%H:%M:%S')} - {message}")

# Funzioni meteo
def weather_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    # Aggiungi pulsanti date
    date_buttons = generate_date_buttons()
    for i in range(0, len(date_buttons), 2):
        row = date_buttons[i:i+2]
        markup.row(*row)
    
    markup.add(KeyboardButton("➕ Aggiungi città"), KeyboardButton("🔙 Menu principale"))
    return markup


def get_coordinates(city):
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},IT&limit=1&appid={OPENWEATHER_API_KEY}"
    response = requests.get(geo_url)
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        return data['lat'], data['lon'], data.get('name', city)
    return None, None, city

def get_weather(city, forecast_day=0):
    lat, lon, city_name = get_coordinates(city)
    if not lat or not lon:
        return "❌ Città non trovata. Controlla il nome e riprova.", []

    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,alerts&appid={OPENWEATHER_API_KEY}&units=metric&lang=it"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        tz = pytz.timezone(data['timezone'])
        now = datetime.datetime.now(pytz.utc).astimezone(tz)

        # Processa i dati giornalieri
        daily = []
        for d in data.get('daily', []):
            dt = datetime.datetime.fromtimestamp(d['dt'], tz=tz)
            daily.append({
                "date": dt.date(),
                "temp_min": round(d['temp']['min'], 1),
                "temp_max": round(d['temp']['max'], 1),
                "desc": d['weather'][0]['description'],
                "icon": d['weather'][0]['icon'],
                "pop": d.get('pop', 0) * 100,
                "humidity": d['humidity'],
                "wind_speed": d['wind_speed'],
                "uvi": d.get('uvi', 0),
                "sunrise": datetime.datetime.fromtimestamp(d['sunrise'], tz=tz).strftime('%H:%M'),
                "wind_gust": d.get('wind_gust', 0),
                "clouds": d.get('clouds', 0),
                "pressure": d.get('pressure', 0),
                "dew_point": d.get('dew_point', 0),
                "feels_like_day": d['feels_like'].get('day', 0),
                "sunset": datetime.datetime.fromtimestamp(d['sunset'], tz=tz).strftime('%H:%M')
            })

        if forecast_day >= len(daily):
            return "❌ Non ci sono previsioni disponibili per il giorno selezionato.", []

        day_data = daily[forecast_day]
        selected_date = day_data['date']

        # Filtra i dati orari per il giorno selezionato
        hourly_for_day = []
        for h in data.get('hourly', []):
            h_dt = datetime.datetime.fromtimestamp(h['dt'], tz=tz)
            if h_dt.date() == selected_date:
                hourly_for_day.append({
                    "time": h_dt.strftime('%H:%M'),
                    "temp": round(h['temp'], 1),
                    "icon": h['weather'][0]['icon'],
                    "wind_speed": h.get('wind_speed', 0),
                    "wind_gust": h.get('wind_gust', 0),
                    "pop": h.get('pop', 0) * 100,
                    "humidity": h.get('humidity', 0)
                })
            elif h_dt.date() > selected_date:
                break

        # Costruzione del testo
        text = f"🌍 *{city_name} - {day_data['date'].strftime('%d/%m/%Y')}*\n\n"
        text += f"🌡️ Min/Max: {day_data['temp_min']}°C / {day_data['temp_max']}°C\n"
        text += f"📖 Condizioni: {day_data['desc'].capitalize()}\n"
        text += f"🌧️ Prob. precipitazioni: {day_data['pop']:.0f}%\n"
        text += f"💧 Umidità: {day_data['humidity']}%\n"
        text += f"🌬️ Vento: {day_data['wind_speed']} m/s\n"
        text += f"☀️ UV Index: {day_data['uvi']}\n"
        text += f"🌅 Alba: {day_data['sunrise']} | 🌇 Tramonto: {day_data['sunset']}\n"
        text += "\n🌡️ **Andamento Termico**\n"
        text += f"• Percepita di giorno: {day_data['feels_like_day']}°C\n"
        text += f"• Punto di rugiada: {day_data['dew_point']}°C\n\n"

        # Sezione oraria
        text += "⏳ **Previsioni**\n"
        for h in hourly_for_day:  # MODIFICATO: usiamo hourly_for_day invece di hourly
            emoji = WEATHER_EMOJI.get(h['icon'], '')
            text += (
                f"{h['time']} {emoji} {h['temp']}°C\n"
                f"• Vento: {h['wind_speed']} m/s (🔄 Raffiche {h['wind_gust']} m/s)\n"
                f"• Pioggia: {h['pop']}% • Umidità: {h['humidity']}%\n"
                "━━━━━━━━━━\n"
            )
        return text, daily
    else:
        return "❌ Errore nel recupero delle previsioni meteo.", []

def generate_weather_image(forecast_data, city, date):
    try:
        import matplotlib.pyplot as plt
        plt.switch_backend('Agg')  # Necessario per ambiente non interattivo
        
        # Prepara i dati per il grafico
        times = [f"{h['time']}" for h in forecast_data[:8]]  # Prime 8 ore
        temps = [h['temp'] for h in forecast_data[:8]]
        
        # Crea il grafico
        plt.figure(figsize=(10, 6))
        plt.plot(times, temps, marker='o', linestyle='-', color='#FF6B6B')
        plt.title(f'Andamento Termico - {city}\n{date.strftime("%d/%m/%Y")}', pad=20)
        plt.xlabel('Ora')
        plt.ylabel('Temperatura (°C)')
        plt.xticks(rotation=45)
        plt.grid(alpha=0.3)
        
        # Salva in buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf
        
    except Exception as e:
        log_debug(f"Errore generazione grafico: {str(e)}")
        return None

# Funzioni notizie
def get_news():
    url = "https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it"
    response = requests.get(url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        items = root.findall(".//item")[:5]
        news_list = "📰 <b>ULTIME NOTIZIE</b>\n\n"
        for item in items:
            title = html.escape(item.find("title").text)  # Assicurati di importare html
            link = item.find("link").text
            news_list += f"🔥 <b>{title}</b>\n<a href='{link}'>Leggi articolo ➡️</a>\n\n"
        return news_list
    else:
        return "❌ Errore nel recupero delle notizie"



# Funzioni treni (mantenute dalla versione precedente)
def load_italo_codes():
    italo_codes = {}
    try:
        with open(FILE_ITALO, 'r', encoding='utf-8') as file:
            next(file)
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        trenitalia_name = parts[0].strip()
                        italo_code = parts[3].strip()
                        if italo_code:
                            italo_codes[trenitalia_name] = italo_code
        log_debug(f"Caricati {len(italo_codes)} codici Italo")
    except Exception as e:
        log_debug(f"Errore caricamento file Italo: {str(e)}")
    return italo_codes

def trova_codici_stazione(nome_stazione):
    log_debug(f"Ricerca stazione: {nome_stazione}")
    codici = []
    try:
        with open(FILE_STAZIONI, 'r', encoding='utf-8') as file:
            for linea in file:
                if nome_stazione.lower() in linea.lower():
                    parts = linea.strip().rsplit(' ', 1)
                    if len(parts) == 2:
                        nome = parts[0].strip()
                        codice = parts[1].strip()
                        codici.append((nome, codice))
        log_debug(f"Trovate {len(codici)} stazioni")
    except Exception as e:
        log_debug(f"Errore lettura file stazioni: {str(e)}")
    return codici

def get_italo_station_code(station_name):
    italo_codes = load_italo_codes()
    return italo_codes.get(station_name, '')

# Gestione tastiere
def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🌦 METEO"), KeyboardButton("📰 NOTIZIE")],
        [KeyboardButton("🚉 TRENO")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def treno_menu_keyboard():
    keyboard = [
        [KeyboardButton("🚉 Infomobilità"), KeyboardButton("🚂 Traccia Treno")],
        [KeyboardButton("🔙 Menu principale")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def opzioni_treno_keyboard():
    keyboard = [
        [KeyboardButton("🚆 Partenze"), KeyboardButton("🚉 Arrivi")],
        [KeyboardButton("🔄 Entrambi")],
        [KeyboardButton("🔙 Indietro")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
    🌟 Benvenuto nel Bot Multifunzione! 🌟

🔍 Cosa posso fare per te?
- 🌦 Fornire previsioni meteo
- 📰 Mostrare ultime notizie
- 🚉 Cercare info sui treni

Usa i pulsanti per navigare!
    """
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

async def handle_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 Inserisci il nome della città:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Menu principale")]], resize_keyboard=True)
    )
    context.user_data['awaiting_city'] = True

async def handle_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        news_text = get_news()
        # Pulizia caratteri speciali per Markdown
        news_text = news_text.replace("*", "").replace("_", "").replace("[", "").replace("]", "")
        await update.message.reply_text(news_text, 
                                      parse_mode='HTML',  # Cambiato da Markdown a HTML
                                      disable_web_page_preview=True)
    except Exception as e:
        log_debug(f"Errore notizie: {str(e)}")
        await update.message.reply_text("❌ Errore nel recupero delle notizie")




async def handle_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.replace("📍 ", "")
    text, forecast_data = get_weather(city)

    if "❌" not in text:
        selected_date = datetime.datetime.today()
        img_path = generate_weather_image(forecast_data, city, selected_date)
        if img_path:
            with open(img_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo)
            os.remove(img_path)
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text)




    if text == "🔙 Menu principale":
        user_data.clear()
        await update.message.reply_text("🏠 Menu principale:", reply_markup=main_menu_keyboard())
        return

    if text == "🌦 METEO":
        await handle_weather(update, context)
    elif text == "📰 NOTIZIE":
        await handle_news(update)
    elif text == "🚉 TRENO":
        await update.message.reply_text("🚉 Scegli un servizio treni:", reply_markup=treno_menu_keyboard())
    elif text in ["🚉 Infomobilità", "🚂 Traccia Treno"]:
        await handle_treno(update, context)
    elif text in ["🚆 Partenze", "🚉 Arrivi", "🔄 Entrambi"]:
        await processa_scelta_treno(update, context, text.lower().replace("🔄", "entrambi"))
    elif user_data.get('awaiting_station'):
        await handle_station_input(update, context, text)
    elif user_data.get('awaiting_train'):
        await handle_train_input(update, context, text)
    elif 'train_results' in user_data:
        await handle_train_selection(update, context, text)
    else:
        await update.message.reply_text("❌ Comando non riconosciuto", reply_markup=main_menu_keyboard())


def date_selection_keyboard():
    date_buttons = generate_date_buttons()
    keyboard = [date_buttons[i:i+2] for i in range(0, len(date_buttons), 2)]
    keyboard.append([KeyboardButton("🔙 Menu principale")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def mostra_opzioni_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_debug("Mostra opzioni stazione (reply keyboard)")
    keyboard = [
        [KeyboardButton("🚆 Partenze"), KeyboardButton("🚉 Arrivi")],
        [KeyboardButton("🔄 Entrambi")],
        [KeyboardButton("🔙 Indietro")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("📋 Seleziona cosa visualizzare:", reply_markup=reply_markup)

async def processa_scelta_treno(update: Update, context: ContextTypes.DEFAULT_TYPE, tipo):
    log_debug(f"Processa scelta treno: {tipo}")
    codice = context.user_data.get('codice_stazione')
    station_name = context.user_data.get('nome_stazione', '')
    
    if not codice:
        log_debug("Nessuna stazione selezionata")
        await update.message.reply_text("❌ Nessuna stazione selezionata", reply_markup=main_menu_keyboard())
        return

    try:
        # Parte per Trenitalia
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
        data_attuale = now.strftime("%a %b %d %Y %H:%M:%S GMT+0100")
        messaggi_trenitalia = []
        
        if tipo == "entrambi":
            url_partenze = f"http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/partenze/{codice}/{data_attuale}"
            url_arrivi = f"http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/arrivi/{codice}/{data_attuale}"
            
            response_partenze = requests.get(url_partenze, timeout=10)
            response_arrivi = requests.get(url_arrivi, timeout=10)
            
            treni_partenze = response_partenze.json() if response_partenze.status_code == 200 else []
            treni_arrivi = response_arrivi.json() if response_arrivi.status_code == 200 else []
            
            if treni_partenze or treni_arrivi:
                messaggi_partenze = formatta_treni(treni_partenze, "partenze") if treni_partenze else []
                messaggi_arrivi = formatta_treni(treni_arrivi, "arrivi") if treni_arrivi else []
                if messaggi_partenze:
                    messaggi_trenitalia.extend(messaggi_partenze)
                if messaggi_arrivi:
                    messaggi_trenitalia.extend(messaggi_arrivi)
            else:
                await update.message.reply_text("⚠️ Nessun dato disponibile per partenze e arrivi", reply_markup=main_menu_keyboard())
        else:
            url = f"http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/{tipo}/{codice}/{data_attuale}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                treni = response.json()
                messaggi_trenitalia = formatta_treni(treni, tipo)
            else:
                await update.message.reply_text(f"⚠️ Nessun dato {tipo} disponibile", reply_markup=main_menu_keyboard())

        # Invia risultati Trenitalia
        if messaggi_trenitalia:
            await update.message.reply_text("🚅 <b>Risultati Trenitalia</b>", parse_mode='HTML')
            for msg in messaggi_trenitalia:
                await update.message.reply_text(msg, parse_mode='HTML')

        # Parte per Italo
        if station_name:
            try:
                italo_code = get_italo_station_code(station_name)
                url_italo = f"https://italoinviaggio.italotreno.com/api/RicercaStazioneService?&CodiceStazione={italo_code}&NomeStazione={station_name.replace(' ', '+')}"
                response_italo = requests.get(url_italo, timeout=10)
                
                if response_italo.status_code == 200:
                    italo_data = response_italo.json()
                    messaggi_italo = []
                    
                    if not italo_data.get('IsEmpty', True):
                        # Formattazione partenze
                        if tipo in ["partenze", "entrambi"]:
                            partenze = italo_data.get('ListaTreniPartenza', [])[:5]
                            if partenze:
                                header = "🚄 <b>ITALO - PARTENZE</b>\n\n"
                                current_msg = header
                                for treno in partenze:
                                    treno_info = (
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"  # Linea divisoria dopo ogni treno
                                        f"🔵 Treno {treno.get('Numero', 'N/A')} per {treno.get('DescrizioneLocalita', 'N/A')}\n"
                                        f"⏰ Orario: {treno.get('NuovoOrario', 'N/A')} "
                                        f"(Ritardo: {treno.get('Ritardo', 0)} min)\n"
                                        f"📌 Binario: {treno.get('Binario', 'N/A')}\n"
                                        f"ℹ️ {treno.get('Descrizione', '')}\n"
                                    )
                                    if len(current_msg) + len(treno_info) > 4000:
                                        messaggi_italo.append(current_msg)
                                        current_msg = header + treno_info
                                    else:
                                        current_msg += treno_info
                                if current_msg != header:
                                    messaggi_italo.append(current_msg)

                        # Formattazione arrivi
                        if tipo in ["arrivi", "entrambi"]:
                            arrivi = italo_data.get('ListaTreniArrivo', [])[:5]
                            if arrivi:
                                header = "🚄 <b>ITALO - ARRIVI</b>\n\n"
                                current_msg = header
                                for treno in arrivi:
                                    treno_info = (
                                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"  # Linea divisoria dopo ogni treno
                                        f"🔴 Treno {treno.get('Numero', 'N/A')} da {treno.get('DescrizioneLocalita', 'N/A')}\n"
                                        f"⏰ Orario: {treno.get('NuovoOrario', 'N/A')} "
                                        f"(Ritardo: {treno.get('Ritardo', 0)} min)\n"
                                        f"📌 Binario: {treno.get('Binario', 'N/A')}\n"
                                        f"ℹ️ {treno.get('Descrizione', '')}\n"
                                    )
                                    if len(current_msg) + len(treno_info) > 4000:
                                        messaggi_italo.append(current_msg)
                                        current_msg = header + treno_info
                                    else:
                                        current_msg += treno_info
                                if current_msg != header:
                                    messaggi_italo.append(current_msg)

                        # Invia risultati Italo
                        if messaggi_italo:
                            await update.message.reply_text("📡 <b>Risultati Italo</b>", parse_mode='HTML')
                            for msg in messaggi_italo:
                                await update.message.reply_text(msg, parse_mode='HTML')

            except Exception as e:
                log_debug(f"Errore recupero dati Italo: {str(e)}")
                await update.message.reply_text("⚠️ Servizio Italo temporaneamente non disponibile")

    except Exception as e:
        log_debug(f"Errore recupero dati: {str(e)}")
        await update.message.reply_text("❌ Errore recupero dati", reply_markup=main_menu_keyboard())

def formatta_treni(treni, tipo):
    log_debug("Formattazione treni")
    header = f"🚉 {'Partenze' if tipo == 'partenze' else 'Arrivi'}:\n\n"
    messaggi = []
    current_msg = header
    for treno in treni[:15]:
        treno_info = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"  # Linea divisoria dopo ogni treno
            f"🚆 Treno: {treno.get('compNumeroTreno', 'N/A')}\n"
            f"📍 {'Destinazione' if tipo == 'partenze' else 'Origine'}: {treno.get('destinazione' if tipo == 'partenze' else 'origine', 'N/A')}\n"
            f"⏰ Orario: {treno.get('compOrarioPartenza' if tipo == 'partenze' else 'compOrarioArrivo', 'N/A')}\n"
            f"🚨 Ritardo: {treno.get('compRitardo', ['N/A'])[0]}\n"
            f"📌 Binario: {treno.get('binarioProgrammatoPartenzaDescrizione' if tipo == 'partenze' else 'binarioProgrammatoArrivoDescrizione', 'N/A')}\n"
        )
        if len(current_msg) + len(treno_info) > 4000:
            messaggi.append(current_msg)
            current_msg = header + treno_info
        else:
            current_msg += treno_info
    if current_msg != header:
        messaggi.append(current_msg)
    return messaggi if messaggi else ["⚠️ Nessun treno disponibile"]

async def handle_train_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log_debug("=" * 40)
        log_debug("INIZIO TRACCIAMENTO TRENO")
        numero_treno = update.message.text.strip()
        
        if not numero_treno.isdigit():
            raise ValueError("Inserire solo numeri per il treno")

        # Ricerca su Viaggiatreno
        url_auto = f"http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/cercaNumeroTrenoTrenoAutocomplete/{numero_treno}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        
        log_debug(f"URL Viaggiatreno: {url_auto}")
        response = requests.get(url_auto, headers=headers, timeout=10)
        
        risultati = []
        if response.ok and response.text.strip():
            log_debug(f"Response Viaggiatreno: {response.text[:200]}...")
            for line in response.text.split('\n'):
                if not line.strip():
                    continue
                try:
                    display_part, data_part = line.split('|')
                    display_parts = display_part.split(' - ')
                    station_name = display_parts[1].strip() if len(display_parts) > 1 else "N/A"
                    treno, stazione, data = data_part.split('-')
                    risultati.append({
                        'display': f"Treno {station_name} - {treno}",
                        'data': (treno, stazione, data),
                        'timestamp': int(data)
                    })
                except Exception as e:
                    log_debug(f"Errore elaborazione riga: {line} - {str(e)}")
                    continue

        log_debug(f"Trovati {len(risultati)} risultati su Viaggiatreno")
        
        if not risultati:
            # Ricerca su Italo
            log_debug("Provo ricerca su Italo...")
            italo_url = f"https://italoinviaggio.italotreno.com/api/RicercaTrenoService?TrainNumber={numero_treno}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'Accept': 'application/json'
            }
            
            log_debug(f"URL Italo: {italo_url}")
            try:
                italo_response = requests.get(italo_url, headers=headers, timeout=15)
                log_debug(f"Status code Italo: {italo_response.status_code}")
                log_debug(f"Contenuto risposta: {italo_response.text[:500]}...")
                
                italo_response.raise_for_status()
                
                italo_data = italo_response.json()
                log_debug(f"Dati parsati: {json.dumps(italo_data, indent=2)}")
                
                if isinstance(italo_data, dict):
                    if italo_data.get('IsEmpty', True):
                        raise ValueError("Treno Italo non trovato nel sistema")
                    
                    message = format_italo_train_details(italo_data)
                    await invia_risposta(update, message)
                    return
                
                raise ValueError("Formato risposta Italo non riconosciuto")
                
            except requests.exceptions.RequestException as e:
                log_debug(f"Errore richiesta Italo: {str(e)}")
                raise ValueError("Servizio Italo non raggiungibile")
            except Exception as e:
                log_debug(f"Errore elaborazione Italo: {str(e)}\nDati: {italo_response.text}")
                raise ValueError("Dati Italo non validi o treno non trovato")

        # Gestione risultati multipli Viaggiatreno
        if len(risultati) > 1:
            risultati.sort(key=lambda x: x['timestamp'])
            keyboard = []
            for risultato in risultati:
                dt = datetime.datetime.fromtimestamp(risultato['timestamp'] / 1000)
                ora_formattata = dt.strftime("%d/%m %H:%M")
                keyboard.append([KeyboardButton(f"{risultato['display']} - {ora_formattata}")])
            keyboard.append([KeyboardButton("🔙 Indietro")])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("🔍 Sono stati trovati più treni:", reply_markup=reply_markup)
            context.user_data['train_results'] = risultati
            return

        # Singolo risultato
        if risultati:
            risultato = risultati[0]
            await processa_selezione_train_reply(update, context, risultato)
            return

        raise ValueError("Nessun treno trovato")

    except Exception as e:
        log_debug(f"ERRORE FINALE: {str(e)}")
        error_msg = f"❌ Errore: {str(e)}"
        await update.message.reply_text(error_msg, reply_markup=main_menu_keyboard())

async def invia_risposta(update: Update, message: str):
    keyboard = [[KeyboardButton("🔙 Indietro")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

def format_italo_train_details(italo_data):
    try:
        if not italo_data or italo_data.get('IsEmpty', True):
            return "🚅 Dettagli treno non disponibili"
        
        train_info = italo_data.get('TrainSchedule', {})
        last_update = italo_data.get('LastUpdate', 'N/A')

        main_info = {
            'numero': train_info.get('TrainNumber', 'N/A'),
            'origine': train_info.get('DepartureStationDescription', 'N/A'),
            'destinazione': train_info.get('ArrivalStationDescription', 'N/A'),
            'ritardo': train_info.get('Distruption', {}).get('DelayAmount', 0),
            'stato': "✅ In viaggio" if train_info.get('IsTrainRunning', False) else "⏳ Non partito",
            'last_update': last_update
        }

        partenza = train_info.get('StazionePartenza', {})
        orari_principali = [
            f"🚀 <b>Partenza:</b>\n"
            f"  ▪️ Effettiva: {partenza.get('ActualDepartureTime', 'N/A')}\n"
            f"  ▪️ Prevista: {partenza.get('EstimatedDepartureTime', 'N/A')}",
            
            f"\n🏁 <b>Arrivo finale:</b>\n"
            f"  ▪️ Effettivo: {train_info.get('Leg', {}).get('ActualArrivalTime', 'N/A')}\n"
            f"  ▪️ Previsto: {train_info.get('Leg', {}).get('EstimatedArrivalTime', 'N/A')}"
        ]

        def formatta_fermata(fermata, tipo):
            emoji = "🟢" if tipo == "Fermata" else "🔵"
            return (
                f"\n{emoji} <b>{fermata.get('LocationDescription', 'N/A')}</b>\n"
                f"  ├ Arrivo:\n"
                f"  │ ▪ Effettivo: {fermata.get('ActualArrivalTime', 'N/A')}\n"
                f"  │ ▪ Previsto: {fermata.get('EstimatedArrivalTime', 'N/A')}\n"
                f"  └ Partenza:\n"
                f"    ▪ Effettiva: {fermata.get('ActualDepartureTime', 'N/A')}\n"
                f"    ▪ Prevista: {fermata.get('EstimatedDepartureTime', 'N/A')}"
            )

        fermate_principali = [formatta_fermata(f, "Fermata") for f in train_info.get('StazioniFerme', [])]
        altre_fermate = [formatta_fermata(f, "Passaggio") for f in train_info.get('StazioniNonFerme', [])]

        messaggio = [
            f"🚄 <b>ITALO {main_info['numero']}</b> ━━━━━━━━━━━━━━━━━━",
            f"📍 <b>Percorso:</b> {main_info['origine']} → {main_info['destinazione']}",
            f"🚨 <b>Ritardo:</b> {main_info['ritardo']} minuti",
            f"📶 <b>Stato:</b> {main_info['stato']}",
            f"\n⏳ <b>ORARI PRINCIPALI</b> ━━━━━━━━━━━━━━━",
            *orari_principali,
            f"\n🛑 <b>FERMATE ({len(fermate_principali)})</b> ━━━━━━━━━━━━━",
            *fermate_principali,
            f"\n🚞 <b>PASSAGGI ({len(altre_fermate)})</b> ━━━━━━━━━━━━",
            *altre_fermate,
            f"\n\n🕒 <i>Ultimo aggiornamento: {main_info['last_update']}</i>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        return "\n".join(messaggio)
    
    except Exception as e:
        log_debug(f"ERRORE FORMATTAZIONE ITALO: {str(e)}")
        return "🚅 Treno Italo trovato!\n(Errore formattazione dati avanzati)"

async def processa_selezione_train_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, risultato):
    try:
        treno, stazione, data = risultato['data']
        url_dettagli = f"http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/andamentoTreno/{stazione}/{treno}/{data}"
        log_debug(f"URL dettagli treno: {url_dettagli}")
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url_dettagli, headers=headers, timeout=15)
        
        log_debug(f"Status code dettagli: {response.status_code}")
        response.raise_for_status()
        
        dati = response.json()
        log_debug(f"Dati treno parsati: {str(dati)[:500]}...")
        
        message = format_train_details(dati)
        await invia_risposta(update, message)
        context.user_data.pop('train_results', None)
    except Exception as e:
        log_debug(f"ERRORE SELEZIONE TRENO: {str(e)}")
        await update.message.reply_text("❌ Impossibile recuperare i dettagli del treno", reply_markup=main_menu_keyboard())

def format_train_details(dati):
    try:
        def converti_orario(ts):
            if not ts:
                return "--:--"
            try:
                dt = datetime.datetime.fromtimestamp(ts / 1000, tz=datetime.timezone(datetime.timedelta(hours=1)))
                return dt.strftime("%H:%M")
            except Exception as e:
                log_debug(f"Errore conversione timestamp {ts}: {str(e)}")
                return "ERR"
        
        messaggio = [
            f"🚂 <b>Treno {dati.get('numeroTreno', 'N/A')}</b>",
            f"📍 Direzione: {dati.get('destinazione', 'N/A')}",
            f"⏳ Ritardo complessivo: {dati.get('ritardo', 0)} minuti",
            "---------------------------------"
        ]
        
        for i, fermata in enumerate(dati.get('fermate', [])):
            stazione = fermata.get('stazione', 'N/A')
            parte = [f"\n🏁 <b>{stazione}</b>"]
            
            if i == 0:
                parte.extend([
                    f"Partenza programmata: {converti_orario(fermata.get('programmata'))}",
                    f"Partenza effettiva: {converti_orario(fermata.get('effettiva'))}",
                    f"Binario: {fermata.get('binarioEffettivoPartenzaDescrizione', fermata.get('binarioProgrammatoPartenzaDescrizione', '--'))}"
                ])
            else:
                parte.extend([
                    f"Arrivo programmato: {converti_orario(fermata.get('programmata'))}",
                    f"Arrivo effettivo: {converti_orario(fermata.get('effettiva'))}",
                    f"Binario arrivo: {fermata.get('binarioEffettivoArrivoDescrizione', fermata.get('binarioProgrammatoArrivoDescrizione', '--'))}"
                ])
                
                if fermata.get('partenza_teorica'):
                    parte.extend([
                        f"Partenza programmata: {converti_orario(fermata.get('partenza_teorica'))}",
                        f"Partenza effettiva: {converti_orario(fermata.get('partenzaReale'))}",
                        f"Binario partenza: {fermata.get('binarioEffettivoPartenzaDescrizione', fermata.get('binarioProgrammatoPartenzaDescrizione', '--'))}"
                    ])

            messaggio.append("\n".join(parte))
        
        return "\n".join(messaggio[:40])
    except Exception as e:
        log_debug(f"ERRORE FORMATTAZIONE: {str(e)}")
        return "⚠️ Errore nella visualizzazione dei dettagli del treno"

async def rispondi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    log_debug(f"Messaggio ricevuto: {user_input}")
    user_data = context.user_data

    # Gestione input città per meteo
    if user_data.get('awaiting_city'):
        user_data.pop('awaiting_city')
        user_data['current_city'] = user_input
        
        await update.message.reply_text(
            f"🌤️ Seleziona il giorno per {user_input}:",
            reply_markup=date_selection_keyboard()
        )
        return

    # Gestione selezione data
    if any(user_input.startswith(x) for x in ('☀️', '🌙')) or (user_input[0].isdigit() and ('current_city' in user_data or 'awaiting_city' in user_data)):
        if 'current_city' not in user_data:
            await update.message.reply_text("❌ Seleziona prima una città", reply_markup=main_menu_keyboard())
            return

        # Trova l'indice del giorno selezionato
        buttons = generate_date_buttons()
        day_index = next((i for i, btn in enumerate(buttons) if btn.text == user_input), None)

        if day_index is not None:
            text, forecast_data = get_weather(user_data['current_city'], day_index)
            if "❌" in text:
                await update.message.reply_text(text)
                return

            selected_date = datetime.datetime.now() + datetime.timedelta(days=day_index)
            img_path = generate_weather_image(forecast_data, user_data['current_city'], selected_date.date())
            
            if img_path:
                with open(img_path, 'rb') as photo:
                    await update.message.reply_photo(photo=photo)
                os.remove(img_path)
            
            await update.message.reply_text(
                text, 
                parse_mode='Markdown', 
                reply_markup=date_selection_keyboard()
            )
        return


    # Gestione comandi principali
    if user_input == "🔙 Menu principale":
        user_data.clear()
        await update.message.reply_text("🏠 Menu principale:", reply_markup=main_menu_keyboard())
        return

    if user_input == "🌦 METEO":
        await handle_weather(update, context)
        return

    if user_input == "📰 NOTIZIE":
        await handle_news(update, context)
        return

    if user_input == "🚉 TRENO":
        await update.message.reply_text("🚉 Scegli un servizio treni:", reply_markup=treno_menu_keyboard())
        return

    if user_input == "🚉 Infomobilità":
        context.user_data['awaiting_station_name'] = True
        await update.message.reply_text(
            "📌 Inserisci il nome della stazione:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Indietro")]], resize_keyboard=True)
        )
        return

    if user_input == "🚂 Traccia Treno":
        context.user_data['awaiting_train_number'] = True
        await update.message.reply_text(
            "🚂 Inserisci il numero del treno:",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Indietro")]], resize_keyboard=True)
        )    
        return

    if context.user_data.get('awaiting_station_name'):
        context.user_data.pop('awaiting_station_name')
        codici = trova_codici_stazione(user_input)
        if not codici:
            await update.message.reply_text("❌ Nessuna stazione trovata", reply_markup=main_menu_keyboard())
            return
        if len(codici) == 1:
            context.user_data['codice_stazione'] = codici[0][1]
            context.user_data['nome_stazione'] = codici[0][0]  # Salva nome stazione per Italo
            await mostra_opzioni_reply(update, context)
        else:
            context.user_data['stations_list'] = codici
            keyboard = []
            for nome, codice in codici:
                keyboard.append([KeyboardButton(f"{nome} - {codice}")])
            keyboard.append([KeyboardButton("🔙 Indietro")])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("🔍 Seleziona stazione:", reply_markup=reply_markup)
        return

    if context.user_data.get('stations_list'):
        stations = context.user_data['stations_list']
        for nome, codice in stations:
            if user_input == f"{nome} - {codice}":
                context.user_data['codice_stazione'] = codice
                context.user_data['nome_stazione'] = nome  # Salva nome stazione per Italo
                context.user_data.pop('stations_list')
                await mostra_opzioni_reply(update, context)
                return
        await update.message.reply_text("❌ Selezione non valida. Riprova o premi 🔙 Indietro per annullare.", reply_markup=main_menu_keyboard())
        return

    if context.user_data.get('awaiting_train_number'):
        context.user_data.pop('awaiting_train_number')
        await handle_train_number(update, context)
        return

    if context.user_data.get('train_results'):
        for risultato in context.user_data['train_results']:
            dt = datetime.datetime.fromtimestamp(risultato['timestamp'] / 1000)
            ora_formattata = dt.strftime("%d/%m %H:%M")
            expected_text = f"{risultato['display']} - {ora_formattata}"
            if user_input == expected_text:
                await processa_selezione_train_reply(update, context, risultato)
                return
        await update.message.reply_text("❌ Selezione non valida. Riprova o premi 🔙 Indietro per annullare.", reply_markup=main_menu_keyboard())
        return

    option_mapping = {
        "🚆 Partenze": "partenze",
        "🚉 Arrivi": "arrivi",
        "🔄 Entrambi": "entrambi"
    }
    if user_input in option_mapping:
        tipo = option_mapping[user_input]
        await processa_scelta_treno(update, context, tipo)
        return

    await update.message.reply_text("❌ Comando non riconosciuto. Usa i pulsanti.", reply_markup=main_menu_keyboard())

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, rispondi))
    log_debug("Bot avviato correttamente")
    application.run_polling()

if __name__ == '__main__':
    main()