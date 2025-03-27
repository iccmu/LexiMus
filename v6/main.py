from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

app = FastAPI()

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para el mensaje JSON-OWL
class OwlMessage(BaseModel):
    content: str
    # Puedes añadir más campos específicos para JSON-OWL si es necesario
    ontology_type: str = None
    properties: dict = None

@app.post("/api/owl")
async def receive_owl_message(message: OwlMessage):
    # Procesar el mensaje JSON-OWL
    print(f"Mensaje OWL recibido: {message.content}")
    print(f"Tipo de ontología: {message.ontology_type}")
    print(f"Propiedades: {message.properties}")
    
    # Aquí puedes implementar la lógica para procesar la ontología
    
    # Devolver una respuesta
    return {
        "status": "success", 
        "message": f"Mensaje OWL procesado: {message.content}",
        "processed_data": {
            "ontology_type": message.ontology_type,
            "properties_count": len(message.properties) if message.properties else 0
        }
    }

@app.get("/")
async def root():
    return {"message": "API JSON-OWL funcionando correctamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
