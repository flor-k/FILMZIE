# FILMZIE

 **Autora**: Florencia Kania

 Este es el proyecto para entregar como prueba tecnica a BB Media

# CONSIGNA

## Objetivo:
 - Obtener todas las películas y series. Obtener la metadata de cada contenido: título, año, sinopsis, link, duración (solo para movies).
 - Guardar la información obtenida en una base de datos, en archivo .json o .csv automáticamente (dejar subido un ejemplo en el repositorio).
 - Imprimir el tiempo de ejecución en el script e indicarlo en el entregable de alguna manera.

## Plus:
 - Episodios de cada serie.
 - Metadata de los episodios.
 - Si es posible obtener mas información/metadata por cada contenido.
 - Identificar modelo de negocio.
 - Tiempo de ejecución menor a 2hs.
 - Analisis y/o limpieza de Metadata.
 - Otros que consideren relevante.
 - Sitio a realizar el scraping: https://filmzie.com/home

## Fecha límite para entrega: 
 - 14/05/2024 hasta las 18:00hrs.

## Requisitos:    
 - Tenes la libertad de utilizar la librería que quieras para realizarlo.
 - Subir a GitHub el script trabajado junto con un archivo de los resultados que se obtienen al correr el script creado (JSON, xlsx, csv, etc).

## Notas
 - No se grabando todos los metadatos para no sobrecargar los archivos ni la base de datos. La estructura actual de metadatos que se graba por cada contenido audiovisual (pelicula o serie) es la siguiente:
   ```
    {
     "duration": int,  # En minutos
     "titulo": str,
     "categorias": list:str,
     "anio": str,  # No utilizo la ñ para evitar conflictos de codificación
     "sinopsis": str,
     "actores": list:str,
     "directores": list:str,
     "studio": str,
     "tipo": "TV_SHOW" o "MOVIE", #str
     "videoId": str,   #None en caso de ser una serie
     "links": list:{"file":str}, #None en caso de ser una serie
     "temporadas": list:{    #None en caso de ser una pelicula
        "titulo": str,
        "episodios": list:{
            "titulo": str,
            "videoId": str,
            "links": list:{"file": str}, 
          }
      }
    }
   ```
 - Se entregan 2 scripts.
    - ScriptAPI.py : Este es el script que funciona y cumple con los requisitos solicitados. 
        - En mi computadora tarda alrededor de 2 min en obtener la informacion del API, generar el json de forma local y grabar toda la informacion en una lista AUDIOVISUALES de MongoDB
        - Utiliza para el scraping el mismo API que usa la pagina.
        - Para grabar en la base de datos utiliza el string de conexion de un archivo .env (nombre de variable *DATABASE_CONNECTION_STRING*).
        - Los metadatos de las peliculas y series se obtienen de forma secuencial.
        - Los metadatos de los archivos para streaming se obtienen en paralelo con 5 hilos.

    - ScriptBot.py : Este script no esta completo pero sirve para mostrar como se podria hacer el scraping utilizando selenium.
        - Es mucho mas lento (aprox 5 horas, sin la metada de los episodios).
        - Utilizar bots que simulen el comportamiento de un usuario en un navegador suele ser la unica alternativa cuando la web no tiene un API publica.
        - En este caso scriptBot.py espera entre uno y dos segundos para tratar de simular un compartamiento humano (tambien se podria simular el movimiento del mouse, etc) debido a que muchas paginas pueden llegar a bloquear las conexiones cuando detectan un bot de scraping.
        - Tambien se podria usar proxys para prevenir bloqueos de IP.


 - Se entrega un archivo .json con los resultados.

## Modelo de negocio
   - Es una pagina que parece ofrecer contenido legal (video on demand con publicidad).
   - Intenta ofrecer al usuario final una experiencia de navegación similar a las aplicaciones de streaming como netflix.
   - Se sustenta economicamente a base de publicidad invasiva.
   - Contiene un conjunto de peliculas, series y cortos (contenido audiovisual) que no suele encontrarse en los canales de streaming convencionales.
   - Los datos de los usuarios son compartidos con productores, autores y/o estudios de las peliculas/series junto con estadisticas de las mismas (ejemplo: review de la pelicula, clicks en una pelicula, etc).

## Tiempo de ejecucion
scriptAPI.py: 2 minutos.

