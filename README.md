# Sistema Taxinomía: Editor Visual de Ontologías y Taxonomías

## Descripción General

Taxinomía es una aplicación web avanzada diseñada para crear, visualizar y gestionar taxonomías y ontologías de manera intuitiva. La interfaz permite construir estructuras jerárquicas visualmente, enriquecerlas con metadatos y propiedades, y exportarlas a formatos estándar como OWL (Web Ontology Language) para su uso en sistemas semánticos.

## Características Principales

- **Editor visual de taxonomías**: Interfaz intuitiva para crear estructuras jerárquicas
- **Gestión de metadatos**: Añade información descriptiva a cada nodo
- **Sistema de propiedades**: Define y asigna propiedades a los elementos
- **Exportación a OWL**: Convierte tus estructuras a formatos estándar de ontologías
- **Visualización jerárquica**: Representa visualmente las relaciones entre conceptos
- **Interfaz de arrastrar y soltar**: Manipulación sencilla de nodos y propiedades
- **Edición YAML/JSON**: Acceso directo al código subyacente

## Estructura del Sistema

### 1. Interfaz Principal

- **Panel de visualización piramidal**: Muestra los nodos organizados jerárquicamente
- **Panel de información**: Muestra y edita detalles del nodo seleccionado
- **Panel de propiedades**: Gestiona la asignación de propiedades a los nodos
- **Editor de metadatos**: Permite añadir pares clave-valor a cualquier nodo
- **Visualizador YAML/JSON**: Muestra y permite editar la representación textual

### 2. Componentes Funcionales

- **Sistema de navegación**: Permite recorrer la estructura jerárquica
- **Motor de drag & drop**: Facilita la reorganización visual de la taxonomía
- **Conversor YAML/JSON**: Transforma entre formatos de representación
- **API de exportación OWL**: Envía la taxonomía para su conversión a OWL

### 3. Almacenamiento de Datos

- **Modelo de nodos**: Estructura para almacenar la jerarquía de conceptos
- **Diccionario de metadatos**: Almacena información adicional por nodo
- **Registro de propiedades**: Mantiene las propiedades asignadas a cada nodo

## Posibilidades para la Creación de Ontologías

### Modelado Conceptual

- **Definición de clases y subclases**: Crea jerarquías de conceptos organizados en taxonomías
- **Establecimiento de relaciones**: Define conexiones entre diferentes conceptos mediante propiedades
- **Anotación semántica**: Añade metadatos descriptivos para enriquecer cada concepto

### Integración con Estándares Semánticos

- **Exportación a OWL**: Convierte automáticamente tus taxonomías a Web Ontology Language
- **Compatibilidad con razonadores**: Estructuras diseñadas para funcionar con motores de inferencia
- **Representación en RDF**: Facilita la integración con la web semántica

### Características Avanzadas

- **Definición de propiedades jerárquicas**: Crea estructuras de propiedades con sus propias taxonomías
- **Asignación de valores a propiedades**: Define no solo la estructura sino también los valores específicos
- **Visualización personalizada**: Adapta la representación visual a las necesidades específicas del dominio

## Uso del Sistema para Ontologías

### 1. Creación de la Estructura Jerárquica

1. Define los conceptos principales en el primer nivel
2. Añade subconceptos mediante la creación de nodos hijo
3. Organiza la jerarquía arrastrando y soltando elementos

### 2. Enriquecimiento Semántico

1. Selecciona un nodo para ver su panel de información
2. Añade metadatos (definiciones, notas, referencias)
3. Asigna propiedades desde el panel de propiedades

### 3. Exportación y Uso

1. Visualiza la representación YAML/JSON de tu ontología
2. Exporta a OWL para su uso en sistemas de razonamiento semántico
3. Integra con otras ontologías o sistemas de gestión del conocimiento

## Ventajas para el Desarrollo de Ontologías

- **Reducción de la curva de aprendizaje**: No requiere conocimientos avanzados en lenguajes de ontología
- **Feedback visual inmediato**: Visualiza la estructura mientras la desarrollas
- **Enfoque incremental**: Comienza con taxonomías simples y evoluciona hacia ontologías complejas
- **Validación integrada**: Detecta inconsistencias en la estructura jerárquica
- **Colaboración facilitada**: Interfaz intuitiva accesible para expertos de dominio sin conocimientos técnicos

## Requisitos Técnicos

- Navegador web moderno con soporte para JavaScript ES6+
- Conexión a Internet para la exportación a OWL (requiere API en http://localhost:8000)
- Se recomienda una resolución mínima de 1366x768 para una experiencia óptima

## Instalación

1. Clona el repositorio
2. Abre el archivo `SEMINARIO/v6/index.html` en tu navegador
3. Para la funcionalidad completa de exportación OWL, asegúrate de tener en ejecución el servidor API
