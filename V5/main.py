from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
from typing import Optional
import os
import json
import requests
import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
async def upload_json(request: Request, url: str = Form(...)):
    try:
        # Obtener y verificar el token o información del usuario
        form_data = await request.form()
        user_data = form_data.get("user_data")
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")
        
        # Convertir la cadena JSON a diccionario
        user = json.loads(user_data)
        
        # Verificar si es superusuario
        if not user.get('is_superuser'):
            raise HTTPException(status_code=403, detail="Acceso no autorizado: Se requiere ser superusuario")

        # Proceder con la carga del JSON si es superusuario
        response = requests.get(url)
        if response.status_code == 200:
            json_data = response.json()
            
            # Obtener el primer elemento que no sea 'id'
            first_key = next((key for key in json_data.keys() if key != 'id'), None)
            if not first_key:
                first_key = "default"  # En caso de que no haya elementos o solo haya 'id'
            first_value = json_data[first_key]
            
            # Crear un nombre de archivo basado en el primer elemento
            safe_name = str(first_value)[:30] if not isinstance(first_value, dict) else first_key
            safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in safe_name).strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"{safe_name}_{timestamp}.json"
            
            # Crear path para guardar el JSON
            base_path = "user_folders"
            user_folder = os.path.join(base_path, user['username'])
            
            # Verificar que la carpeta existe
            if not os.path.exists(user_folder):
                raise HTTPException(status_code=400, detail="Carpeta de usuario no encontrada")
            
            json_path = os.path.join(user_folder, json_filename)
            
            # Guardar el JSON en la carpeta del usuario
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True, 
                "data": json_data,
                "saved_path": json_path
            }
        else:
            raise HTTPException(status_code=400, detail="No se pudo obtener el JSON de la URL")
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Error al procesar la información del usuario")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

# Crear las carpetas al iniciar la aplicación
@app.on_event("startup")
async def startup_event():
    create_user_directories()
