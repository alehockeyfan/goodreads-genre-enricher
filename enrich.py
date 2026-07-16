import pandas as pd
import requests
import time
import os
import glob
import re

def clean_isbn(isbn):
    if pd.isna(isbn):
        return ""
    # Rimuove tutto ciò che non è un numero (es. lettere, virgolette, uguali)
    cleaned = re.sub(r'\D', '', str(isbn))
    return cleaned if len(cleaned) in [10, 13] else ""

def get_genres_google_books(isbn, title, author):
    """Cerca i generi su Google Books."""
    if isbn:
        query = f"isbn:{isbn}"
    else:
        # Pulisce titolo e autore per la ricerca
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
        print(f"  [Google] Errore di connessione per {title}: {e}")
    return []

def get_genres_open_library(isbn):
    """Cerca i generi su Open Library come backup (funziona solo con ISBN)."""
    if not isbn:
        return []
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=data&format=json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            book_key = f"ISBN:{isbn}"
            if book_key in data:
                subjects = data[book_key].get("subjects", [])
                if subjects:
                    # Estrae i nomi dei soggetti (generi) limitandosi ai primi 3
                    return [s.get("name") for s in subjects[:3]]
    except Exception as e:
        print(f"  [OpenLibrary] Errore di connessione: {e}")
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
    
    df = pd.read_csv(input_file)
    genres_column = []
    
    for idx, row in df.iterrows():
        title = row.get('Title', 'Unknown Title')
        author = row.get('Author', 'Unknown Author')
        
        # Estrazione e pulizia dell'ISBN
        isbn13 = clean_isbn(row.get('ISBN13'))
        isbn10 = clean_isbn(row.get('ISBN'))
        isbn = isbn13 if isbn13 else isbn10
        
        print(f"[{idx+1}/{len(df)}] {title} (ISBN: {isbn or 'N/A'})...")
        
        # 1. Tentativo con Google Books
        found_genres = get_genres_google_books(isbn, title, author)
        
        # 2. Tentativo con Open Library (se Google fallisce ed esiste un ISBN)
        if not found_genres and isbn:
            print("  -> Google vuoto, provo Open Library...")
            found_genres = get_genres_open_library(isbn)
            
        if found_genres:
            genre_str = ", ".join(found_genres)
            print(f"  -> Generi trovati: {genre_str}")
            genres_column.append(genre_str)
        else:
            print("  -> Nessun genere trovato.")
            genres_column.append("Unknown")
            
        # Pausa di 1 secondo per rispettare i limiti delle API ed evitare ban di IP
        time.sleep(1.0)
        
    df['Genres'] = genres_column
    df.to_csv(output_file, index=False)
    print(f"\nFatto! File salvato in: {output_file}")

if __name__ == "__main__":
    enrich_goodreads_export()
