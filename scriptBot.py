from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import numpy
from pymongo import MongoClient
from dotenv import main
import os
from datetime import datetime

main.load_dotenv()
DATABASE_CONNECTION_STRING = os.environ['DATABASE_CONNECTION_STRING']

coneccionAlServidor = MongoClient(DATABASE_CONNECTION_STRING)
db = coneccionAlServidor['FILMZIE']  #accedo a la base de datos FILMZIE
coll = db['audiovisuales'] #accedo a la coleccion de peliculas


url = "https://filmzie.com/home"
driver = webdriver.Chrome()
driver.maximize_window()
driver.get(url)


##Lista de los links de todas las peliculas que se recorrieron
linksTodasLasPeliculas = []

#Definicion de Audiovisual como Clase
class Audiovisual:
    """representa un elemento audiovisual
    """
    def __init__(self, titulo:str, anio:str, duracion:str, categorias:list, sinopsis:str, link:list, esPelicula:bool, esSerie:bool):
        """_summary_

        Args:
            titulo (str): titulo del audiovisual
            anio (str): año del audiovisual, le saque la ñ para evitar problemas de caracteres
            duracion (str): duracion del audiovisual
            categorias (list): categorias del audiovisual
            sinopsis (str): sinopsis del audiovisual
            link (list): link del audiovisual
            esPelicula (bool): define con un boolean si es una pelicula
            esSerie (bool): define con un boolean si es una serie
        """

        self.titulo = titulo
        self.anio = anio
        self.duracion  = duracion
        self.categorias = categorias.split(',')
        self.sinopsis  = sinopsis
        self.link = link
        self.esPelicula = esPelicula
        self.esSerie = esSerie
    
    def obtenerDocumento(self):
        """define la estructura de un documento
        """
        return {"titulo" : self.titulo,
                "anio" : self.anio,
                "duracion"  : self.duracion,
                "categorias" : self.categorias,
                "sinopsis"  : self.sinopsis,
                "link" : self.link,
                "esPelicula" : self.esPelicula,
                "esSerie" : self.esSerie}
                
 
#Inicio de definicion de funciones
        

def obtenerLinksCategorias():
    """Obtiene los links de todas las categorias

    Returns:
        list: links de todas las categorias
    """
    burger = driver.find_element(By.CSS_SELECTOR, "button.category-burger")
    burger.click()
    pausa()
    links = driver.find_elements(By.CSS_SELECTOR, 'header > div > div.categories-menu > div.categories > a')
    linksRetornados:list[str] = []
    for link in links:
        #selecciona solo las categorias cuyo link contenga /category/
        if(link.get_attribute('href').find('/category/') != -1):
            linksRetornados.append(link.get_attribute('href'))
    return linksRetornados

def obtenerLinksPeliculas(url):
    """obtiene los links para cada pelicula de la categoria

    Args:
        url (str): link de una categoria

    Returns:
        list: lista con los links de las peliculas
    """
    driver.get(url)
    pausa()
    scrollAlFinal()
    links = driver.find_elements(By.CSS_SELECTOR, 'main#root div div.content-blocks div.content-block-large a')
    linksRetornados:list[str] = []
    for link in links:
        linksRetornados.append(link.get_attribute('href'))
    return linksRetornados


#Funcion para scrollear hasta el final de la pagina ya que la misma carga dinamicamente
def scrollAlFinal():
    while True:
        driver.execute_script("window.scrollBy(0,1000)")
        pausa()
        bottom = driver.execute_script('return window.innerHeight + window.pageYOffset >= document.body.scrollHeight')
        if bottom:
            break

#Genera una pausa para simular el tiempo de espera de una persona, ademas de que permite darle tiempo a la pagina para cargar        
def pausa():
    time.sleep(1 + numpy.random.uniform(0,1))



