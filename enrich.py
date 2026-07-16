import pandas as pd
import requests
import time
import os

def get_genres_google_books(isbn, title, author):
    query = f"isbn:{isbn}" if pd.notna(isbn) and str(isbn).strip() != "" else f"intitle:{title}+inauthor:{author}"
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "items" in data:
                volume_info = data["items"][0].get("volumeInfo", {})
                categories = volume_info.get("categories", [])
                if categories:
                    return ", ".join(categories)
    except Exception as e:
        print(f"Errore per {title}: {e}")
    return "Unknown"

def enrich_goodreads_export(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Errore: Il file {input_file} non esiste!")
        return
        
    df = pd.read_csv(input_file)
    print(f"Trovati {len(df)} libri. Recupero generi...")
    genres = []
    
    for idx, row in df.iterrows():
        isbn = row.get('ISBN13') if pd.notna(row.get('ISBN13')) else row.get('ISBN')
        if isinstance(isbn, str):
            isbn = ''.join(filter(str.isdigit, isbn))
            
        title = row['Title']
        author = row['Author']
        
        print(f"[{idx+1}/{len(df)}] {title}...")
        genre = get_genres_google_books(isbn, title, author)
        genres.append(genre)
        time.sleep(0.5)
        
    df['Genres'] = genres
    df.to_csv(output_file, index=False)
    print(f"File arricchito salvato in: {output_file}")

if __name__ == "__main__":
    enrich_goodreads_export("goodreads_export.csv", "goodreads_enriched.csv")
