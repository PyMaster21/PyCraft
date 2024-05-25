"""SETTINGS DE GENERATION DE TERRAIN"""
from game.settings import *  # importe les settings communs
import game.preferences as preferences
preferences.setup_preferences()
GENERATION = preferences.GENERATION

# ------------------------ GENERATION SETTINGS ----------------------------
WATERNESS = 1.0  # a quel point le monde est composé d'eau
WORLD_AMPLIFICATION = 0.75  # amplification verticale du monde


if WORLD_AMPLIFICATION > 0:
    MAX_HEIGHT = max(350, int(WORLD_AMPLIFICATION * 150))  # hauteur max du terrain
    WATER_LEVEL = max(50, int(50+abs(WORLD_AMPLIFICATION-1)*10 + WATERNESS*15))  # niveau de l'eau
else:
    MAX_HEIGHT = max(350, int(-WORLD_AMPLIFICATION * 100))
    WATER_LEVEL = max(50, int(-WORLD_AMPLIFICATION * 50 + WATERNESS*15))

SUPERFLAT_HEIGHT = 10  # hauteur du terrain si un monde plat est generé
WATER_HEIGHT_DECREASING_RATE = 10  # a quel point les océans sont abruptes
HEIGHTS_SIZE = 4  # format des données des fichiers de hauteur

DIRT_BLOCS = 4  # nombre de blocs de terre


# ------------------------ FLOATING ISLAND SETTINGS -------------------------

FLOATING_ISLAND_PERLIN_NOISE_INFO = {   # paramètres de perlin noise des îles flottantes
    "main": [80, 1, 0.5],
    "main_variation": [50, 0, 0.5, [4]],
    "small_variation": [50, 0, 0.5, [8]]
}

FLOATING_ISLAND_LAYERS = 3  # nombre de couches d'îles flottantes generées

FLOATING_ISLAND_BASE_HEIGHT = 150  # hauteur de base du premier layer
FLOATING_ISLAND_HEIGHT_GAP = 50  # espacement vertical entre deux layers
FLOATING_ISLAND_ISLAND_STRETCH = 5  # etirement de l'île
FLOATING_ISLAND_THRESHOLD = 0.1  # paramètre de densité des îles flottantes
FLOATING_ISLAND_RANDOM_HEIGHTS = (20, 30)  # hauteurs des deux autres layers


# ----------------------- VILLAGE SETTINGS --------------------------------

VILLAGES_BY_1000x1000 = 20  # nombre théorique de villages par zone de 1000x1000 blocs

VILLAGES_MAX_RADIUS = 100  # rayon maximal que peut avoir un village
VILLAGES_MIN_DISTANCE_FROM_PLAYER = 10  # distance minimale d'un village avec le player pour pouvoir spawner
VILLAGES_RANDOM_NUMBER_OF_HOUSES = [8, 20]  # nombre de maisons
VILLAGES_IGNORED_BLOCS = [0, 3, 4]  # blocs ignorés : si il y a une maison, on les remplace par les blocs de maison
VILLAGES_MIN_GAP_BETWEEN_HOUSES = 5  # espacement minimal entre deux maisons

# localisation des fichiers
VILLAGES_STRUCT_EXTENSION = ".struct.npy"
VILLAGES_FILE_DIRECTORY = os.path.dirname(__file__)
VILLAGES_STRUCT_DIRECTORY = "structures"
VILLAGES_DIR_TO_GENERATE = "rotated"

VILLAGES_OOB_HOUSE_PATH = f"{WORLD_ID}/_outofbounds/villages"
VILLAGES_OOB_CHUNK_PATH = f"{WORLD_ID}/_outofbounds/villages"
VILLAGE_HOUSE_CHUNK_CHECK_PATH = f"{WORLD_ID}/_outofbounds/villages/houses_finished.json"


# ------------------------ VOLCANO SETTINGS -------------------------------

VOLCANO_HEIGHT = [50, 80]  # hauteur du volcan
VOLCANO_DECREASING_FACTOR = [12, 18]  # A quel point le volcan est abrupte

VOLCANO_SAFETY_THRESHOLD = 2  # hauteur effective de la lave (diminuée) par rapport à la hauteur max théorique
VOLCANO_VERIFICATION_SIZE = 10  # nombre de chunks verifiées autour du volcan lors du spawn
VOLCANO_CHECK_THETA_STEP = 2  # différence d'angle entre deux mesures

VOLCANOS_BY_1000x1000 = 13  # nombre théorique de volcans par zone de 1000x1000 blocs

# localisation des fichiers
OOB_VOLCANOS_PATH = f"{WORLD_ID}/_outofbounds/volcanos/_entities"
OOB_VOLCANOS_CHUNK_PATH = f"{WORLD_ID}/_outofbounds/volcanos"

VOLCANO_LAVA_CHECK_PATH = f"{WORLD_ID}/_outofbounds/volcanos/lava.json"


# ------------------------ USEFUL FUNCTIONS -------------------------------
def coords_to_normalized(x, y):
    """Convertis des coordonnées de bloc en coordonnées de chunk"""
    return x >> 4, y >> 4


def normalized_to_coords(x, y):
    """Convertis des coordonnées de chunk en coordonnées de bloc"""
    return x*CHUNK_SIZE, y*CHUNK_SIZE
