import csv
import json
from pathlib import Path
import re

def normalize_string(text):
    """Normaliza el texto para crear IDs válidos."""
    return re.sub(r'[^a-z0-9]+', '_', str(text).lower()).strip('_')

def extract_hierarchy(element, parent_path=""):
    """Extrae la jerarquía recursivamente y genera IDs únicos."""
    items = []
    
    if isinstance(element, dict):
        for key, value in element.items():
            current_path = f"{parent_path}/{key}" if parent_path else key
            id = normalize_string(key)
            page_url = f"https://raw.githubusercontent.com/iccmu/LexiMus/refs/heads/main/v3/leximus_pages/{id}.html"
            
            items.append({
                'name': key,
                'id': id,
                'path': current_path,
                'page_url': page_url
            })
            
            if isinstance(value, (dict, list)):
                items.extend(extract_hierarchy(value, current_path))
    
    elif isinstance(element, list):
        for item in element:
            if isinstance(item, (dict, list)):
                items.extend(extract_hierarchy(item, parent_path))
            else:
                id = normalize_string(str(item))
                current_path = f"{parent_path}/{item}"
                page_url = f"https://raw.githubusercontent.com/iccmu/LexiMus/refs/heads/main/v3/leximus_pages/{id}.html"
                
                items.append({
                    'name': item,
                    'id': id,
                    'path': current_path,
                    'page_url': page_url
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
    <p>URL: <a href="{item['page_url']}" target="_blank">{item['page_url']}</a></p>
    
    <!-- Aquí puedes añadir más información específica de la clase -->
    
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
        writer = csv.DictWriter(f, fieldnames=['name', 'id', 'path', 'page_url'])
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
