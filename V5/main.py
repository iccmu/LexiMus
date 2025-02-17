from fastapi import FastAPI, Request, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
from typing import Optional
import os
import json
import requests
import datetime
from uuid import uuid4
from pathlib import Path

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

PROPERTIES_FILE = "user_folders/props.json"

def create_user_directories():
    # Leer el CSV
    df = pd.read_csv('users.csv')
    base_path = "user_folders"
    
    # Crear el directorio base si no existe
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # Primero crear todas las carpetas de superusuarios en el directorio raíz
    for _, user in df.iterrows():
        if bool(user['is_superuser']):
            user_path = os.path.join(base_path, user['username'])
            if not os.path.exists(user_path):
                os.makedirs(user_path)
                print(f"Creado directorio para superusuario: {user_path}")
    
    # Luego crear las carpetas de usuarios normales dentro de sus respectivos creadores
    for _, user in df.iterrows():
        if not bool(user['is_superuser']):
            # Encontrar el path del creador
            creator_path = os.path.join(base_path, user['created_by'])
            if os.path.exists(creator_path):
                user_path = os.path.join(creator_path, user['username'])
                if not os.path.exists(user_path):
                    os.makedirs(user_path)
                    print(f"Creado directorio para usuario: {user_path}")

# Función para verificar las credenciales
def verify_user(username: str, password: str) -> Optional[dict]:
    df = pd.read_csv('users.csv')
    user = df[df['username'] == username]
    if not user.empty and user.iloc[0]['password'] == password:
        return {
            'username': username,
            'is_superuser': bool(user.iloc[0]['is_superuser']),
            'created_by': user.iloc[0]['created_by']
        }
    return None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = verify_user(username, password)
    if user:
        return {"success": True, "user": user, "redirect": "/dashboard"}
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

