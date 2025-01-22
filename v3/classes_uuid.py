import json
import uuid
import csv
import re
import unicodedata
import os
import html
import hashlib

def normalize_for_url(text):
    # Eliminar acentos
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    # Convertir a minúsculas
    text = text.lower()
    # Reemplazar caracteres especiales y espacios con guion bajo
    text = re.sub(r'[^\w\s-]', '_', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text

def get_safe_filename(url_path):
    # Si la ruta es más larga que 100 caracteres, usar un hash MD5
    if len(url_path) > 100:
        return hashlib.md5(url_path.encode('utf-8')).hexdigest()
    return url_path

def create_html_file(url_path, original_path, uuid_value):
    # Crear el contenido del HTML
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(original_path)}</title>
</head>
<body>
    <h1>{html.escape(original_path)}</h1>
    <p>UUID: {uuid_value}</p>
    <p>URL-friendly path: {url_path}</p>
</body>
</html>"""
    
    # Asegurar que el directorio existe
    os.makedirs('leximus_clases', exist_ok=True)
    
    # Obtener un nombre de archivo seguro
    safe_filename = get_safe_filename(url_path)
    
    # Crear el archivo HTML
    file_path = os.path.join('leximus_clases', f"{safe_filename}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def extract_paths(data, current_path="", paths=None):
    if paths is None:
        paths = []
    
    if isinstance(data, dict):
        # Obtener el UUID del nodo actual si existe
        current_uuid = data.get("id", "")
        
        for key, value in data.items():
            if key != "id" and key != "value":
                new_path = f"{current_path}/{key}" if current_path else key
                url_friendly_path = normalize_for_url(new_path)
                paths.append((new_path, url_friendly_path, current_uuid))
                # Crear archivo HTML para esta entrada
                create_html_file(url_friendly_path, new_path, current_uuid)
                extract_paths(value, new_path, paths)
    
    return paths

def add_uuids(data):
    if isinstance(data, dict):
        # Crear un nuevo diccionario con ID
        new_dict = {"id": str(uuid.uuid4())}
        
        # Si el diccionario está vacío o solo contiene null
        if not data:
            new_dict["value"] = None
            return new_dict
            
        # Procesar cada elemento del diccionario
        for key, value in data.items():
            if value is None:
                # Si el valor es null, crear un objeto con id y value
                new_dict[key] = {
                    "id": str(uuid.uuid4()),
                    "value": None
                }
            else:
                # Si el valor es otro diccionario, procesarlo recursivamente
                new_dict[key] = add_uuids(value)
                
        return new_dict
    return data

# Leer el archivo JSON original
with open('clases.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Transformar los datos
transformed_data = add_uuids(data)

# Guardar el resultado en un nuevo archivo
with open('clases_with_uuids.json', 'w', encoding='utf-8') as file:
    json.dump(transformed_data, file, ensure_ascii=False, indent=2)

# Extraer las rutas y generar el CSV y los archivos HTML
paths = extract_paths(transformed_data)

# Guardar las rutas en un archivo CSV
with open('paths.csv', 'w', encoding='utf-8', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Original Path', 'URL-friendly Path', 'UUID'])
    writer.writerows(paths)

print(f"Se han creado {len(paths)} archivos HTML en la carpeta 'leximus_clases'")