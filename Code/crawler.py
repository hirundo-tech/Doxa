import os, json, requests, shutil
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

def doxa_crawler(url, folder_name="DATA"):
    data_dir = Path(folder_name)
    
    # 1. PULIZIA: Elimina la cartella se esiste per ripartire da zero
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"[!] Errore connessione: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    extracted_data = {}

    # Estrazione dati (Tabelle/Strong)
    for row in soup.find_all(['div', 'tr']):
        strong = row.find('strong')
        if strong:
            label = strong.get_text(strip=True).replace(":", "")
            value = strong.next_sibling
            if not value or not value.strip():
                value = strong.parent.get_text(strip=True).replace(strong.get_text(strip=True), "")
            if label and value.strip():
                extracted_data[label] = value.strip()

    # 2. DOWNLOAD: Gestione duplicati e numerazione
    downloaded_urls = set() # Evita di scaricare due volte lo stesso URL
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/allegato/' in href and '.pdf' in href.lower():
            pdf_url = urljoin(url, href)
            
            # Salta se abbiamo già processato questo identico link
            if pdf_url in downloaded_urls:
                continue
            
            # Determina il nome base del file
            base_name = pdf_url.split('/')[-1].split('?')[0]
            if not base_name.endswith('.pdf'): base_name += ".pdf"
            
            # 3. NUMERAZIONE: Se il nome esiste già (ma l'URL è diverso), aggiungi un numero
            final_path = data_dir / base_name
            counter = 1
            while final_path.exists():
                name_stem = Path(base_name).stem
                final_path = data_dir / f"{name_stem} ({counter}).pdf"
                counter += 1
            
            try:
                pdf_res = requests.get(pdf_url, headers=headers)
                with open(final_path, 'wb') as f:
                    f.write(pdf_res.content)
                print(f"[*] Scaricato: {final_path.name}")
                downloaded_urls.add(pdf_url)
            except Exception as e:
                print(f"[!] Errore su {pdf_url}: {e}")

    with open(data_dir / "info_data.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    
    return extracted_data