@app.post("/upload-json")
async def upload_json(
    file: Optional[UploadFile] = None,
    url: Optional[str] = Form(None),
    user_data: str = Form(...)
):
    try:
        user = json.loads(user_data)
        
        # Determinar la ruta correcta basada en el tipo de usuario
        base_path = "user_folders"
        df = pd.read_csv('users.csv')
        user_info = df[df['username'] == user['username']].iloc[0]
        
        if bool(user_info['is_superuser']):
            # Si es superusuario, usar su propia carpeta
            save_folder = os.path.join(base_path, user['username'])
        else:
            # Si es usuario normal, usar la carpeta de su creador
            save_folder = os.path.join(base_path, user_info['created_by'], user['username'])
        
        # Crear directorio si no existe
        os.makedirs(save_folder, exist_ok=True)
        
        # Procesar archivo o URL
        if file:
            # Leer contenido del archivo
            content = await file.read()
            json_data = json.loads(content)
            filename = file.filename
        elif url:
            # Descargar JSON de la URL
            response = requests.get(url)
            response.raise_for_status()
            json_data = response.json()
            filename = url.split('/')[-1] or 'downloaded.json'
        else:
            raise HTTPException(status_code=400, detail="Se requiere un archivo o URL")

        # Asegurarse de que el archivo termine en .json
        if not filename.endswith('.json'):
            filename += '.json'

        # Guardar el JSON en la ubicación correcta
        save_path = os.path.join(save_folder, filename)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        return JSONResponse({
            "message": "JSON guardado correctamente",
            "saved_path": save_path,
            "data": json_data
        })

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error al descargar el JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list-jsons/{username}")
async def list_jsons(username: str):
    try:
        base_path = "user_folders"
        
        # Leer el CSV para obtener información del usuario
        df = pd.read_csv('users.csv')
        user = df[df['username'] == username].iloc[0]
        is_superuser = bool(user['is_superuser'])
        
        if is_superuser:
            # Si es superusuario, usar su propia carpeta
            user_folder = os.path.join(base_path, username)
        else:
            # Si es usuario normal, usar la carpeta de su creador
            user_folder = os.path.join(base_path, user['created_by'])
        
        if not os.path.exists(user_folder):
            return {"files": [], "message": "No se encontraron archivos"}
        
        def count_elements(obj):
            if isinstance(obj, dict):
                count = 0
                for value in obj.values():
                    count += count_elements(value)
                return max(1, count)  # Contar al menos 1 para diccionarios no vacíos
            elif isinstance(obj, list):
                return sum(count_elements(item) for item in obj)
            else:
                return 0
        
        json_files = []
        for filename in os.listdir(user_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(user_folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    # Obtener el primer elemento que no sea 'id'
                    first_key = next((key for key in json_data.keys() if key != 'id'), None)
                    if first_key:
                        first_value = json_data[first_key]
                        if isinstance(first_value, dict):
                            # Contar elementos recursivamente
                            num_elements = count_elements(first_value)
                            display_value = f"{num_elements} elementos"
                        else:
                            display_value = first_value
                    else:
                        display_value = "Sin elementos"
                    
                    json_files.append({
                        "filename": filename,
                        "path": file_path,
                        "first_element": f"{first_key}: {display_value}"
                    })
        
        return {"files": json_files}
    except Exception as e:
        return {"files": [], "message": str(e)}

@app.get("/get-json-content/{filename}")
async def get_json_content(filename: str, request: Request):
    try:
        base_path = "user_folders"
        
        # Buscar el archivo en todas las carpetas de usuario
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    return json_data
        
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/edit-json/{filename}", response_class=HTMLResponse)
async def edit_json(request: Request, filename: str):
    return templates.TemplateResponse("edit-json.html", {"request": request})

@app.get("/add-taxonomy/{filename}", response_class=HTMLResponse)
async def add_taxonomy(request: Request, filename: str):
    return templates.TemplateResponse("add-taxonomy.html", {"request": request})

@app.post("/update-json/{filename}")
async def update_json(filename: str, request: Request):
    try:
        data = await request.json()
        json_content = data.get('content')
        username = data.get('user')
        
        # Validar el JSON
        try:
            json_data = json.loads(json_content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON inválido")
        
        # Buscar el archivo en todas las carpetas de usuario
        base_path = "user_folders"
        file_found = False
        
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                file_found = True
                break
        
        if not file_found:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        return {"message": "JSON actualizado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-taxonomy/{filename}")
async def save_taxonomy(filename: str, request: Request):
    try:
        # Obtener el JSON-LD de la solicitud
        json_ld = await request.json()
        
        # Obtener el JSON actual
        base_path = "user_folders"
        file_path = None
        
        # Buscar el archivo en todas las carpetas de usuario
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Leer el JSON actual
        with open(file_path, 'r', encoding='utf-8') as f:
            current_json = json.load(f)
        
        # Añadir o actualizar la sección de taxonomías
        if '@context' not in current_json:
            current_json['@context'] = json_ld['@context']
        
        if 'taxonomies' not in current_json:
            current_json['taxonomies'] = []
        
        # Añadir la nueva taxonomía
        current_json['taxonomies'].append(json_ld)
        
        # Guardar el JSON actualizado
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(current_json, f, indent=2, ensure_ascii=False)
        
        return {"message": "Taxonomía guardada correctamente"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Función para descargar y guardar las librerías
def download_libraries():
    # Crear directorio static/js si no existe
    static_js_path = Path("static/js")
    static_js_path.mkdir(parents=True, exist_ok=True)
    
    # Definir las librerías necesarias
    libraries = {
        "vis-network.min.js": "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js",
        "js-yaml.min.js": "https://cdnjs.cloudflare.com/ajax/libs/js-yaml/4.1.0/js-yaml.min.js"
    }
    
    for filename, url in libraries.items():
        file_path = static_js_path / filename
        
        # Descargar solo si el archivo no existe
        if not file_path.exists():
            try:
                print(f"Descargando {filename}...")
                response = requests.get(url)
                response.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"✓ {filename} descargado correctamente")
            except Exception as e:
                print(f"Error descargando {filename}: {str(e)}")

@app.on_event("startup")
async def startup_event():
    create_user_directories()
    download_libraries()

# Funciones auxiliares para manejar las propiedades
def load_properties():
    try:
        with open(PROPERTIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convertir la estructura jerárquica a lista plana de propiedades
            properties = []
            def process_node(node, parent_id=None):
                if isinstance(node, dict):
                    node_id = node.get('id')
                    for key, value in node.items():
                        if key != 'id' and isinstance(value, dict):
                            properties.append({
                                "id": value.get('id'),
                                "name": key,
                                "type": "object" if "value" not in value else "string",
                                "parent": parent_id
                            })
                            process_node(value, value.get('id'))
            
            process_node(data)
            return properties
    except FileNotFoundError:
        return []

def save_properties(properties):
    # Convertir la lista plana de propiedades a estructura jerárquica
    root = {"id": "root-family-123"}
    
    def build_hierarchy(props, parent_id=None):
        node = {}
        children = [p for p in props if p["parent"] == parent_id]
        for child in children:
            child_node = {"id": child["id"]}
            if child["type"] == "string":
                child_node["value"] = None
            else:
                child_node.update(build_hierarchy(props, child["id"]))
            node[child["name"]] = child_node
        return node
    
    hierarchy = build_hierarchy(properties)
    root.update(hierarchy)
    
    with open(PROPERTIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(root, f, indent=2, ensure_ascii=False)

# Añadir las nuevas rutas
@app.get("/property-hierarchy", response_class=HTMLResponse)
async def property_hierarchy(request: Request):
    return templates.TemplateResponse("property-hierarchy.html", {"request": request})

@app.get("/api/properties")
async def get_properties():
    return load_properties()

@app.post("/api/properties")
async def create_property(request: Request):
    try:
        property_data = await request.json()
        properties = load_properties()
        
        new_property = {
            "id": str(uuid4()),
            "name": property_data["name"],
            "type": property_data["type"],
            "parent": property_data["parent"]
        }
        
        properties.append(new_property)
        save_properties(properties)
        
        return new_property
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/properties/{property_id}")
async def delete_property(property_id: str):
    try:
        properties = load_properties()
        properties = [p for p in properties if p["id"] != property_id]
        save_properties(properties)
        return {"message": "Propiedad eliminada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
