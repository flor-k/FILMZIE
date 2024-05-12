from pymongo import MongoClient
from datetime import datetime
import requests
import json
import time
import numpy
from concurrent.futures import ThreadPoolExecutor
import threading
import asyncio
import aiohttp
from dotenv import load_dotenv
import os


load_dotenv()
DATABASE_CONNECTION_STRING = os.environ['DATABASE_CONNECTION_STRING']

inicio = datetime.now()
inicioStr = str(datetime.now().isoformat().replace(':','_'))
cantidadDeHilos = 5
coneccionAlServidor = MongoClient(DATABASE_CONNECTION_STRING)
db = coneccionAlServidor['FILMZIE']  #accedo a la base de datos FILMZIE
coll = db['audiovisuales'] #accedo a la coleccion de peliculas
documentosConLinksCargados = 0

url = "https://filmzie.com/api/v1/content?"
limit = 100
offset = 0
hayDatos = True
listaDocumentosTodos = [] # contiene 1 documento por cada pelicula o serie. 
chunksLista = 100

def pausa():
    time.sleep(1 + numpy.random.uniform(0,1))


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
    


print('cargando links para {} audiovisuales con {} hilos en paralelo... '.format(str(len(listaDocumentosTodos)), str(cantidadDeHilos)))

async def get(documento, session):
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
    

async def main(listaDocumentosTodos):
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(get(documento, session) for documento in listaDocumentosTodos))

asyncio.run(main(listaDocumentosTodos))

print('Creando archivo resultado_{}.json...'.format(inicioStr))
with open('resultado_'+inicioStr+'.json', 'w') as f:
    json.dump(listaDocumentosTodos, f)
print(' - Archivo resultado_{}.json creado'.format(inicioStr))

def crearSublistas(listas, n):
    for i in range(0, len(listas), n):
        yield listas[i:i + n]

subListas = crearSublistas(listaDocumentosTodos, chunksLista)
cantidadDocumentos = len(listaDocumentosTodos)
documentosInsertados = 0
print('Insertando documentos en base de datos...')
for subLista in subListas:
    print('  - Insertando {} / {}'.format(str(len(subLista) + documentosInsertados), str(cantidadDocumentos)))
    coll.insert_many(subLista)
    documentosInsertados = documentosInsertados + len(subLista)
print(' - Todos los documentos se insertaron en la base de datos')

fin = datetime.now()
print('Tiempos de ejecucion:')
print(' - Inicio: {}'.format(inicio))
print(' - Fin:    {}'.format(fin))
print(' - Tiempo: {}'.format(fin - inicio))

