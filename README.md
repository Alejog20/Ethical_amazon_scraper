# Enhanced Amazon Scraper

Este es un script avanzado de web scraping en Python diseñado para extraer datos de productos de Amazon de manera resiliente y eficiente. El proyecto demuestra el uso de múltiples estrategias de evasión, manejo de sesiones y extracción de datos robusta.

## ⚠️ Descargo de Responsabilidad y Uso Ético

**Este proyecto fue creado únicamente con fines educativos y para demostrar habilidades avanzadas de programación.**

- **Uso bajo su propio riesgo:** Este software se proporciona "TAL CUAL", sin garantía de ningún tipo. El autor no se hace responsable de ningún daño o reclamación que surja del uso de este script.
- **Responsabilidad del usuario:** Los usuarios de este código son los únicos responsables de asegurarse de no violar los Términos de Servicio del sitio web al que decidan apuntar. Se recomienda encarecidamente revisar los Términos de Servicio de Amazon antes de usar esta herramienta.
- **Scraping ético:** El script incluye deliberadamente retrasos entre las solicitudes para evitar sobrecargar los servidores del sitio web. Se ruega a los usuarios que utilicen esta herramienta de manera considerada y responsable.

## ✨ Características Principales

- **Estrategia Multi-enfoque:** Utiliza varias sesiones (`cloudscraper` para escritorio, una sesión móvil y una de API) para maximizar las posibilidades de éxito.
- **Pruebas Adaptativas:** Realiza una prueba inicial para determinar qué métodos de scraping funcionan antes de lanzar la búsqueda principal.
- **Extracción Robusta:** Emplea una lista de múltiples selectores CSS para adaptarse a los cambios en el diseño de la página de Amazon.
- **Persistencia de Datos:** Guarda los resultados en una base de datos SQLite para evitar duplicados y permitir análisis posteriores.
- **Exportación de Datos:** Permite exportar los resultados a un archivo CSV.

## 🚀 Uso

### 1. Prerrequisitos
- Python 3.10 o superior.
- `uv` (o `pip`) para la gestión de paquetes.

### 2. Instalación

Clona el repositorio y navega al directorio del proyecto. Luego, instala las dependencias. Si el proyecto ya tiene un archivo `pyproject.toml` con las dependencias listadas, puedes instalar todo con:

```bash
# Usando uv
uv pip sync

O si estás configurando el proyecto por primera vez:

```bash

uv pip install requests beautifulsoup4 pandas cloudscraper
```

### 3. Ejecución

Para iniciar el script, ejecuta el siguiente comando en tu terminal:

```bash
python main.py
```
#### El script te pedirá el producto que deseas buscar y el número de páginas a extraer.

### 📄 Licencia
Este proyecto está bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.