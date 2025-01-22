import csv
import json
from pathlib import Path
import re
import unicodedata

def normalize_string(text):
    """Normaliza un string manteniendo ñ y tildes para mostrar, pero eliminándolas para IDs."""
    # Convertir 'ñ' a 'n' y eliminar tildes para el ID
    id_text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    id_text = id_text.replace('ñ', 'n')
    return re.sub(r'[^a-z0-9]+', '_', id_text.lower()).strip('_')

def extract_hierarchy(element, parent_path=""):
    """Extrae la jerarquía recursivamente y genera IDs únicos."""
    items = []
    
    if isinstance(element, dict):
        for key, value in element.items():
            current_path = f"{parent_path}/{key}" if parent_path else key
            id = normalize_string(key)
            gist_url = f"https://gist.github.com/user/leximus_{id}"
            
            items.append({
                'name': key,  # Mantiene tildes y ñ para mostrar
                'id': id,     # Version normalizada para URLs
                'path': current_path,
                'gist_url': gist_url
            })
            
            # Procesar elementos hijos
            if isinstance(value, (dict, list)):
                items.extend(extract_hierarchy(value, current_path))
    
    elif isinstance(element, list):
        for item in element:
            if isinstance(item, (dict, list)):
                items.extend(extract_hierarchy(item, parent_path))
            else:
                id = normalize_string(str(item))
                current_path = f"{parent_path}/{item}"
                gist_url = f"https://gist.github.com/user/leximus_{id}"
                
                items.append({
                    'name': item,
                    'id': id,
                    'path': current_path,
                    'gist_url': gist_url
                })
    
    return items

def generate_html_page(item):
    """Genera una página HTML individual para cada elemento."""
    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LexiMus - {item['name']}</title>
    <link rel="icon" type="image/svg+xml" href="https://raw.githubusercontent.com/iccmu/LexiMus/main/static/LexiMus-Logo-Horiizontal.svg">
</head>
<body>
    <h1>{item['name']}</h1>
    <p>ID: {item['id']}</p>
    <p>Path: {item['path']}</p>
    <p>Gist URL: <a href="{item['gist_url']}" target="_blank">{item['gist_url']}</a></p>
</body>
</html>
"""
    return html_template

def main():
    # Crear directorio de salida
    output_dir = Path("leximus_pages")
    output_dir.mkdir(exist_ok=True)
    
    # Cargar la jerarquía desde un archivo JSON
    with open('clases.json', 'r', encoding='utf-8') as f:
        hierarchy = json.load(f)
    
    # Extraer todos los elementos
    items = extract_hierarchy(hierarchy)
    
    # Guardar la información en CSV
    with open('leximus_mapping.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'id', 'path', 'gist_url'])
        writer.writeheader()
        writer.writerows(items)
    
    # Generar páginas HTML individuales
    for item in items:
        html_content = generate_html_page(item)
        html_file = output_dir / f"{item['id']}.html"
        html_file.write_text(html_content, encoding='utf-8')
    
    print(f"Generados {len(items)} archivos HTML en {output_dir}")
    print(f"Archivo de mapeo guardado como leximus_mapping.csv")

if __name__ == "__main__":
    main()
