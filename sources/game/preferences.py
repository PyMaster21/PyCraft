"""
Ce fichier va prendre preferences.txt et récupérer ses paramètres pour qu'ils puissent être utilisés
dans le jeu.
C'est donc un simple algorithme de parsing qui se trouve ici
"""
import os
import pygame as pg

# On va maintenant défnir le dictionnaire str_to_pg qui pourra convertir des chars à des pg.K event,
# afin de pouvoir les customiser
# Une splendide comprehension de dictionaire, qui crée un dictionnaire de paires ("b",ord(b)) pour toues les
# lettres de l'alphabet, puisque pour celles-ci pg.K_lettre = ord(lettre)
str_to_pg = {chr(i): i for i in range(ord("a"), ord("z")+1)}
# str_to_pg = dict(zip(map((lambda x: chr(x)),range(ord("a"), ord("z")+1)),range(ord("a"), ord("z")+1)))
# On met maintenant toutes les touches autres que l'alphabet
str_to_pg["space"] = pg.K_SPACE
str_to_pg["shift"] = pg.K_LSHIFT
str_to_pg["up"] = pg.K_UP
str_to_pg["down"] = pg.K_DOWN
str_to_pg["left"] = pg.K_LEFT
str_to_pg["right"] = pg.K_RIGHT
str_to_pg["escape"] = pg.K_ESCAPE
str_to_pg["espace"] = pg.K_SPACE  # En français
str_to_pg["maj"] = pg.K_LSHIFT
str_to_pg["haut"] = pg.K_UP
str_to_pg["bas"] = pg.K_DOWN
str_to_pg["gauche"] = pg.K_LEFT
str_to_pg["droite"] = pg.K_RIGHT
str_to_pg["echap"] = pg.K_ESCAPE

int_digits = set(str(1234567890))  # Les chiffres autorisés pour un entier
float_digits = int_digits | {"-", "."}


