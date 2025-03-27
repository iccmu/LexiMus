from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from typing import Dict, Any, Optional

app = FastAPI()

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OntologyData(BaseModel):
    """Modelo para los datos de la ontología en formato JSON"""
    # Este modelo debe adaptarse a la estructura de tu JSON
    # Aquí usamos Dict[str, Any] para aceptar cualquier estructura JSON
    __root__: Dict[str, Any]

@app.post("/convert-to-owl")
async def convert_to_owl(data: Dict[str, Any]):
    try:
        # Aquí iría tu lógica para convertir el JSON a OWL
        # Por ejemplo, usando owlready2, rdflib u otra biblioteca
        
        # Ejemplo simplificado:
        filename = "ontology.owl"
        output_path = f"./static/{filename}"
        
        # Guardar el JSON recibido (para depuración)
        with open("received_data.json", "w") as f:
            json.dump(data, f, indent=2)
        
        # Aquí implementarías la conversión real a OWL
        # ...
        
        # Simular la creación de un archivo OWL
        with open(output_path, "w") as f:
            f.write("<!-- Archivo OWL generado desde JSON -->")
        
        # Devolver la URL para descargar el archivo
        download_url = f"/static/{filename}"
        
        return JSONResponse({
            "status": "success",
            "message": "Ontología OWL generada correctamente",
            "filename": filename,
            "download_url": download_url
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al convertir a OWL: {str(e)}")

# Para servir archivos estáticos (como los OWL generados)
from fastapi.staticfiles import StaticFiles

# Crear directorio static si no existe
os.makedirs("./static", exist_ok=True)

# Montar el directorio static
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)