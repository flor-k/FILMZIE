from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import numpy
from pymongo import MongoClient
from dotenv import load_dotenv
import os


load_dotenv()
DATABASE_CONNECTION_STRING = os.environ[DATABASE_CONNECTION_STRING]

coneccionAlServidor = MongoClient(DATABASE_CONNECTION_STRING)
db = coneccionAlServidor['FILMZIE']  #accedo a la base de datos FILMZIE
coll = db['audiovisuales'] #accedo a la coleccion de peliculas


url = "https://filmzie.com/home"
driver = webdriver.Chrome()
driver.maximize_window()
driver.get(url)


##Lista de los links de todas las peliculas que se recorrieron
linksTodasLasPeliculas = []


class Audiovisual:
    def __init__(self, titulo, año, duracion, categorias, sinopsis, link, esPelicula, esSerie):
        self.titulo = titulo
        self.año = año
        self.duracion  = duracion
        self.categorias = categorias.split(',')
        self.sinopsis  = sinopsis
        self.link = link
        self.esPelicula = esPelicula
        self.esSerie = esSerie
    
    def obtenerDocumento(self):
        return {"titulo" : self.titulo,
                "año" : self.año,
                "duracion"  : self.duracion,
                "categorias" : self.categorias,
                "sinopsis"  : self.sinopsis,
                "link" : self.link,
                "esPelicula" : self.esPelicula,
                "esSerie" : self.esSerie}
                
 

        

def obtenerLinksCategorias():
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
    driver.get(url)
    pausa()
    scrollAlFinal()
    links = driver.find_elements(By.CSS_SELECTOR, 'main#root div div.content-blocks div.content-block-large a')
    linksRetornados:list[str] = []
    for link in links:
        linksRetornados.append(link.get_attribute('href'))
    return linksRetornados

def scrollAlFinal():
    while True:
        driver.execute_script("window.scrollBy(0,1000)")
        pausa()
        bottom = driver.execute_script('return window.innerHeight + window.pageYOffset >= document.body.scrollHeight')
        if bottom:
            break
        
def pausa():
    time.sleep(1 + numpy.random.uniform(0,1))



def obtenerDatosPelicula(url):
    driver.get(url)
    pausa()
    if(esUnaSerie()):
        titulo = driver.find_element(By.CSS_SELECTOR, "h1.title").get_attribute('innerText')
        año = driver.find_element(By.CSS_SELECTOR, 'span.year').get_attribute('innerText')
        duracion = None
        categorias = driver.find_element(By.CSS_SELECTOR, 'span.category').get_attribute('innerText')
        sinopsis = driver.find_element(By.CSS_SELECTOR, 'p.fs-18').get_attribute('innerText')
        esPelicula = False
        esSerie = True
        link = None

    else:
        titulo = driver.find_element(By.CSS_SELECTOR, "h1.title").get_attribute('innerText')
        año = driver.find_element(By.CSS_SELECTOR, 'span.year').get_attribute('innerText')
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
    audivoisual = Audiovisual(titulo = titulo, año = año, duracion = duracion, categorias = categorias, sinopsis = sinopsis, link = link, esPelicula = esPelicula, esSerie = esSerie)

    return audivoisual

    

def scrapingLinksPeliculas(linksPeliculas):
    peliculasCategoria:list[Audiovisual] = []
    for linkPelicula in linksPeliculas:
        encontrado = linkPelicula in linksTodasLasPeliculas
        if not encontrado:
            pelicula:Audiovisual = obtenerDatosPelicula(linkPelicula)
            linksTodasLasPeliculas.append(linkPelicula)
            peliculasCategoria.append(pelicula)
            #coll.insert_one(pelicula.obtenerDocumento())  #esta linea sirve para insertar pelicula por pelicula
    return peliculasCategoria


def insertarPeliculasEnBaseDatos(peliculasCategoria:list[Audiovisual]):
    if(len(peliculasCategoria)>0): #nos aseguramos de tener peliculas en la categoria para que no falle MongoDB por insertar una lista vacia
        documentosDePeliculas:list[object] = []
        for pelicula in peliculasCategoria:
            documentosDePeliculas.append(pelicula.obtenerDocumento())
        coll.insert_many(documentosDePeliculas)


def esUnaSerie():
    try:
        driver.find_element(By.CSS_SELECTOR, 'div.select-alternative button.select-trigger')
        return True
    except:
        return False


def obtenerTemporadas():
    driver.find_element(By.CSS_SELECTOR,'button.select-trigger').click()
    temporadas = driver.find_elements(By.CSS_SELECTOR,'div.select-content button.text-white span').__getattribute__('innerText')
    return temporadas







#obtiene todos los links de cada categoria
linksCategorias = obtenerLinksCategorias()
for linkCategoria in linksCategorias:
    #obtiene los links de cada pelicula en la categoria
    linksPeliculas = obtenerLinksPeliculas(linkCategoria)
    #obtiene la lista de peliculas con sus datos
    peliculasCategoria = scrapingLinksPeliculas(linksPeliculas)
    #inserta la lista de peliculas en la base de datos
    insertarPeliculasEnBaseDatos(peliculasCategoria)
 
    