def parse_preferences():
    """
    Une fonction qui va parser les préférences pour les sortir du txt
    :return: un dictionnaire {key:val} pour les préférences
    """
    if os.path.exists("../preferences.txt"):  # Le fichier existe
        with open("../preferences.txt", "r") as f:  # On l'ouvre
            contents = f.read()
            # On parse
            # Si on a commencé un commentaire, dans quel cas on ignore tout texte jusqu'à la prochaine ligne
            hashtagged = False
            equaled = False  # Si on a commencé une équivalence key:val
            parsed_key = ""  # La key parsée
            parsed_value = ""  # La valeur parsée
            param_dict = {}  # Le dictionnaire à rendre
            for char in contents:  # On itère sur le contenuu
                if not hashtagged:  # On ignore le texte sinon
                    if char == ":":  # Le caractère pour créer une équivalence entre key et val
                        equaled = True
                    elif char == "#":  # On a entamé un commentaire
                        hashtagged = True
                    elif char != " " and char != "\n":  # Ce n'est ni un espace ou un retour à la ligne
                        if equaled:  # On a déjà fait l'équivalence donc on est en train de donner la valeur
                            parsed_value += char
                        else:  # L'équivalence n'ayant pas encore été faire on est en train de donner la key
                            parsed_key += char
                if char == "\n":  # On a fait un retour à la ligne
                    if equaled:  # Si on avait fait l'équivalence, alors cette ligne contiendrait une paire key:val
                        equaled = False  # On remet à 0
                        # On met la paire dans le dict
                        param_dict[parsed_key] = parsed_value
                    parsed_key = ""  # On remet toutes les autres variables à 0 et on recommence
                    parsed_value = ""
                    hashtagged = False
            if equaled:  # IL faut stocker la dernière paire à la fin du parsing
                param_dict[parsed_key] = parsed_value
            return param_dict  # On retourne le dict

    else:  # Si le fichier n'existe pas on le crée
        # On crée le fichier si celui-ci n'existe pas encore
        with open("../preferences.txt", "w+") as f:
            f.write("""
Ce fichier de préférences est traité par le fichier préférences.py
les paramètres sont de forme
# param : valeur sachant que le "#" n'est que nécessaire quand on veut annoter quelque chose derrière une valeur, ex:
# param : valeur      # annotation


PARAMÈTRES MISC
sensibilite: 0.4          # défaut: 0.4    Un float pour la sensibilite de la souris dans le jeu
vitesse: 0.4            # défaut: 0.4     Un float pour la vitesse, 0.4 est assez lent
gravite dynamique: True # défaut: True Un bool pour la gravité dynamique (la gravité diminue 
                        #              progressivement le plus haut on monte avant de s'inverser)
max fps: 80             # défaut: 80   Le fps auquel le jeu sera limité
fov: 70                 # défaut: 70   Se référer à la section caméra de la doc pour voir ce que ce nombre représente



PARAMÈTRES CLAVIER
clavier : azerty # Changeable à "qwerty", "azerty" ou "autre". 	Si autre est choisi, le programme regardera les 
                                touches écrites ci-dessous qui peuvent soit être une lettre de l'alphabet, 
                                soit les touches du clavier:
                                "up"/"haut", "down"/"bas", "left"/"gauche", "right"/"droite"
                                soit encore "shift"/"maj", "space"/"espace" et "escape"/"echap"
DÉFINITION DES TOUCHES DANS LE CAS D'UN CLAVIER=AUTRE
--Mouvement--
devant : z   # qwerty: w, azerty: z
gauche : q   #         a          q
droite : d   #         d          d
derriere : s #         s          s
monter : space #       space      space
descendre : shift #    shift      shift
                    
--Contrôle du jeu --
voler : f           #  f          f           Voler met la gravité en pause
pause : escape      #  escape     escape      Quand le jeu est pausé la souris est libérée et la physique 
                                              ainsi que les contrôles sont arrêtés
quitter : a         #  q          a           Appuyer sur quitter + pause pour quitter le jeu  
                    
-- Contrôle de --                             Permet de changer les touches utilisées pour changer le bloc 
--  la hotbar  --                             sélectionné dans la hotbar
                                              Ainsi que de changer celles utilisées pour changer de hotbar
hotbar gauche : left # left       left        
hotbar droite : right# right      right
hotbar haut : up    #  up         up   
hotbar bas : down   #  down       down


PARAMÈTRES DE GÉNÉRATION
renderdistance : 5     # défaut : 5,       Un uint >=3, Ceci va déterminer la distance en dessous de laquelle les chunks 
                                                        seront affichés
gendistance : 7        # défaut : 7,       Un uint >=3, Ceci va déterminer la distance en dessous de laquelle les chunks
                                                        seront demandées à être générées
generation initiale : 10 # défaut: 10      Un int, ceci va déterminer la longueur (en chunks) du côté du carré de génération
                                           initale. 
relief: True           # défaut: True      Un bool, ceci va déterminer si le terrain a du relief ou pas
biomes: True           # défaut: True      Un bool, ceci va déterminer si le terrain a des biomes ou pas
arbres: True           # défaut: True      Un bool, ceci va déterminer si le terrain a des arbres ou pas
îles flottantes: True  # défaut: True      Un bool, ceci va déterminer si le terrain a des îles flottantes ou pas
volcans: True          # défaut: True      Un bool, ceci va déterminer si le terrain a des volcans ou pas
villages: True         # défaut: True      Un bool, ceci va déterminer si le terrain a des villages ou pas
minerais: True         # défaut: True      Un bool, ceci va déterminer si le terrain a des minerais ou pas
grottes: True          # défaut: True      Un bool, ceci va déterminer si le terrain a des grottes ou pas
                    
qualitégrottes: 2      # défaut: 2        Un uint entre 1 et 8 (inclus), determine la qualité de géneration des grottes 
                                          A augmenter avec précaution, et seulement si vous allez visiter les grottes 
                                          (mettre dans ce cas une gendistance et renderdistance pas trop élevées)
                                          (le paramètre n'est pas pris en compte si grottes:False)
                    
Plus votre ordinateur est puissant, plus vous pouvez augmenter les paramètres suivants : vitesse, renderdistance, gendistance (et qualitégrottes)
Pour un très bon ordinateur, vous pouvez mettre vitesse à 1, renderdistance à 20 et gendistance à 22.
                    """)
        return {}  # On retourne un dict vide puisque setup_préférences saura mettre les défauts


