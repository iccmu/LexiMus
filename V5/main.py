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
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

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

# Función auxiliar para contar elementos en un objeto anidado
def count_elements(obj):
    """Cuenta recursivamente el número de elementos en un objeto anidado."""
    if not isinstance(obj, dict):
        return 1
    
    count = 0
    for key, value in obj.items():
        if isinstance(value, dict):
            count += count_elements(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    count += count_elements(item)
                else:
                    count += 1
        else:
            count += 1
    
    return count

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
            # También buscar en subcarpetas de usuarios creados por este superusuario
            folders_to_search = [user_folder]
            for subdir in os.listdir(user_folder):
                subdir_path = os.path.join(user_folder, subdir)
                if os.path.isdir(subdir_path):
                    folders_to_search.append(subdir_path)
        else:
            # Si es usuario normal, usar la carpeta de su creador y su propia subcarpeta
            creator_folder = os.path.join(base_path, user['created_by'])
            user_folder = os.path.join(creator_folder, username)
            folders_to_search = [user_folder]
        
        json_files = []
        
        for folder in folders_to_search:
            if not os.path.exists(folder):
                continue
                
            for filename in os.listdir(folder):
                if filename.endswith('.json'):
                    file_path = os.path.join(folder, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                            
                            # Verificar que json_data no sea None y sea un diccionario
                            if json_data is None or not isinstance(json_data, dict):
                                display_value = "Formato no válido"
                                first_key = "Error"
                            else:
                                # Obtener el primer elemento que no sea 'id'
                                first_key = next((key for key in json_data.keys() if key != 'id'), None)
                                
                                if first_key:
                                    first_value = json_data[first_key]
                                    if isinstance(first_value, dict):
                                        # Contar elementos recursivamente
                                        num_elements = count_elements(first_value)
                                        display_value = f"{num_elements} elementos"
                                    else:
                                        display_value = str(first_value)
                                else:
                                    display_value = "Sin elementos"
                            
                            json_files.append({
                                "filename": filename,
                                "path": file_path,
                                "first_element": f"{first_key if first_key else 'Sin clave'}: {display_value}"
                            })
                    except Exception as e:
                        # Si hay un error al leer un archivo, continuar con el siguiente
                        print(f"Error al leer {file_path}: {str(e)}")
                        # Añadir el archivo con información de error
                        json_files.append({
                            "filename": filename,
                            "path": file_path,
                            "first_element": f"Error: {str(e)[:50]}..."
                        })
                        continue
        
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
                    
                    # Verificar que el JSON sea un objeto
                    if json_data is None or not isinstance(json_data, dict):
                        # Si no es un objeto, devolver un objeto con información sobre el error
                        return {
                            "error": "Formato no válido",
                            "original_content": json_data,
                            "message": "El archivo JSON no contiene un objeto válido"
                        }
                    
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

def generate_uuid():
    return str(uuid4())

def add_uuids_to_object(obj):
    """Añade UUIDs a un objeto de forma recursiva si no los tiene."""
    if not isinstance(obj, dict):
        return obj
    
    # Añadir ID al objeto actual si no tiene
    if 'id' not in obj:
        obj['id'] = generate_uuid()
    
    # Procesar recursivamente todos los valores que son diccionarios
    for key, value in obj.items():
        if isinstance(value, dict):
            obj[key] = add_uuids_to_object(value)
        elif isinstance(value, list):
            obj[key] = [add_uuids_to_object(item) if isinstance(item, dict) else item 
                       for item in value]
    
    return obj

@app.post("/save-taxonomy/{filename}")
async def save_taxonomy(filename: str, request: Request):
    try:
        # Obtener el YAML convertido a JSON de la solicitud
        data = await request.json()
        
        # Añadir UUIDs a todos los objetos que no los tengan
        data_with_uuids = add_uuids_to_object(data)
        
        # Buscar el archivo en todas las carpetas de usuario
        base_path = "user_folders"
        file_path = None
        
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Guardar el JSON actualizado con los UUIDs
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_with_uuids, f, indent=2, ensure_ascii=False)
        
        # Devolver el JSON actualizado con los UUIDs para actualizar el frontend
        return {
            "message": "Taxonomía guardada correctamente",
            "data": data_with_uuids
        }
        
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

@app.post("/save-rdf/{filename}")
async def save_rdf(filename: str, request: Request):
    try:
        # Obtener el JSON de la solicitud
        data = await request.json()
        json_data = data.get('json')
        relations_data = data.get('relations', [])  # Obtener las relaciones definidas
        
        if not json_data:
            raise HTTPException(status_code=400, detail="No se proporcionó contenido JSON")
        
        print("JSON recibido:", json_data)  # Debug
        print("Relaciones recibidas:", relations_data)  # Debug
        
        # Obtener el nombre base del archivo sin extensión
        base_filename = filename.rsplit('.', 1)[0]
        owl_filename = f"{base_filename}.owl"
        
        # Buscar la carpeta del usuario
        base_path = "user_folders"
        owl_file_path = None
        
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                owl_file_path = os.path.join(root, owl_filename)
                print(f"Path encontrado: {owl_file_path}")  # Debug
                break
        
        if not owl_file_path:
            raise HTTPException(status_code=404, detail="No se encontró el directorio del usuario")
        
        try:
            # Crear un grafo RDF
            g = Graph()
            
            # Definir namespaces
            onto = Namespace("http://www.semanticweb.org/ontology#")
            g.bind("owl", OWL)
            g.bind("rdfs", RDFS)
            g.bind("rdf", RDF)
            g.bind("xsd", XSD)
            g.bind("", onto)
            
            # Crear la ontología
            ontology = URIRef("")
            g.add((ontology, RDF.type, OWL.Ontology))
            
            # Diccionario para almacenar las clases creadas (para referencias posteriores)
            classes = {}
            
            # Procesar el JSON y crear las clases y propiedades
            def process_json_to_owl(data, parent=None):
                for key, value in data.items():
                    if key == 'id':
                        continue
                        
                    # Crear clase
                    class_uri = onto[key.replace(" ", "_")]
                    g.add((class_uri, RDF.type, OWL.Class))
                    g.add((class_uri, RDFS.label, Literal(key)))
                    
                    # Guardar referencia a la clase
                    classes[key] = class_uri
                    
                    # Añadir subclase si hay padre
                    if parent:
                        g.add((class_uri, RDFS.subClassOf, parent))
                    
                    # Procesar hijos recursivamente
                    if isinstance(value, dict):
                        process_json_to_owl(value, class_uri)
            
            # Procesar el JSON para crear la jerarquía de clases
            process_json_to_owl(json_data)
            
            # Procesar las relaciones definidas
            for relation in relations_data:
                source_class = relation.get('source')
                target_class = relation.get('target')
                relation_type = relation.get('type')
                relation_name = relation.get('name', 'hasRelation')
                
                if source_class in classes and target_class in classes:
                    source_uri = classes[source_class]
                    target_uri = classes[target_class]
                    
                    # Crear la propiedad de objeto para la relación
                    relation_uri = onto[relation_name.replace(" ", "_")]
                    
                    # Definir el tipo de relación
                    if relation_type == 'objectProperty':
                        # Propiedad de objeto estándar
                        g.add((relation_uri, RDF.type, OWL.ObjectProperty))
                        g.add((relation_uri, RDFS.label, Literal(relation_name)))
                        g.add((relation_uri, RDFS.domain, source_uri))
                        g.add((relation_uri, RDFS.range, target_uri))
                    
                    elif relation_type == 'equivalentClass':
                        # Clases equivalentes
                        g.add((source_uri, OWL.equivalentClass, target_uri))
                    
                    elif relation_type == 'disjointWith':
                        # Clases disjuntas
                        g.add((source_uri, OWL.disjointWith, target_uri))
                    
                    elif relation_type == 'inverseOf':
                        # Propiedades inversas
                        inverse_relation_uri = onto[f"inverse_{relation_name}".replace(" ", "_")]
                        g.add((inverse_relation_uri, RDF.type, OWL.ObjectProperty))
                        g.add((inverse_relation_uri, RDFS.label, Literal(f"inverse of {relation_name}")))
                        g.add((relation_uri, OWL.inverseOf, inverse_relation_uri))
                        g.add((inverse_relation_uri, RDFS.domain, target_uri))
                        g.add((inverse_relation_uri, RDFS.range, source_uri))
                    
                    elif relation_type == 'symmetricProperty':
                        # Propiedad simétrica
                        g.add((relation_uri, RDF.type, OWL.ObjectProperty))
                        g.add((relation_uri, RDF.type, OWL.SymmetricProperty))
                        g.add((relation_uri, RDFS.label, Literal(relation_name)))
                        g.add((relation_uri, RDFS.domain, source_uri))
                        g.add((relation_uri, RDFS.range, target_uri))
                    
                    elif relation_type == 'transitiveProperty':
                        # Propiedad transitiva
                        g.add((relation_uri, RDF.type, OWL.ObjectProperty))
                        g.add((relation_uri, RDF.type, OWL.TransitiveProperty))
                        g.add((relation_uri, RDFS.label, Literal(relation_name)))
                        g.add((relation_uri, RDFS.domain, source_uri))
                        g.add((relation_uri, RDFS.range, target_uri))
                    
                    # Restricciones de cardinalidad si están definidas
                    min_cardinality = relation.get('minCardinality')
                    max_cardinality = relation.get('maxCardinality')
                    
                    if min_cardinality is not None or max_cardinality is not None:
                        # Crear una restricción
                        restriction_node = URIRef(f"_:restriction_{source_class}_{relation_name}_{target_class}")
                        g.add((restriction_node, RDF.type, OWL.Restriction))
                        g.add((restriction_node, OWL.onProperty, relation_uri))
                        
                        if min_cardinality is not None:
                            g.add((restriction_node, OWL.minCardinality, 
                                  Literal(min_cardinality, datatype=XSD.nonNegativeInteger)))
                        
                        if max_cardinality is not None:
                            g.add((restriction_node, OWL.maxCardinality, 
                                  Literal(max_cardinality, datatype=XSD.nonNegativeInteger)))
                        
                        # Añadir la restricción como subclase
                        g.add((source_uri, RDFS.subClassOf, restriction_node))
            
            # Serializar a OWL/XML
            owl_content = g.serialize(format='pretty-xml')
            
            # Guardar el archivo
            with open(owl_file_path, 'w', encoding='utf-8') as f:
                f.write(owl_content)
            
            return {
                "message": "Archivo OWL guardado correctamente",
                "path": owl_file_path
            }
            
        except Exception as e:
            print(f"Error en el procesamiento OWL: {str(e)}")  # Debug
            raise HTTPException(status_code=400, detail=f"Error en el procesamiento OWL: {str(e)}")
        
    except Exception as e:
        print(f"Error general: {str(e)}")  # Debug
        raise HTTPException(status_code=500, detail=str(e))

# Añadir una nueva ruta para gestionar relaciones
@app.get("/manage-relations/{filename}", response_class=HTMLResponse)
async def manage_relations(request: Request, filename: str):
    return templates.TemplateResponse("manage-relations.html", {"request": request})

# Endpoint para obtener las clases disponibles para crear relaciones
@app.get("/api/classes/{filename}")
async def get_classes(filename: str):
    try:
        # Buscar el archivo en todas las carpetas de usuario
        base_path = "user_folders"
        file_path = None
        
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Leer el JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Extraer las clases del JSON
        classes = []
        
        def extract_classes(data, path=""):
            for key, value in data.items():
                if key == 'id':
                    continue
                
                current_path = f"{path}.{key}" if path else key
                classes.append(current_path)
                
                if isinstance(value, dict):
                    extract_classes(value, current_path)
        
        extract_classes(json_data)
        
        return {"classes": classes}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
