"""
Ce fichier est un fichier dans lequel la majorité des constantes non muables sont (les autres sont dans les préférences.txt traitées par préférences.py)
Les seules fonctions qui sont ici sont les fonctions mettant en place les paths utilisés pour accédér au repositoire du monde
"""

import random
import os
import json
import game.preferences as preferences
preferences.setup_preferences()

# ---------------------------------------- PARAMÈTRES DE CHUNKS----------------------------------------
CHUNK_SIZE = 16 # La longueur du côté de la chunk (c'est un carré selon le plan xy)
WORLD_HEIGHT = 300 # La hauteur maximale à laquelle nous avons des blocs
CHUNK_BLOCK_MARGIN = 500 # La marge de blocs à mettre en vram en plus que prévoit une chunk (voir world.game_chunk.load_to_screen)
# PARAMÈTRES D'OVERCHUNKS 
OVERCHUNK_SIZE =  (preferences.GEN_DISTANCE + 1) * 2 * CHUNK_SIZE# Un overchunk est un grand chunk utilisé pour le scan de structures, ceci est donc la longueur de son côté /2, puisque c'est une opération que nous effectuons dans tous les cas
OVERCHUNK_SAFETY_MARGIN = 0 # La marge de sécurité pour les overchunks, utilisée lors de bugs


# ---------------------------------------- PARAMÈTRES DE GÉNÉRATION INTIALE ----------------------------------------
DEFAULT_INITIAL_TERRAIN_SIZE = 10 # La longueur du côté du carré de génération initiale, en chunks
# ---------------------------------------- PARAMÈTRES DE SCANS ----------------------------------------
# RUNTIME
MINIMUM_INITIAL_PRESCAN_MARGIN = 256 # éviter de spawn dans un volcan
STRUCTURES_CHECK_STEP = 64 # afin d'être sûr d'avoir des coordonnées multiples de STRUCTURE_CHECK_STEP et pour donc faire ceux-là step_wise
# DÉBUT
INITIAL_GENERATION_EXTENT = max(MINIMUM_INITIAL_PRESCAN_MARGIN,
                                OVERCHUNK_SIZE - DEFAULT_INITIAL_TERRAIN_SIZE * CHUNK_SIZE) # la quantité par laquelle augmenter le scan initial (il est plus grand)
INITIAL_PRESCAN = ((- INITIAL_GENERATION_EXTENT,
                    - INITIAL_GENERATION_EXTENT),
                   (DEFAULT_INITIAL_TERRAIN_SIZE * CHUNK_SIZE + INITIAL_GENERATION_EXTENT,
                    DEFAULT_INITIAL_TERRAIN_SIZE * CHUNK_SIZE + INITIAL_GENERATION_EXTENT)) # Scan de structure initial (il est plus grand que les autres)




# ---------------------------------------- PARAMÈTRES DE JOUEUR ----------------------------------------
PLAYER_SPAWN = [DEFAULT_INITIAL_TERRAIN_SIZE*CHUNK_SIZE/2, DEFAULT_INITIAL_TERRAIN_SIZE*CHUNK_SIZE/2, 200] # Le spawn du joueur
PLAYER_HITBOX_OFFSETS = [0.4,0.4,[-1.5,0.2]] # Les offsets pour dans chaque direction pour former la hitbox du joueur
                                             # Il y a deux offsets différents pour la direction z, puisque la hitbox n'est pas symmétrique autour du joueur dans cette dimension 


# ---------------------------------------- PARAMÈTRES DE MOUVEMENT ----------------------------------------
MOVECONST = preferences.SPEED*1/30*1/2 # La constante de mouvement: va décider si on bouge plus ou moins vite
TURNCONST = 0.02*1/30 # La constante pour tourner: va décider si on tourne plus ou moins vite, en plus de la sensitivité
JUMPCONST = 0.4 # La constante de saut, va décider de combien on augment la vitesse verticale du joueur
SENSITIVITY = 1*0.75 # La sensitivité pour tourner
GRAVITY=0.1 * 1/100 # La gravité (le g de notre jeu)
DYNAMIC_GRAVITY = True # Si nou utilisons de la gravité dynamique, aka que le plus on monte, le moins la terre nous attire, donc le moins fort sa gravité se fait sentir, et si on va trop haut, la gravité s'inverse
GRAVITY_THRESHOLD = [60, 250] # en dessous du premier paramètre la gravité n'est pas modifiée, entre le premier et le deuxieme elle diminue, et au dessus du deuxieme elle s'inverse


# ---------------------------------------- PARAMÈTRES DE VISUELS DANS LE JEU ----------------------------------------
FOV = 70 # L'angle en degrés de la largeur du champ de vision (voir la doc)
CAM_CLIP= (0.05,500) # tout point contenu entre les deux paramètres sera visible, utilisé pour la matrice de projection
MAXFPS = 80 # La limite sur les fps

# ---------------------------------------- PARAMÈTRES DE FENÊTRE ----------------------------------------
WINDOW_WIDTH = 800 # La largeur de la fenètre initiale, en px
WINDOW_HEIGHT = 600 # La longueur de la fenètre initiale, en px
BACKGROUND_COLOUR = (0.66, 0.98, 1.0)# La couleur de fond de la fenètre (le ciel)
ASPECT_RATIO = WINDOW_WIDTH / WINDOW_HEIGHT # Le aspect ratio utilisé pour la caméra


