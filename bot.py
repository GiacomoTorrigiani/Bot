import requests
from urllib.parse import quote
import time

BASE_URL = "http://www.viaggiatreno.it/infomobilitamobile/resteasy/viaggiatreno/autocompletaStazione/{city}?q={city}"

def get_stations(city):
    try:
        encoded_city = quote(city.upper())
        url = BASE_URL.format(city=encoded_city)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/plain, */*'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        stations = []
        for line in response.text.split('\n'):
            if '|' in line:
                name, code = line.strip().split('|')
                stations.append(f"{name.title()} {code}")
        
        return stations

    except Exception as e:
        print(f"Errore per {city}: {str(e)}")
        return []

def main():
    cities = [
        "Agrigento", "Alessandria", "Ancona", "Aosta", "Arezzo", "Ascoli Piceno", "Asti", 
        "Avellino", "Bari", "Barletta", "Belluno", "Benevento", "Bergamo", "Biella", 
        "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", 
        "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", 
        "Cremona", "Crotone", "Cuneo", "Enna", "Ferrara", "Firenze", "Foggia", "Forlì", 
        "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "l`aquila", 
        "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", 
        "Mantova", "Massa", "Matera", "Messina", "Milano", "Modena", "Napoli", "Novara", 
        "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro", 
        "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", 
        "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", 
        "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", 
        "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", 
        "Udine", "Varese", "Venezia", "Verbano Cusio Ossola", "Vercelli", "Verona", 
        "Vibo Valentia", "Vicenza", "Viterbo"
    ]
    
    with open("stazioni.txt", "w", encoding="utf-8") as f:
        for city in cities:
            stations = get_stations(city)
            if stations:
                f.write(f"\n=== {city.upper()} ===\n")
                f.write("\n".join(stations) + "\n")
                print(f"Trovate {len(stations)} stazioni per {city}")
            else:
                print(f"Nessun risultato per {city}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()