def setup_preferences():
    """
    Cette fonction va mettre les bonnes valeurs pour les constantes générales du jeu (extraites de preferences.py)
    """
    global FORWARD_K, LEFT_K, RIGHT_K, BACK_K, UP_K, DOWN_K, FLYING_K, PAUSE_K, QUIT_K, HB_L_K, HB_R_K, HB_U_K, HB_D_K
    global ONLY_ON_PRESS_KEYS
    global GEN_DISTANCE, RENDER_DISTANCE, SENSITIVITY, DYNAMIC_GRAVITY, MAX_FPS, FOV
    global GENERATION, INITIAL_TERRAIN_SIZE
    global SPEED, CAVE_QUALITY
    default_preferences = {  # Les préférences par défaut
        "clavier": "azerty",
        "devant": str_to_pg["z"],
        "gauche": str_to_pg["q"],
        "droite": str_to_pg["d"],
        "derriere": str_to_pg["s"],
        "monter": str_to_pg["space"],
        "descendre": str_to_pg["shift"],
        "voler": str_to_pg["f"],
        "pause": str_to_pg["escape"],
        "quitter": str_to_pg["a"],
        "hotbardroite": str_to_pg["left"],
        "hotbargauche": str_to_pg["right"],
        "hotbarhaut": str_to_pg["up"],
        "hotbarbas": str_to_pg["down"],
        "renderdistance": 5,
        "gendistance": 7,
        "sensibilite": 0.4,
        "vitesse": 0.4,
        "gravitedynamique": True,
        "maxfps": 80,
        "fov": 70,
        "generationinitiale": 10,
        "relief": True,
        "biomes": True,
        "arbres": True,
        "îlesflottantes": True,
        "volcans": True,
        "villages": True,
        "minerais": True,
        "grottes": True,
        "qualitégrottes": 2,
    }
    parsed = parse_preferences()  # On récupère le dict des préférences en le parsant

    def get_param_pg_key(key):
        """
        Cette fonction va pour un paramètre censé être dans le dictionnaire str_to_pg vérifier 
        si cela est le cas, et renvoyer une valeur en fonction
        :param key: le paramètre, aka la clé du dictionnaire parsed 
        """
        if isinstance(str_to_pg.get(parsed.get(key)), int):
            return str_to_pg[parsed[key]]
        else:
            return default_preferences[key]

    def get_param_value_number(key, num_type):
        """
        Cette fonction va pour un paramètre censé être un nombre, vérifier si
        cela est le cas, et renvoyer une valeur en fonction

        :param key: la clé du dictionnaire pour laquelle nous voulons vérifier
        :param num_type: le type de nombre, 0 pour int et 1 pour float 
        """
        if parsed.get(key) is not None:
            value_set = set(parsed.get(key))  # On peut alors en faire un ensemble
            if num_type == 0:  # Nous voulons un entier
                if len(value_set) == len(value_set & int_digits):  # Il n'y a que des chiffres dans le str
                    return int(parsed[key])
            elif num_type == 1:  # Nous voulons un float
                if len(value_set) == len(value_set & float_digits):  # Il n'y a que des chiffres dans le str
                    return float(parsed[key])
        else:
            return default_preferences[key]
    
    def get_param_value_bool(key):
        """
        Cette fonction va pour un paramètre censé être un bool, vérifier si
        cela est le cas, et renvoyer une valeur en fonction

        :param key: la clé du dictionnaire pour laquelle nous voulons vérifier
        """
        if parsed.get(key) is not None:
            if parsed.get(key) == "True":  # Il n'y a que des chiffres dans le str
                return True
            elif parsed.get(key) == "False":
                return False
        else:
            return default_preferences[key]

    # Les utilisateurs sont des gueux ne sachant pas lire les instructions
    if parsed.get("clavier") not in {"qwerty", "azerty", "autre"}:
        parsed["clavier"] = default_preferences["clavier"]  # On met le défaut
    # L'utilisateur aura défini ses propres hotkeys, quel nerd
    elif parsed.get("clavier") == "autre":
        # La fonction ci dessous va verifier si les touches sont bien définies, et donner la valeur par défaut sinon
        FORWARD_K = get_param_pg_key("devant")
        LEFT_K = get_param_pg_key("gauche")
        RIGHT_K = get_param_pg_key("droite")
        BACK_K = get_param_pg_key("derriere")
        UP_K = get_param_pg_key("monter")
        DOWN_K = get_param_pg_key("descendre")
        FLYING_K = get_param_pg_key("voler")
        PAUSE_K = get_param_pg_key("pause")
        QUIT_K = get_param_pg_key("quitter")
        HB_L_K = get_param_pg_key("hotbargauche")
        HB_R_K = get_param_pg_key("hotbardroite")
        HB_U_K = get_param_pg_key("hotbarhaut")
        HB_D_K = get_param_pg_key("hotbarbas")

    match parsed.get("clavier"):  # On regarde parmis les claviers standards
        case "qwerty":  # On met les constantes pour le clavier qwerty
            FORWARD_K = str_to_pg["w"]
            LEFT_K = str_to_pg["a"]
            RIGHT_K = str_to_pg["d"]
            BACK_K = str_to_pg["s"]
            UP_K = str_to_pg["space"]
            DOWN_K = str_to_pg["shift"]
            FLYING_K = str_to_pg["f"]
            PAUSE_K = str_to_pg["escape"]
            QUIT_K = str_to_pg["q"]
            HB_L_K = str_to_pg["left"]
            HB_R_K = str_to_pg["right"]
            HB_U_K = str_to_pg["up"]
            HB_D_K = str_to_pg["down"]
        case "azerty":  # On met les constantes pour le clavier azerty
            FORWARD_K = str_to_pg["z"]
            LEFT_K = str_to_pg["q"]
            RIGHT_K = str_to_pg["d"]
            BACK_K = str_to_pg["s"]
            UP_K = str_to_pg["space"]
            DOWN_K = str_to_pg["shift"]
            FLYING_K = str_to_pg["f"]
            PAUSE_K = str_to_pg["escape"]
            QUIT_K = str_to_pg["a"]
            HB_L_K = str_to_pg["left"]
            HB_R_K = str_to_pg["right"]
            HB_U_K = str_to_pg["up"]
            HB_D_K = str_to_pg["down"]

    # Variables de génération
    RENDER_DISTANCE = max(3, get_param_value_number("renderdistance", 0))  # Le nombre doit être >3
    GEN_DISTANCE = max(3, get_param_value_number("gendistance", 0))  # Le nombre doit être >3
    SENSITIVITY = get_param_value_number("sensibilite", 1)  # Un float pour la sensitivité de la souris dans le jeu
    DYNAMIC_GRAVITY = get_param_value_bool("gravitedynamique")  # Un bool pour la gravité dynamique
    MAX_FPS = get_param_value_number("maxfps", 1)  # Le fps auquel le jeu sera limité
    FOV = get_param_value_number("fov", 1)  # Voir la section caméra de la doc pour voir ce que ce nombre représente
    SPEED = get_param_value_number("vitesse", 1)
    CAVE_QUALITY = get_param_value_number("qualitégrottes", 0)
    #la longueur (en chunks) du côté du carré de génération initale.
    INITIAL_TERRAIN_SIZE = min(max(0,get_param_value_number("generationinitiale",0)), int(GEN_DISTANCE * 2**(1/2)))

    GENERATION = {  # Différentes constantes pour activer ou désactiver certaines fonctionnalités de la génération
        "relief": get_param_value_bool("relief"),
        "biomes": get_param_value_bool("biomes"),
        "trees": get_param_value_bool("arbres"),
        "floating islands": get_param_value_bool("îlesflottantes"),
        "volcanos": get_param_value_bool("volcans"),
        "caves": get_param_value_bool("grottes"),
        "villages": get_param_value_bool("villages"),
        "ores": get_param_value_bool("minerais")
    }

    # Ces touches là fonctionnent de façon particulière, elles ne s'activent que lors de l'appui initial,
    # et non tout au long comme les touches de mouvement
    ONLY_ON_PRESS_KEYS = {FLYING_K, PAUSE_K, HB_L_K, HB_R_K, HB_U_K, HB_D_K}
