import json
import game.settings as settings
import game.preferences as prefs
import os
import random


class Game:
    def __init__(self):
        """Classe résponsable de tout ce qui est autour du jeu, à savoir la création ou le load de mondes,
        mais aussi la sauvegarde à la fin du jeu"""
        self.WORLD_ID = ""
        self.world = None
        self.params = {}
        self.init_type = ""

    def __enter__(self):
        """Magic Method servant à autoriser la création d'un contexte avec cette classe"""
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Magic Method appellée lors de la sortie du contexte, donc quand le programme s'arrête,
        même si c'est par une erreur, et qui permet de sauvegarder notre monde quand même"""
        print("-- Context exit --")
        print(f"Exception class : {exc_type}")
        print(f"Exception value : {exc_val}")
        print(f"Exception traceback : {exc_tb}")
        # Sauvegarde le monde
        self.save_world()

        # Termine et kill le process en cours
        import game.data_manager_world as data_manager
        for chunk in data_manager.changed_chunks.copy():
            data_manager.save_chunk(chunk)
        data_manager.process.terminate()
        data_manager.process.join()
        self.world.renderer.end() # On termine le renderer


    def autostart(self):
        """Vous pouvez appeler cette méthode depuis main.py pour executer une
        même action à chaque lancement de jeu"""
        self.create_world("mwahohooasa", "d")
        # self.load_world("mwahohooasa")

    def bind_context_to_world(self, world):
        """Passe l'instance du World ici, pour que cette classe y ait accès"""
        self.world = world

    def load_parameters(self):
        """Load tous les paramètres qu'avait le player avant de quitter le monde"""
        if self.init_type == "load":
            if "position" in self.params and "direction" in self.params and "velocity" in self.params:
                self.world.player.position = self.params["position"]
                self.world.player.direction = self.params["direction"]
                self.world.fpcamera.direction = self.params["direction"]
                self.world.player.speed_y = self.params["velocity"]
            else:
                print("Paramètres du monde corrompus, reinitialisation des paramètres du monde")

    def save_world(self):
        """Sauvegarde les paramètres du monde"""
        params = {"position": tuple(self.world.player.position.tolist()),
                  "direction": tuple(self.world.player.direction.tolist()),
                  "velocity": self.world.player.speed_y}

        # Load les paramètres déjà existants pour d'autres mondes
        if os.path.exists("worlds.json"):
            with open("worlds.json", "r") as fr:
                worlds = json.load(fr)
        else:
            worlds = {}

        # Ajoute les paramètres de ce monde
        worlds[self.WORLD_ID] = params

        # Sauvegarde les données complètes
        with open("worlds.json", "w") as fw:
            json.dump(worlds, fw)

        print("WORLD SUCCESSFULLY SAVED")

    def starting_input(self):
        """Definit avec un input si le monde sera créé ou bien loadé"""
        world = input("Voulez vous (o)uvrir ou (c)réer un monde : ")
        if world.lower() == "o":
            self.input_load()
        elif world.lower() == "c":
            self.input_create()

    def input_load(self):
        """Le monde sera loadé, definit quel monde il faut loader"""
        if os.path.exists("worlds.json"):
            with open("worlds.json", "r") as fr:
                worlds = json.load(fr)
        else:
            print("Le fichier de mondes 'worlds.json' n'existe pas, il est impossible d'ouvrir un monde")
        world_to_open = None
        while not world_to_open:
            name = None
            while not name:  # empêche les inputs vides
                name = input("Nom du monde à ouvrir : ")

            # Verifie que le monde existe
            if name in worlds.keys():
                if os.path.exists(name):
                    # Le monde existe, son dossier aussi, on peut le load
                    world_to_open = name
                    print(f"Le monde va être ouvert : {world_to_open}")
                else:
                    # Le monde existe mais pas son dossier, le monde est corrompu
                    print(f"Le dossier du monde est inexistant, impossible d'ouvrir : {name}")
            else:
                # Le monde n'existe pas
                print(f"Le monde n'existe pas : {name}")

        # Load le world
        self.load_world(world_to_open)

    def load_world(self, world_to_open):
        """Load le monde qui s'appelle 'world_to_open'"""
        self.init_type = "load"
        self.WORLD_ID = world_to_open

        # Initialise les settings aveec ce world_id
        settings.init_settings(self.WORLD_ID)

        # Récupère les paramètres du monde à load
        with open("worlds.json", "r") as fr:
            worlds = json.load(fr)

        self.params = worlds[self.WORLD_ID]
        print(self.params)

    def input_create(self):
        """Le monde sera créé, definit quel sera le nom du world, et quelle sera sa seed"""
        name = input("Nom du monde à créer : ")
        if not name:
            name = "auto"

        custom_seed = input("Seed spécifique ? (o/n) ")
        if custom_seed.lower() == "o":
            seed = None
            while not seed:
                temp_seed = input("Entrez la seed : ")
                if temp_seed.isalnum(): # verifie que la seed n'a que des caractères alpha-numériques
                    seed = temp_seed
        else:
            # Crée une seed aléatoire
            seed = ''.join(random.choices('0123456789', k=settings.SEED_LENGTH))

        # Crée le monde avec un nom donné et une seed donnée
        self.create_world(name, seed)

    def create_world(self, name, seed):
        """Crée un monde qui s'appelle en theorie 'name' et qui a pour seed 'seed'"""
        self.init_type = "create"

        # Load les données des mondes
        with open("worlds.json", "r") as fr:
            worlds = json.load(fr)

        if name == "auto":
            self.WORLD_ID = "New_World"
        else:
            self.WORLD_ID = name

        # Trouve un nom unique qui n'existe pas déjà
        if self.WORLD_ID in worlds or os.path.exists(self.WORLD_ID):
            for i in range(10000):
                if not self.WORLD_ID + f"_{i}" in worlds and not os.path.exists(self.WORLD_ID + f"_{i}"):
                    self.WORLD_ID = self.WORLD_ID + f"_{i}"
                    break

        # Inite le monde dans les données de monde
        worlds[self.WORLD_ID] = {}

        # Initialise les settings pour ce world id
        settings.init_settings(self.WORLD_ID)
        settings.SEED = seed  # definit la seed

        # Crée les dossiers nécessaires au world
        self.create_world_directories()

        # Sauvegarde les données de monde
        with open("worlds.json", 'w') as fw:
            json.dump(worlds, fw)

        # Sauvegarde les settings
        with open("settings.json", 'w') as fw:
            json.dump((self.WORLD_ID, [seed]), fw)

        # Génère le terrain initial
        self.generate_initial_terrain()

    def create_world_directories(self):
        """Crée les dossiers nécessaires pour le monde"""
        os.mkdir(self.WORLD_ID)
        os.mkdir(f"{self.WORLD_ID}/_outofbounds")
        os.mkdir(f"{self.WORLD_ID}/_outofbounds/villages")
        os.mkdir(f"{self.WORLD_ID}/_outofbounds/volcanos")
        os.mkdir(f"{self.WORLD_ID}/_outofbounds/volcanos/_entities")
        os.mkdir(f"{self.WORLD_ID}/_outofbounds/trees")

    @staticmethod
    def generate_initial_terrain():
        """Génère le terrain inital, ce qui va permettre d'avoir une base de terrain déjà génerée, et ici avec toutes
        les ressources disponibles car le jeu ne tourne pas"""
        # on importe ici, car on doit importer APRES l'initialisation des settings
        import game.terrain_generation.main as chunk_generation
        init_generation_size = prefs.INITIAL_TERRAIN_SIZE

        # Genère le terrain sur une grande zone, de 'initial_generation_size' chunks de côté
        chunk_generation.generate_initial_terrain(
            ((0, 0), (init_generation_size * settings.CHUNK_SIZE, init_generation_size * settings.CHUNK_SIZE)))

        # Obtiens les renderables pour ces chunks génerés
        for i in [(j // init_generation_size, j % init_generation_size) for j in range(init_generation_size ** 2)]:
            chunk_generation.get_renderables_norm(i[0], i[1])