def obtenerDatosPelicula(url):
    """Obtiene los datos solicitados de las peliculas y series

    Args:
        url (str): se pasa la url de una pelicula o serie

    Returns:
        Audiovisual: objeto audiovisual
    """

    driver.get(url)
    pausa()
    if(esUnaSerie()):
        titulo = driver.find_element(By.CSS_SELECTOR, "h1.title").get_attribute('innerText')
        anio = driver.find_element(By.CSS_SELECTOR, 'span.year').get_attribute('innerText')
        duracion = None
        categorias = driver.find_element(By.CSS_SELECTOR, 'span.category').get_attribute('innerText')
        sinopsis = driver.find_element(By.CSS_SELECTOR, 'p.fs-18').get_attribute('innerText')
        esPelicula = False
        esSerie = True
        link = None

    else:
        titulo = driver.find_element(By.CSS_SELECTOR, "h1.title").get_attribute('innerText')
        anio = driver.find_element(By.CSS_SELECTOR, 'span.year').get_attribute('innerText')
        duracion = driver.find_element(By.CSS_SELECTOR, 'span.duration').get_attribute('innerText')
        categorias = driver.find_element(By.CSS_SELECTOR, 'span.category').get_attribute('innerText')
        sinopsis = driver.find_element(By.CSS_SELECTOR, 'p.fs-18').get_attribute('innerText')
        driver.find_element(By.CSS_SELECTOR, 'div.movie-detail div.row div.left-panel button.btn-watch-free').click()
        pausa()
        try:
            link = driver.find_element(By.CSS_SELECTOR, 'div#modal-root div.player-modal div.modal-body div.player div.background video').get_attribute('src')
        except:
            link = None
        esPelicula = True
        esSerie = False
    audiovisual = Audiovisual(titulo = titulo, anio = anio, duracion = duracion, categorias = categorias, sinopsis = sinopsis, link = link, esPelicula = esPelicula, esSerie = esSerie)

    return audiovisual

    

def scrapingLinksPeliculas(linksPeliculas):
    """verifica que las peliculas no esten repetidas antes de hacer el scraping,
    luego obtiene los datos de la misma.

    Args:
        linksPeliculas (list): una lista con todos los links a las peliculas o series

    Returns:
        list:Audiovisual: devuelve todas las peliculas de la categoria
    """
    peliculasCategoria:list[Audiovisual] = []
    for linkPelicula in linksPeliculas:
        encontrado = linkPelicula in linksTodasLasPeliculas #Me aseguro de no tener el link de la pelicula repetido para no subirlo dos veces a la base de datos
        if not encontrado:
            pelicula:Audiovisual = obtenerDatosPelicula(linkPelicula)
            linksTodasLasPeliculas.append(linkPelicula)
            peliculasCategoria.append(pelicula)
            #coll.insert_one(pelicula.obtenerDocumento())  #esta linea sirve para insertar pelicula por pelicula
    return peliculasCategoria


def insertarPeliculasEnBaseDatos(peliculasCategoria:list[Audiovisual]):
    """inserta los datos de cada audiovisual en la base de datos

    Args:
        peliculasCategoria (list[Audiovisual]): posee una lista con un objeto Audiovisual que contiene los datos de cada audiovisual
    """
    if(len(peliculasCategoria)>0): #nos aseguramos de tener peliculas en la categoria para que no falle MongoDB por insertar una lista vacia
        documentosDePeliculas:list[object] = []
        for pelicula in peliculasCategoria:
            documentosDePeliculas.append(pelicula.obtenerDocumento())
        coll.insert_many(documentosDePeliculas)


def esUnaSerie():
    """define si un audiovisual es o no una serie dependiendo si tiene el boton de temporadas

    Returns:
        boolean
    """
    try:
        driver.find_element(By.CSS_SELECTOR, 'div.select-alternative button.select-trigger')
        return True
    except:
        return False



#Inicio de ejecucion

inicio = datetime.now()
#obtiene todos los links de cada categoria
linksCategorias = obtenerLinksCategorias()
for linkCategoria in linksCategorias:
    #obtiene los links de cada pelicula en la categoria
    linksPeliculas = obtenerLinksPeliculas(linkCategoria)
    #obtiene la lista de peliculas con sus datos
    peliculasCategoria = scrapingLinksPeliculas(linksPeliculas)
    #inserta la lista de peliculas en la base de datos
    insertarPeliculasEnBaseDatos(peliculasCategoria)
 
fin = datetime.now()
print('Tiempos de ejecucion:')
print(' - Inicio: {}'.format(inicio))
print(' - Fin:    {}'.format(fin))
print(' - Tiempo: {}'.format(fin - inicio))
    
#Fin de ejecucion