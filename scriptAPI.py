from pymongo import MongoClient
from datetime import datetime
import requests
import json
import asyncio
import aiohttp
from dotenv import main
import os

#Inicia definicio de variables


main.load_dotenv()
DATABASE_CONNECTION_STRING = os.environ['DATABASE_CONNECTION_STRING']
inicio = datetime.now()
inicioStr = str(datetime.now().isoformat().replace(':','_'))
coneccionAlServidor = MongoClient(DATABASE_CONNECTION_STRING)
db = coneccionAlServidor['FILMZIE']  #accedo a la base de datos FILMZIE
coll = db['audiovisuales2'] #accedo a la coleccion de peliculas
documentosConLinksCargados = 0

url = "https://filmzie.com/api/v1/content?"


listaDocumentosTodos = [] # contiene 1 documento por cada pelicula o serie. 
chunksLista = 100

#Inicia definicio de funciones

def principal():
    """
    obtengo la data de la API y guardo cada metadato en Documento exceptuando el link
    """
    hayDatos = True
    limit = 100
    offset = 0
    while hayDatos:
        url = 'https://filmzie.com/api/v1/content?limit='+str(limit)+'&offset='+str(offset)+'&comingSoonSupported=true'
        resultado = requests.get(url)
        resultadoJson = resultado.json()
        listaAudiovisuales = list(resultadoJson['data']['data'])
        if(len(listaAudiovisuales) == 0):
            hayDatos = False
            break
        if hayDatos:
            listaDocumentos = []
            for audiovisual in listaAudiovisuales:
                try:
                    # no guardo todos los datos del json para no ocupar demasiado espacio en la base de datos, me interesan solo
                    # la informacion relevante para el negocio
                    documento = {"duration":None,
                                 "titulo":None,
                                 "categorias":None,
                                 "anio":None, #no uso la ñ para evitar problemas de caracteres
                                 "sinopsis":None,
                                 "actores": None,
                                 "directores": None,
                                 "studio":None,
                                 "tipo": None,
                                 "videoId": None,
                                 "links" : None,
                                 "temporadas": None}

                    documento["duration"] = int(int(audiovisual['duration'])/60) if audiovisual['duration'] is not None else None
                    documento["titulo"] = str(audiovisual['title']) if audiovisual['title'] is not None else None
                    documento["categorias"] = list(audiovisual['category']) if audiovisual['category'] is not None else None
                    documento["anio"] = str(audiovisual['released']) if audiovisual['released'] is not None else None
                    documento["sinopsis"] = str(audiovisual['description']) if audiovisual['description'] is not None else None
                    documento["actores"] = list(audiovisual['actors']) if audiovisual['actors'] is not None else None
                    documento["directores"] = list(audiovisual['directors']) if audiovisual['directors'] is not None else None
                    documento["studio"] = str(audiovisual['studio']) if audiovisual['studio'] is not None else None
                    documento["tipo"] = str(audiovisual['type']) if audiovisual['type'] is not None else None
                    documento["videoId"] = str(audiovisual['mainVideoId']) if audiovisual['mainVideoId'] is not None else None
                    if documento["videoId"] is None:
                        documento["temporadas"] = []

                        for temporada in list(audiovisual["seasons"]):
                            documentoTemporada = {'titulo': temporada['title'],
                                                  'episodios' : []}
                            for episodio in list(temporada['episodes']):
                                documentoTemporada['episodios'].append({"titulo": episodio['title'],
                                                                        "videoId": episodio['videoId']})
                            documento['temporadas'].append(documentoTemporada)

                    listaDocumentos.append(documento)
                    listaDocumentosTodos.append(documento)
                except Exception as error:
                    print('error al obtener DATOS de una pelicula ',error)
                    with open(str('error_'+inicioStr+'.json'), 'a') as f:
                        json.dump(audiovisual, f)

            offset += limit
            print('cargando pagina', 'offset:{} - limit:{} - documentosCreados:{}'.format(str(offset), str(limit), str(len(listaDocumentos))))
        

async def conseguirLinks(listaDocumentosTodos):
    """
    Consigo los links para cada Documento (pelicula y cada episodio) pasando por el get de forma paralela

    Args:
        listaDocumentosTodos (list): lista con todos los Documentos
    """
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(get(documento, session) for documento in listaDocumentosTodos))


async def get(documento, session):
    """accedemos a la API con el videoID, la misma nos devuelve el link al video

    Args:
        documento (Documento): 
        session (aiohttp.ClientSession()): 
    """
    try:
        if(documento["tipo"] == 'MOVIE'):
            url = 'https://filmzie.com/api/v1/video/stream/'+str(documento["videoId"])
            async with session.get(url=url) as response:
                resp = await response.read()
                # decodifica la respuesta obtenida por read(), remplazamos ' por " para que sea un json valido
                my_json = resp.decode('utf8').replace("'", '"')
                data = json.loads(my_json)
                documento['links'] = data['data']['source']['sources']
        elif(documento["tipo"] == 'TV_SHOW'):
            for temporada in list(documento["temporadas"]):
                for episodio in list(temporada['episodios']):
                    url = 'https://filmzie.com/api/v1/video/stream/'+str(episodio["videoId"])
                    async with session.get(url=url) as response:
                        resp = await response.read()
                        # decodifica la respuesta obtenida por read(), remplazamos ' por " para que sea un json valido
                        my_json = resp.decode('utf8').replace("'", '"')
                        data = json.loads(my_json)
                        episodio['links'] = data['data']['source']['sources']
    except Exception as e:
        print("No se pudo obtener la url {} debido a {}.".format(url, e.__class__))
    



def crearSublistas(listas, n):
    """Divide la lista de Audiovisuales en chunks de 100

    Args:
        listas (list): 
        n (int): 

    """
    for i in range(0, len(listas), n):
        yield listas[i:i + n]


#Inicia la ejecucion de codigo


principal()

print('cargando links para {} audiovisuales en paralelo... '.format(str(len(listaDocumentosTodos))))

asyncio.run(conseguirLinks(listaDocumentosTodos))

print('Creando archivo resultado_{}.json...'.format(inicioStr))

with open('resultado_'+inicioStr+'.json', 'w') as f:
    """Inserto todos los datos en un JSON
    """
    json.dump(listaDocumentosTodos, f)

print(' - Archivo resultado_{}.json creado'.format(inicioStr))

subListas = crearSublistas(listaDocumentosTodos, chunksLista) #Creo las sublistas de audiovisuales
cantidadDocumentos = len(listaDocumentosTodos)
documentosInsertados = 0

print('Insertando documentos en base de datos...')

for subLista in subListas:
    #voy insertando los metadatos en mongoDB de a chunks
    print('  - Insertando {} / {}'.format(str(len(subLista) + documentosInsertados), str(cantidadDocumentos)))
    coll.insert_many(subLista)
    documentosInsertados = documentosInsertados + len(subLista)

print(' - Todos los documentos se insertaron en la base de datos')

fin = datetime.now()
print('Tiempos de ejecucion:')
print(' - Inicio: {}'.format(inicio))
print(' - Fin:    {}'.format(fin))
print(' - Tiempo: {}'.format(fin - inicio))

#   Fin de ejecucion

