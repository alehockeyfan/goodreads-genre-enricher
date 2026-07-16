import pandas as pd
import requests
import time
import os
import glob
import re
from bs4 import BeautifulSoup

def clean_isbn(isbn):
    if pd.isna(isbn):
        return ""
    cleaned = re.sub(r'\D', '', str(isbn))
    return cleaned if len(cleaned) in [10, 13] else ""

def get_genres_from_goodreads_web(isbn, title, author):
    """
    Tenta di fare scraping "leggero" direttamente su Goodreads usando l'ISBN 
    o cercando il libro tramite titolo e autore se l'ISBN manca.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }
    
    # Se abbiamo l'ISBN cerchiamo direttamente la pagina del libro
    if isbn:
        search_url = f"https://www.goodreads.com/search?q={isbn}"
    else:
        clean_title = re.sub(r'[^\w\s]', '', title)
        clean_author = re.sub(r'[^\w\s]', '', author)
        search_url = f"https://www.goodreads.com/search?q={clean_title}+{clean_author}"
        
    try:
        # 1. Richiedi la pagina (Goodreads spesso reindirizza direttamente alla pagina del libro se cerchi l'ISBN)
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Estraiamo gli "shelves" popolari direttamente dalla pagina del libro su Goodreads
            # (Su Goodreads i generi sono rappresentati come "scaffali" in cui gli utenti inseriscono i libri)
            genres = []
            
            # Cerca i link che puntano ai generi (es. /genres/romance o /shelf/show/fantasy)
            genre_elements = soup.find_all('a', href=re.compile(r'/(genres|shelf/show)/'))
            for element in genre_elements:
                genre_name = element.get_text().strip()
                # Filtriamo i tag di sistema inutili o troppo generici
                if genre_name and genre_name.lower() not in ['to-read', 'currently-reading', 'owned', 'default', 'books', 'ebook', 'kindle', 'read']:
                    if genre_name not in genres:
                        genres.append(genre_name)
                        
            if genres:
                return genres[:3] # Prendiamo solo i primi 3 generi più rilevanti
    except Exception as e:
        print(f"  [Goodreads Web] Errore: {e}")
    return []

def get_genres_google_books(isbn, title, author):
    if isbn:
        query = f"isbn:{isbn}"
    else:
        clean_title = re.sub(r'[^\w\s]', '', title)
        clean_author = re.sub(r'[^\w\s]', '', author)
        query = f"intitle:{clean_title}+inauthor:{clean_author}"
        
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "items" in data:
                volume_info = data["items"][0].get("volumeInfo", {})
                categories = volume_info.get("categories", [])
                if categories:
                    return [c.strip() for c in categories]
    except Exception as e:
        pass
    return []

def find_input_file():
    csv_files = glob.glob("*.csv")
    valid_files = [f for f in csv_files if f != "goodreads_enriched.csv"]
    if not valid_files:
        return None
    return max(valid_files, key=os.path.getmtime)

def enrich_goodreads_export():
    input_file = find_input_file()
    if not input_file:
        print("Errore: Nessun file CSV trovato!")
        return
        
    output_file = "goodreads_enriched.csv"
    print(f"File rilevato: {input_file}. Avvio recupero generi...")
    
    # Carichiamo BeautifulSoup per lo scraping leggero
    df = pd.read_csv(input_file)
    genres_column = []
    
    for idx, row in df.iterrows():
        title = row.get('Title', 'Unknown Title')
        author = row.get('Author', 'Unknown Author')
        
        isbn13 = clean_isbn(row.get('ISBN13'))
        isbn10 = clean_isbn(row.get('ISBN'))
        isbn = isbn13 if isbn13 else isbn10
        
        print(f"[{idx+1}/{len(df)}] {title}...")
        
        # 1. Tentativo con Google Books (veloce e senza blocchi)
        found_genres = get_genres_google_books(isbn, title, author)
        
        # 2. Fallback: Scraping diretto della pagina Goodreads (per self-publishing e nicchie)
        if not found_genres:
            print("  -> Google vuoto, tento il recupero diretto da Goodreads...")
            found_genres = get_genres_from_goodreads_web(isbn, title, author)
            
        if found_genres:
            genre_str = ", ".join(found_genres)
            print(f"  -> Generi trovati: {genre_str}")
            genres_column.append(genre_str)
        else:
            print("  -> Nessun genere trovato.")
            genres_column.append("Unknown")
            
        # Pausa di 1.5 secondi per non sovraccaricare Goodreads ed evitare blocchi IP
        time.sleep(1.5)
        
    df['Genres'] = genres_column
    df.to_csv(output_file, index=False)
    print(f"\nFatto! File salvato in: {output_file}")

if __name__ == "__main__":
    enrich_goodreads_export()