# ---------------------------------------- PARAMÈTRES DE TEXTURES ----------------------------------------
TEXTURE_LOCATION = 0 # Le nombre associé aux textures principales (bedrock inclue)
HB_TEXTURE_LOCATION = 1 # Le nombre associé aux textures de hotbat (bedrock exclue)
DIR = os.path.dirname(__file__) # Le fichier mère dans lequel nous sommes éxécutés
TEXTURE_PATH = os.path.join(DIR, "texture_atlas\\texture_atlas_1-134x8.png") # L'endroit où l'on peut trouver les textures standard
HB_TEXTURE_PATH = os.path.join(DIR, "texture_atlas\\texture_atlas_1-128x8.png") # L'endroit òu l'on peut trouver les textures de hotbar

# ---------------------------------------- PARAMÈTRES DE DATA_MANAGER_WORLD ----------------------------------------
LAST_SENT_LENGTH = 10 # La longueur de la liste des derniers chunks envoyés, pour éviter un overload
MAX_RENDERABLES_STORED = 500 # La quantité max de renderables stockés chez le data manager world
MAX_CHUNKS_STORED = 500 # La quantité max de chunks stockés chez le data manager generation


# ---------------------------------------- PARAMÈTRES DE DATA_MANAGER_GENERATION ----------------------------------------
MAX_QUEUE = 500 # Le nombre maximum de demandes stockées dans la queue


# ---------------------------------------- PARAMÈTRES DE BLOCS ----------------------------------------
CUBE_SIDELENGTH = 1 # La largeur d'un cube (À NE PAS CHANGER)
ID_VERS_BLOC = { # Le dictionnaire envoyant un id à son nom
    0: "air",
    1: "pierre",
    2: "terre",
    3: "tronc",
    4: "feuille",
    5: "eau",
    6: "herbe",
    7: "fer",
    8: "diamant",
    -1: "charbon",
    -2: "bedrock",
    11: "lave",
    12: "sable",
    13: "planche",
    14: "porte",
    14.1: "porte_bas",
    14.2: "porte_haut",
    16: "neige",
    17: "basalte",
    19: "cuivre",
    21: "verre",
    22: "artefact"
}
BLOC_VERS_ID = {item : key for key, item in ID_VERS_BLOC.items()} # Le dictionnaire ID_VERS_BLOC inversé
id_vers_tex = { # Un dictionnaire envoyant un id de bloc à son indice de texture
    4:0,
    5:1,
    1:2,
    3:3,
    6:4,
    2:5,
    12:6,
    16:7,
    7:8,
    8:9,
    -1:10,
    10:11,
    11:12,
    13:13,
    21:14,
    17:15,
    -2:16
}
tex_vers_id = {item : key for key, item in id_vers_tex.items()} # Le dictionnaire id_vers_tex inversé



# ---------------------------------------- PARAMÈTRES DE GÉNÉRATION ----------------------------------------


MINERAIS_DATA = lambda z:  [ # Fonction utilisée pour calculer la distribution de minerais
    ("fer",(40, 2**(-0.0005 * (z-40)**2) - 0.01*z + 0.32)),
    ("diamant", (120, 2**(-0.01 * (z-15)) - 0.04*z + 0.54)),
    ("charbon", (30, 2**(-0.0005 * (z-50)**2) + 0.001*z - 0.05))
]

# ---------------------------------------- PARAMÈTRES DE SEED ----------------------------------------
SEED = "" # La seed
SEED_LENGTH = 16 # La longueur des sous seeds

def setSeeds(MAIN_SEED, num_seeds, length=SEED_LENGTH):
    """
    Cette fonction va calculer les sous seeds utilisées pour différentes parties de le génération
    :param MAIN_SEED: la seed principale
    :param num_seeds: le nombre de sous-seeds
    :param length: la longueur des sous seeds (défault seed_length)
    """
    seeds = []
    for i in range(num_seeds):
        random.seed(MAIN_SEED+str(i))
        seeds.append(''.join(random.choices('0123456789', k=length)))
    return seeds
# ---------------------------------------- PATHS VERS FICHIERS DU MONDE ----------------------------------------

palmiers_path = os.path.join(DIR, "terrain_generation\\structures\\palmiers\\palmier%s_rotation_[%s].struct.npy") # Le chemin vers le fichier de structures de palmiers

WORLD_ID = "" # L'ID du monde
CHUNKS_FORMAT = "" # Le format du path vers les chunks pour pouvoir faire CHUNKS_FORMAT%(chunk_x,chunk_y)
RENDERABLES_FORMAT = "" # idem pour les renderables
HEIGHTS_FORMAT = "" # Et pour les fichiers heights
WORLD_ID_FORMAT = "New_World_%s" # et encore de même pour le format du fichier mère du monde


def init_settings(new_world_id):
    """
    Cette fonction va fixer les différentes constantes pour les formats des paths vers les différents fichiers du jeu
    :new_world_id: l'id du monde
    """
    global WORLD_ID, CHUNKS_FORMAT, RENDERABLES_FORMAT, HEIGHTS_FORMAT
    WORLD_ID = new_world_id
    CHUNKS_FORMAT = str(os.path.join(WORLD_ID, "chunks_%s_%s.npy"))
    RENDERABLES_FORMAT = str(os.path.join(WORLD_ID, "chunks_renderables_%s_%s.npy"))
    HEIGHTS_FORMAT = str(os.path.join(WORLD_ID, "heights_%s_%s.npy"))

# On essaie d'ouvrir le fichier settings.json qui contient toutes les infos lors d'un load. Ceci est effectué sur import, et ne fera rien dans le cas d'une création de fichier
if os.path.exists("settings.json"):
    with open("settings.json", 'r') as fr:
        data = json.load(fr)
        if len(data) == 2 and isinstance(data[0], str) and isinstance(data, list):
            WORLD_ID, params = data
            SEED = params[0]
            init_settings(WORLD_ID)
        else:
            raise Exception("Paramètres corrompus, supprimez 'settings.json' et relancez le jeu")
