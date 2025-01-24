from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import csv
import json
from pydantic import BaseModel
from typing import List, Optional
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar archivos estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=".")

# Modelos de datos
class User(BaseModel):
    username: str
    password: str
    is_superuser: bool = False
    created_by: str = None

class CSVSaveRequest(BaseModel):
    content: str
    username: str
    is_superuser: bool

# Funciones de utilidad para manejar users.csv
def read_users():
    try:
        with open('users.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            users = list(reader)
            logger.info(f"Read {len(users)} users from CSV")
            return users
    except Exception as e:
        logger.error(f"Error reading users: {str(e)}")
        # Crear archivo con superusuarios por defecto
        superusers = [
            {"username": "admin1", "password": "admin1", "is_superuser": "True", "created_by": "system"},
            {"username": "admin2", "password": "admin2", "is_superuser": "True", "created_by": "system"},
            {"username": "admin3", "password": "admin3", "is_superuser": "True", "created_by": "system"}
        ]
        write_users(superusers)
        return superusers

def write_users(users):
    try:
        with open('users.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["username", "password", "is_superuser", "created_by"])
            writer.writeheader()
            writer.writerows(users)
            logger.info("Users written to CSV successfully")
    except Exception as e:
        logger.error(f"Error writing users: {str(e)}")

# Función para crear carpetas de superusuarios
def ensure_superuser_folders():
    try:
        users = read_users()
        # Primero crear las carpetas de superusuarios
        superusers = {user["username"]: user for user in users if user["is_superuser"] == "True"}
        
        for superuser in superusers.values():
            superuser_folder = os.path.join('static', f'{superuser["username"]}@main.py')
            if not os.path.exists(superuser_folder):
                os.makedirs(superuser_folder, exist_ok=True)
                logger.info(f"Created directory for superuser: {superuser_folder}")
            else:
                logger.info(f"Directory already exists for superuser: {superuser_folder}")
        
        # Luego crear las subcarpetas de usuarios regulares
        for user in users:
            if user["is_superuser"] == "False" and user["created_by"] in superusers:
                creator_folder = os.path.join('static', f'{user["created_by"]}@main.py')
                user_subfolder = os.path.join(creator_folder, user["username"])
                
                if not os.path.exists(user_subfolder):
                    os.makedirs(user_subfolder, exist_ok=True)
                    logger.info(f"Created subfolder for regular user: {user_subfolder}")
                else:
                    logger.info(f"Subfolder already exists for regular user: {user_subfolder}")
                    
    except Exception as e:
        logger.error(f"Error ensuring user folders: {str(e)}")

# Verificar y crear carpetas de superusuarios al iniciar
@app.on_event("startup")
async def startup_event():
    logger.info("Checking and creating superuser folders...")
    ensure_superuser_folders()

# Rutas
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/users")
async def get_users():
    users = read_users()
    return {"users": users}

@app.post("/api/users")
async def create_user(user: User):
    # Verificar que el creador existe y es superusuario
    users = read_users()
    creator = next((u for u in users if u["username"] == user.created_by), None)
    
    if not creator or creator["is_superuser"] != "True":
        raise HTTPException(
            status_code=403, 
            detail="Only superusers can create new users"
        )
    
    # Verificar si el usuario ya existe
    if any(u["username"] == user.username for u in users):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Agregar nuevo usuario
    new_user = {
        "username": user.username,
        "password": user.password,
        "is_superuser": str(user.is_superuser),
        "created_by": user.created_by
    }
    users.append(new_user)
    write_users(users)

    # Crear carpeta según el tipo de usuario
    try:
        if user.is_superuser:
            # Si es superusuario, crear su carpeta en static
            user_folder = os.path.join('static', f'{user.username}@main.py')
            os.makedirs(user_folder, exist_ok=True)
            logger.info(f"Created directory for new superuser: {user_folder}")
        else:
            # Si es usuario regular, crear su carpeta dentro de la carpeta del creador
            creator_folder = os.path.join('static', f'{user.created_by}@main.py')
            user_subfolder = os.path.join(creator_folder, user.username)
            os.makedirs(user_subfolder, exist_ok=True)
            logger.info(f"Created subfolder for new regular user: {user_subfolder}")
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}")
    
    return {
        "message": "User created successfully",
        "folder_created": True
    }

@app.post("/api/login")
async def login(user: User):
    logger.info(f"Login attempt for user: {user.username}")
    users = read_users()
    logger.info(f"Users in database: {users}")
    
    for stored_user in users:
        if stored_user["username"] == user.username:
            logger.info("Username matched")
            if stored_user["password"] == user.password:
                logger.info("Password matched")
                return {
                    "success": True,
                    "is_superuser": stored_user["is_superuser"] == "True",
                    "username": user.username
                }
            else:
                logger.info("Password did not match")
    
    logger.info("No matching user found")
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Opcional: Manejar favicon.ico
@app.get('/favicon.ico')
async def favicon():
    return HTTPException(status_code=404)

@app.post("/api/save-csv")
async def save_csv(request: CSVSaveRequest):
    try:
        # Determinar la ruta de guardado según el tipo de usuario
        if request.is_superuser:
            base_path = os.path.join('static', f'{request.username}@main.py')
            file_path = os.path.join(base_path, 'main.csv')  # Archivo principal para superusuarios
        else:
            # Encontrar el superusuario que creó este usuario
            users = read_users()
            user_info = next((u for u in users if u["username"] == request.username), None)
            if not user_info:
                raise HTTPException(status_code=404, detail="User not found")
            
            base_path = os.path.join('static', f'{user_info["created_by"]}@main.py', request.username)
            file_path = os.path.join(base_path, 'validated.csv')  # CSV normal para usuarios regulares

        # Asegurar que la carpeta existe
        os.makedirs(base_path, exist_ok=True)

        # Para superusuarios, verificar si ya existe un CSV principal
        if request.is_superuser and os.path.exists(file_path):
            # Si existe, eliminarlo antes de guardar el nuevo
            os.remove(file_path)
            logger.info(f"Existing main CSV removed for superuser {request.username}")

        # Guardar el archivo CSV
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        logger.info(f"CSV saved successfully for user {request.username} at {file_path}")
        return {
            "message": "CSV saved successfully", 
            "path": file_path,
            "is_main_csv": request.is_superuser
        }

    except Exception as e:
        logger.error(f"Error saving CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/main-csv/{username}")
async def get_main_csv(username: str):
    try:
        # Verificar que el usuario es un superusuario
        users = read_users()
        user = next((u for u in users if u["username"] == username), None)
        if not user or user["is_superuser"] != "True":
            raise HTTPException(status_code=403, detail="Only superusers can have main CSV")
        
        file_path = os.path.join('static', f'{username}@main.py', 'main.csv')
        if not os.path.exists(file_path):
            return {"exists": False}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "exists": True,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error reading main CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/main-csv/{username}")
async def delete_main_csv(username: str):
    try:
        # Verificar que el usuario es un superusuario
        users = read_users()
        user = next((u for u in users if u["username"] == username), None)
        if not user or user["is_superuser"] != "True":
            raise HTTPException(status_code=403, detail="Only superusers can delete main CSV")
        
        file_path = os.path.join('static', f'{username}@main.py', 'main.csv')
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Main CSV deleted for superuser {username}")
            return {"message": "Main CSV deleted successfully"}
        else:
            return {"message": "No main CSV found"}
            
    except Exception as e:
        logger.error(f"Error deleting main CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
