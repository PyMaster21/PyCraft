"""
Ce script est celui qui gère le monde du jeu dans son ensemble. Ici sont mis en relation les
scripts rendering, les scripts terrain_generation, en passant par les data_manager (se référer à la doc)
et les scripts world afin de faire exister le joueur et sa physique, et de pouvoir lui faire placer et casser des blocs. 
"""
from win32gui import GetWindowRect, FindWindow
import pygame as pg
import numpy as np

import game.settings as settings
import game.preferences as prefs
import game.data_manager_world as data_manager


from game.world.game_chunk import *
from game.world.player import *

import game.rendering.renderer as renderer
import game.rendering.scene as scene
import game.rendering.texture as textures
from game.rendering.gui import Gui

import game.shaders.shaders as shaders

import game.terrain_generation.fast_renderables as fast_renderables

from pynput import mouse
current_mouse = mouse.Controller()


class World:
    def __init__(self):
        """
        La classe du jeu, à laquelle sera assignée un renderer et un player. Le terrain passera par lui
        via le data_manager (voir la doc)
        """
        self.renderdistance = prefs.RENDER_DISTANCE  # Distance en dessous de laquelle les chunks sont affichés
        # de même mais pour la génération des chunks
        self.gendistance = prefs.GEN_DISTANCE
        self.lookat = None  # Le bloc que nous regardons
        self.running = True  # Si le jeu est en pause
        self.flying = False  # Si nous sommes en train de voler
        self.pressed_keys = set()  # Les touches appuyées
        # Le compteur "hotbar" est un indice qui indique quel place de celle ci est sélectionnée
        self.hbcounter = 0
        self.hblevel = 0  # Le niveau "hotbar" désigne laquelle des deux hotbars est sélectionnée

        # Mise en place du renderer
        self.renderer = renderer.Renderer()
        self.scene = scene.Scene()
        self.renderer.bind_scene(self.scene)
        # On récupère la position absolue de la fenêtre pygame
        window_position = GetWindowRect(
            FindWindow(None, pg.display.get_caption()[0]))
        self.pg_win_middle = (int((window_position[0]+window_position[2])/2), int(
            (window_position[1]+window_position[3])/2))  # On calcule le milieu de la fenêtre

        # Mise en place du joueur et de sa caméra
        self.player = Player(settings.PLAYER_SPAWN, direction=[0, 1, 0])
        self.previous_player_chunk = (0,0) # La chunk où le joueur était au frame précédent
        # le fov vient des preferences
        self.fpcamera = Camera([0, 0, 0], [0, 1, 0], following_position=self.player,
                               fov=prefs.FOV, clip=settings.CAM_CLIP, aspect_ratio=settings.ASPECT_RATIO)

        # Initialisation des variables chunk
        # Tous les chunks affichés sur l'écran (instances de la classe world.game_chunk.Chunk)
        self.rendered_chunks = {}
        # Toutes les positions des chunks affichés sur l'écran en format (chunk_x, chunk_y)
        self.rendered_chunks_positions = set()
        # Les chunks dont les renderables n'ont pas encore été générés alors que ceux-ci devraient l'être
        # (afin de pouvoir les redemander en priorité)
        self.unrendered_chunks = set()

        # Mise en place des shaders
        # Mise en place des textures
        self.texture_atlas = textures.TextureAtlas(
            self.renderer.ctx, settings.TEXTURE_PATH)
        # Le texture atlas des blocs contient la bedrock
        self.texture_atlas.use_texture(settings.TEXTURE_LOCATION)

        self.hb_texture_atlas = textures.TextureAtlas(
            self.renderer.ctx, settings.HB_TEXTURE_PATH)
        self.hb_texture_atlas.use_texture(
            settings.HB_TEXTURE_LOCATION)  # Et celui de la hotbar non

        # Création des shaders
        self.renderer.shader_manager.create_program("cube", shaders.cube_with_shadows_vert,
                                                    shaders.cube_with_shadows_frag)
        self.renderer.shader_manager.create_program("transparent_cube", shaders.transparent_vert,
                                                    shaders.transparent_frag)

        # Initialisation des uniforms du shader cube
        self.renderer.shader_manager.update_uniforms("cube", ["cam_pos", "m_proj", "alpha_rot",
                                                              "beta_rot", "TextureAtlas"],
                                                             [self.fpcamera.position, self.fpcamera.projectionMatrix,
                                                              self.fpcamera.alpha_matrix, self.fpcamera.beta_matrix,
                                                              np.array([settings.TEXTURE_LOCATION], dtype="int8")])
        self.renderer.shader_manager.update_uniforms("transparent_cube", ["cam_pos", "m_proj", "alpha_rot",
                                                              "beta_rot", "TextureAtlas"],
                                                             [self.fpcamera.position, self.fpcamera.projectionMatrix,
                                                              self.fpcamera.alpha_matrix, self.fpcamera.beta_matrix,
                                                              np.array([settings.TEXTURE_LOCATION], dtype="int8")])
                                                              

        # Mise en place des shaders gui

        # La croix affichée au milieu de l'écran
        self.renderer.shader_manager.create_program("cross", shaders.cross_vert, shaders.cross_frag)
        # La hotbar
        self.renderer.shader_manager.create_program("hotbar", shaders.hotbar_vert, shaders.hotbar_frag)
        # Le petit carré utilisé pour sélectionner un bloc dans la hotbar
        self.renderer.shader_manager.create_program("hbselection", shaders.selection_square_vert,
                                                    shaders.selection_square_frag)

        # Initialisation des uniforms de ces derniers shaders
        self.renderer.shader_manager.update_uniform(
            "cross", "AspectRatio", np.float32(settings.ASPECT_RATIO))
        self.renderer.shader_manager.update_uniforms("hotbar", ("AspectRatio", "TextureAtlas", "HotbarOffset"),
                                                     (np.float32(settings.ASPECT_RATIO),
                                                      np.int8(settings.HB_TEXTURE_LOCATION), np.int8(self.hblevel)))

        self.renderer.shader_manager.update_uniforms("hbselection", ("AspectRatio", "SelectionIndex"),
                                                     (np.float32(settings.ASPECT_RATIO), np.uint8(self.hbcounter)))

        # Création de l'objet gui et ajout à la scène
        g = Gui(self.renderer.ctx, self.renderer.shader_manager["cross"],
                self.renderer.shader_manager["hotbar"], self.renderer.shader_manager["hbselection"])
        self.renderer.scene.add_object(g)

    @property
    def renderdistance(self):
        """
        On crée une propriété afin de pouvoir changer certaines listes si self.renderdistance devait être changée
        """
        return self._renderdistance

    @renderdistance.setter
    def renderdistance(self, value: int):
        """
        Assigne la valeur à self._renderdistance mais change également la liste self.relative_chunks_visible
        :param value: la nouvelle valeur de renderdistance
        """
        self._renderdistance = value
        # Une liste de positions (chunk_x, chunk_y) de chunks relatifs visibles
        self.relative_chunks_visible = []
        # Génère une liste de positions parmi lesquelles nous pourrons tout simplement purger
        # (un carré de côté 2*renderdistance)
        chunks_to_check = [(i//(2*value+2)-value, i % (2*value+2)-value)
                           for i in range((2*value+1)**2+2*value)]
        for chunk in chunks_to_check:  # Purge de chunks non inclus dans le cercle de rayon renderdistance
            if chunk[0]**2+chunk[1]**2 <= value**2:
                self.relative_chunks_visible.append(chunk)

    @property
    def gendistance(self):
        """
        On crée une propriété afin de pouvoir changer certaines listes si self.gendistance devait être changée
        """
        return self._gendistance

    @gendistance.setter
    def gendistance(self, value: int):
        """
        Assigne la valeur à self._gendistance mais change également la liste self.relative_chunks_to_generate
        :param value: la nouvelle valeur de gendistance
        """
        self._gendistance = value
        # L'algorithme ci-dessous est expliqué dans la documentation (voir la doc)
        chunks_to_check = [(i//(2*value+2)-value, i % (2*value+2)-value)
                           for i in range((2*value+1)**2+2*value)]  # Le carré de côté 2*gendistance
        relative_chunks_to_generate_subdivided = [
            [] for _ in range(value+1)]  # On crée la liste de subdivisions
        for chunk in chunks_to_check:
            chunk_distance = int((chunk[0]**2+chunk[1]**2)**0.5)
            if chunk_distance <= value:  # On purge les chunks trop éloignés
                relative_chunks_to_generate_subdivided[chunk_distance].append(
                    chunk)  # On ajoute la chunk à son anneau
        self.relative_chunks_to_generate = []
        for chunk_ring in relative_chunks_to_generate_subdivided:
            # On ajoute les anneaux du plus proche au plus éloigné
            self.relative_chunks_to_generate += chunk_ring

    def update_shaders(self):
        """
        Cette fonction va mettre à jour les uniforms de caméra pour les shaders de blocs. 
        À noter que les shaders du GUI ne sont pas mis à jour ici
        """

        # Si la caméra n'a pas changé sa matrice de projection nous n'avons pas besoin de la redonner
        if self.fpcamera.computed_projection_matrix:
            self.renderer.shader_manager.update_uniforms("cube", ["cam_pos", "alpha_rot", "beta_rot"],
                                                         [self.fpcamera.position, self.fpcamera.alpha_matrix,
                                                          self.fpcamera.beta_matrix])
            self.renderer.shader_manager.update_uniforms("transparent_cube", ["cam_pos", "alpha_rot", "beta_rot"],
                                                         [self.fpcamera.position, self.fpcamera.alpha_matrix,
                                                          self.fpcamera.beta_matrix])
        else:  # Mais sinon oui
            self.renderer.shader_manager.update_uniforms("cube", ["cam_pos", "m_proj", "alpha_rot", "beta_rot"],
                                                         [self.fpcamera.position, self.fpcamera.projectionMatrix,
                                                          self.fpcamera.alpha_matrix, self.fpcamera.beta_matrix])
            self.renderer.shader_manager.update_uniforms("transparent_cube", ["cam_pos", "m_proj", "alpha_rot", "beta_rot"],
                                                         [self.fpcamera.position, self.fpcamera.projectionMatrix,
                                                          self.fpcamera.alpha_matrix, self.fpcamera.beta_matrix])

    def load_chunks(self, unload=True, generate=True):
        """
        Cette fonction va prendre les chunks en distance d'affichage et les afficher si cela peut être fait.
        Cette fonction va également demander à ce que des chunks non générés mais normalement visibles soient
        générés le plus vite possible (il va les demander à la priority queue du data manager)
        :param unload: un bool qui décide si nous désaffichons les chunks qui ne sont plus visibles
        :param generate: si il faut générer des chunks manquants
        """
        player_chunk = self.player.chunk

        if unload:  # Si il faut désafficher certains chunks nous le faisons
            self.unload_chunks()

        for chunk in self.relative_chunks_visible:  # Pour chacun des chunks visibles en théorie
            # Nous convertissons les coordonnées relatives en coordonnées absolues de chunk
            chunk_absolute = (
                int(chunk[0] + player_chunk[0]), int(chunk[1] + player_chunk[1]))

            # Le chunk n'est pas affiché à l'écran, et ce n'est pas un cas de chunk non généré
            if chunk_absolute not in self.rendered_chunks_positions and chunk_absolute not in self.unrendered_chunks:
                # Si les blocs renderables n'existent pas encore, le datamanager les demandera, avec priorité
                chunk_fetch = data_manager.get_renderables(
                    chunk_absolute, generate, False)
                # On vérifie pour voir si le chunk a bien été récupéré
                # Il n'est pas encore récupérable côté data_manager
                if not isinstance(chunk_fetch, np.ndarray):
                    self.unrendered_chunks.add(chunk_absolute)
                else:
                    # On instantialise un objet chunk avec les blocks que nous venons de récupérer
                    self.rendered_chunks[chunk_absolute] = (
                        Chunk(chunk_absolute, chunk_fetch))
                    self.rendered_chunks_positions.add(chunk_absolute)
                    self.rendered_chunks[chunk_absolute].load_to_screen(
                        self.renderer)  # On met les blocks du chunk à l'écran
                    # On demande au renderer de trier les water batchs pour qu'ils soient visibles
                    self.renderer.scene.sort_waters(self.player.chunk)

        # On itère sur les chunks sans renderables
        # on va modifier la liste donc on la copie au préalable
        unrendered_chunks_copy = self.unrendered_chunks.copy()
        for chunk in unrendered_chunks_copy:
            chunk_relative = (chunk[0]-player_chunk[0],
                              chunk[1]-player_chunk[1])
            if chunk_relative not in self.relative_chunks_visible:
                # Si le chunk non affiché n'est plus censé l'être, on le sort de la liste
                self.unrendered_chunks.remove(chunk)
            else:
                # si le chunk n'est pas encore généré le data manager le demandera avec priorité
                chunk_fetch = data_manager.get_renderables(
                    chunk, generate, False)
                if isinstance(chunk_fetch, np.ndarray):  # Le chunk est généré
                    self.unrendered_chunks.remove(chunk)
                    self.rendered_chunks[chunk] = (  # On initialise le chunk comme lors d'un load normal
                        Chunk(chunk, chunk_fetch))
                    self.rendered_chunks_positions.add(chunk)
                    self.rendered_chunks[chunk].load_to_screen(
                        self.renderer)
                    # On demande au renderer de trier les water batchs pour qu'ils soient visibles
                    self.renderer.scene.sort_waters(self.player.chunk)

    def structure_scan(self):
        """
        Cette fonction va effectuer les scans de structure afin d'avoir de celles-ci dans le monde
        """
        step = settings.STRUCTURES_CHECK_STEP
        position = self.player.position
        current_overchunk = ((int(position[0] - settings.OVERCHUNK_SIZE)//step*step,
                              int(position[1] - settings.OVERCHUNK_SIZE)//step*step),
                             (int(position[0] + settings.OVERCHUNK_SIZE)//step*step,
                              int(position[1] + settings.OVERCHUNK_SIZE)//step*step))

        # On envoie le overchunk au data_manager afin qu'il envoie le scan à faire
        data_manager.send_structure_scan(current_overchunk, position)

    def unload_chunks(self):
        """
        Fonction utilisée pour désafficher les chunks qui ne sont plus censés être visibles
        """
        player_chunk = self.player.chunk

        # Itère sur tous les chunks affichés
        for chunk_pos, chunk in self.rendered_chunks.copy().items():
            position_relative = (
                chunk_pos[0]-player_chunk[0], chunk_pos[1] - player_chunk[1])  # La position relative du chunk

            if position_relative not in self.relative_chunks_visible:  # Le chunk n'est pas censé être visible
                for index in chunk.indices:  # Si le chunk a plusieurs batch il faut tous les enlever de là
                    if index[0] == 0:
                        self.renderer.scene.delete_chunk_batch(index[1])
                    else:
                        self.renderer.scene.delete_water_batch(index[1])
                self.rendered_chunks_positions.remove(chunk_pos)
                self.rendered_chunks.pop(chunk_pos)
                if chunk_pos in data_manager.changed_chunks:  # Si le chunk a été modifié, il faut le sauvegarder
                    data_manager.save_chunk(chunk_pos)
                del chunk

    def gen_chunks(self):
        """
        Demande à générer tous les chunks en distance de génération
        """
        player_chunk = self.player.chunk

        batch = []  # On va faire un envoi par batch
        for chunk in self.relative_chunks_to_generate:  # On itère sur les chunks en distance de génération
            chunk_absolute = (chunk[0] + player_chunk[0],
                              chunk[1] + player_chunk[1])
            # Si le chunk n'a pas encore été généré on le demande
            if chunk_absolute not in data_manager.generated_chunks:
                batch.append([chunk_absolute, 1])
        data_manager.send_batch(batch)

    def chunk_loop(self, unload=True, generate=True):
        """
        Ceci est la boucle runtime pour tout ce qui concerne les chunks
        """
        if generate:
            self.gen_chunks()
            self.structure_scan()
        self.load_chunks(unload, generate)

    def click(self, event):
        """
        Cette fonction est appellée lors d'un click en pygame
        """
        if self.running:  # Nous ne prenons le click en compte que si le jeu n'est pas en pause
            if event.button == 1:  # clic gauche
                self.break_block()  # On casse le bloc
            elif event.button == 3:  # clic droit
                self.place_block()  # On place un bloc

    def break_block(self):
        """
        Fonction appellée lors d'un clic gauche du joueur, qui va casser le bloc devant celui-ci
        """
        if self.lookat is not None:  # Un bloc est dans notre champ de vision
            # Le chunk est affiché (on ne doit pas pouvoir casser un bloc non affiché)
            if self.lookat[0] in self.rendered_chunks_positions:
                # On récupère l'objet chunk
                chunk = self.rendered_chunks[self.lookat[0]]
                data_manager.change_in_chunks(
                    *self.lookat[0], self.lookat[1], 0)  # On change la chunk en ram

                # On récupère les blocs additionnels qui sont alors visibles(quand on creuse, des blocs sont dévoilés)
                changes = fast_renderables.cassage(
                    self.lookat[1], self.lookat[0])
                for change in changes:
                    updated_chunk = change[0]
                    # Si le changement a eu lieu dans une chunk à l'écran
                    if updated_chunk in self.rendered_chunks_positions:
                        change_chunk = self.rendered_chunks[updated_chunk]
                        block = (*change[1], change[2])
                        # Si le bloc n'est pas celui que nous venons de casser et si il n'est pas déjà dans la chunk
                        if block not in change_chunk.cubes_dynamic_set and block[:3] != self.lookat[1]:
                            change_chunk.add_block(block)
                            data_manager.change_in_chunks(
                                *updated_chunk, (change[1]), change[2])  # On change la chunk en ram
                # On supprime finalement le bloc de sa chunk
                chunk.delete_block((*self.lookat[1], self.lookat[2]))
                self.renderer.scene.sort_waters(self.player.chunk) # Si le bloc casse a mis à jour des blocs transparents

    def place_block(self):
        """
        Fonction appellée lors d'un placement de bloc.
        Cette fonction placera un bloc dans la direction dans laquelle le joueur regarde
        """
        if self.lookat is not None:  # Nous regardons en effet un bloc
            # Nous ne savons que quel bloc nous *regardons*,
            # il nous faut donc savoir de quel côté de ce dernier placer le bloc
            # Nous allons donc vérifier avec la dernière direction qui a été traversée
            match self.lookat[3]:
                case -1:  # nous avons traversé -x en dernier
                    to_place = (self.lookat[0][0]*16+self.lookat[1][0]+1,
                                self.lookat[0][1]*16+self.lookat[1][1], self.lookat[1][2])
                case 1:  # nous avons traversé +x en dernier
                    to_place = (self.lookat[0][0]*16+self.lookat[1][0]-1,
                                self.lookat[0][1]*16+self.lookat[1][1], self.lookat[1][2])
                case -2:  # nous avons traversé -y en dernier
                    to_place = (self.lookat[0][0]*16+self.lookat[1][0],
                                self.lookat[0][1]*16+self.lookat[1][1]+1, self.lookat[1][2])
                case 2:  # nous avons traversé +y en dernier
                    to_place = (self.lookat[0][0]*16+self.lookat[1][0],
                                self.lookat[0][1]*16+self.lookat[1][1]-1, self.lookat[1][2])
                case -3:  # nous avons traversé -z en dernier
                    to_place = (self.lookat[0][0]*16+self.lookat[1][0],
                                self.lookat[0][1]*16+self.lookat[1][1], self.lookat[1][2]+1)
                case 3:  # nous avons traversé +z en dernier
                    to_place = (self.lookat[0][0]*16+self.lookat[1][0],
                                self.lookat[0][1]*16+self.lookat[1][1], self.lookat[1][2]-1)
            # Le chunk du bloc à placer
            to_place_chunk = (to_place[0]//16, to_place[1]//16)
            # ce même chunk mais en coordonnées relatives
            to_place_relative = (to_place[0] %
                                 16, to_place[1] % 16, to_place[2])
            if to_place_chunk in self.rendered_chunks_positions:
                # Nous récupérons l'objet chunk si celui-ci existe
                chunk = self.rendered_chunks[to_place_chunk]

                # Nous vérifions que le joueur ait bien le droit de placer le bloc à cet endroit
                placed_hitbox1, placed_hitbox2 = to_place[:3], [
                    to_place[i] + settings.CUBE_SIDELENGTH for i in range(3)]  # La hitbox du cube
                if (*to_place_relative, self.lookat[2]) not in chunk.cubes_dynamic_set and\
                        0 < to_place[2] < settings.WORLD_HEIGHT and\
                        not self.player.colliding(placed_hitbox1, placed_hitbox2):
                    # Si le bloc n'existe pas encore, si 0<hauteur<world limit
                    # et si le joueur ne collsisionne pas avec la hitbox du cube
                    # alors nous récupérons le type de bloc sélectionné dans la hotbar
                    block_id = settings.tex_vers_id[self.hbcounter +
                                                    8*self.hblevel]  # La hotbar a un sélectionneur et plusieurs niveaux
                    # On aojoute le bloc
                    chunk.add_block((*to_place_relative, block_id))
                    data_manager.change_in_chunks(
                        *to_place_chunk, to_place_relative, block_id)  # On change la chunk en ram
                    # On change les renderables en ram
                    data_manager.change_in_renderables(
                        *to_place_chunk, block=(*to_place_relative, block_id))

                    # Au cas où ce soit un bloc transparent, nous trions ceux-ci
                    self.renderer.scene.sort_waters(self.player.chunk)

    def hb_select(self):
        """
        Cette fonction va permettre de traiter les touches nécéssitées pour changer de bloc sélectionné
        dans la hotbar, ainsi que de changer les uniforms dans les shaders correspondants pour afficher
        le changement
        """
        if prefs.HB_L_K in self.pressed_keys:  # La touche pour aller vers la gauche dans la hotbar
            self.hbcounter -= 1
            self.hbcounter %= 8  # le compteur de hotbar fonctionne avec une arithmétique mod 8
            self.renderer.shader_manager.update_uniform(
                "hbselection", "SelectionIndex", np.uint8(self.hbcounter))  # Nous bougeons le carré blanc
            # Ce n'est que sur appui que cette fonction est appellée
            self.pressed_keys.remove(prefs.HB_L_K)
        elif prefs.HB_R_K in self.pressed_keys:  # La touche pour aller vers la droite d\ans la hotbar
            self.hbcounter += 1
            self.hbcounter %= 8
            self.renderer.shader_manager.update_uniform(
                "hbselection", "SelectionIndex", np.uint8(self.hbcounter))
            self.pressed_keys.remove(prefs.HB_R_K)
        elif prefs.HB_U_K in self.pressed_keys:  # On change de hotbar
            self.hblevel = 1 - self.hblevel  # Il y a deux niveaux
            self.renderer.shader_manager.update_uniform(
                "hotbar", "HotbarOffset", np.int8(self.hblevel))  # On change de hotbar
            # Ce n'est que sur appui que cette fonction est appellée
            self.pressed_keys.remove(prefs.HB_U_K)
        elif prefs.HB_D_K in self.pressed_keys:
            self.hblevel = 1 - self.hblevel
            self.renderer.shader_manager.update_uniform(
                "hotbar", "HotbarOffset", np.int8(self.hblevel))
            self.pressed_keys.remove(prefs.HB_D_K)

    def physics_loop(self, deltatime=0):
        """
        Ceci est la fonction qui effectue tous les changements physiques, inclus le mouvement, la gravité etc...
        Elle est appellée dans self.run
        :param deltatime: le temps élapsé depuis le dernier frame afin d'avoir un mouvement plus uniforme
        """
        # On calcule le mouvement de la souris
        mouse_movement = (
            current_mouse.position[0]-self.pg_win_middle[0], current_mouse.position[1]-self.pg_win_middle[1])
        # On place la souris au centre de l'écran
        current_mouse.position = self.pg_win_middle
        # On calcule la quantité de mouvement basée sur une constante et le deltatime
        movement = settings.MOVECONST*deltatime
        if movement > 0.3:  # On cap pour éviter de traverser des blocs
            movement = 0.3

        # ----------TRAITEMENT DE TOUCHES----------------

        # On bouge ici le joueur
        if prefs.FORWARD_K in self.pressed_keys:
            self.player.move([0, movement, 0])
        if prefs.LEFT_K in self.pressed_keys:
            self.player.move([-movement, 0, 0])
        if prefs.RIGHT_K in self.pressed_keys:
            self.player.move([movement, 0, 0])
        if prefs.BACK_K in self.pressed_keys:
            self.player.move([0, -movement, 0])

        if self.flying:  # Si nous volons,il faut monter continûment
            if prefs.UP_K in self.pressed_keys:
                self.player.move([0, 0, movement])
                # On fait un check de speed_y>0 dans la physique pour éviter de monter à traveres des blocs
                self.player.speed_y = 0.1
        else:
            if prefs.UP_K in self.pressed_keys:
                if self.player.can_jump:  # Si nous pouvons sauter, faisons cela!
                    jump_by = settings.JUMPCONST
                    if jump_by > 0.8:
                        # cappons le saut (nous ne pouvons le capper de plus puisque la hitbox fait 1.8 de haut)
                        jump_by = 0.8
                    self.player.speed_y = jump_by
                    self.player.can_jump = False
                elif self.player.in_water:
                    # Nous n'avons pas de moment, les méchaniques sont celles du vol moins puissant
                    self.player.position[2] += 0.3*movement

        if prefs.DOWN_K in self.pressed_keys and self.flying:  # Si nous volons et voulons descendre, faisons cela!
            self.player.move([0, 0, -movement])
            self.player.speed_y = 0

        self.player.simulatePhysics(
            deltatime=deltatime, gravity=not self.flying)  # On simule la physique du joueur

        # on calcule l'angle de rotation pour l'angle alpha à partir du mouvement de la souris (et de sa sensitivité)
        alpha_turn = -settings.TURNCONST * \
            deltatime * \
            mouse_movement[0] * prefs.SENSITIVITY
        self.player.turn(alpha_turn)
        self.fpcamera.turn(alpha_turn)
        # on calcule l'angle de rotation pour l'angle beta à partir du mouvement de la souris
        beta_turn = -settings.TURNCONST * deltatime * mouse_movement[1] * prefs.SENSITIVITY
        self.player.turn(0, beta_turn)
        self.fpcamera.turn(0, beta_turn)
        self.lookat = self.player.look_at_block(
            5)  # On récupère le bloc regardé

    def run(self, max_fps):
        """
        La boucle maître qui éxécutera le jeu
        :param max_fps: le nombre max de fps atteignables
        """

        # Le renderer doit savoir qu'il est en train de fonctionner Ceci ne changera pas même quand le jeu sera en pause
        self.renderer.running = True
        if self.running:
            # On cache la souris au début si le jeu n'est pas en pause
            pg.mouse.set_visible(False)
            current_mouse.click(mouse.Button.left)
        
        # On met en place les water batchs
        self.renderer.scene.sort_waters(self.player.chunk)

        while 1:  # Plus rapide que while True

            # Pygame.clock.tick nous renvoie le deltatime
            deltatime = self.renderer.clock.tick(max_fps)

            for event in pg.event.get():  # Tous les évènements pygame
                if event.type == pg.QUIT:
                    self.renderer.end()
                    raise Exception("Ending the World")
                elif event.type == pg.MOUSEBUTTONDOWN:
                    self.click(event)
                elif event.type == pg.KEYDOWN:
                    if event.key == prefs.PAUSE_K:  # On met le jeu en pause/on dépause
                        self.running = not self.running
                        if self.running:  # Si le jeu était en pause et ne l'est plus
                            # on remet la souris au milieu de l'écran
                            current_mouse.position = self.pg_win_middle
                            pg.mouse.set_visible(False)  # et on la cache
                        else:  # Dans l'autre cas on montre la souris
                            pg.mouse.set_visible(True)
                        # PAUSE_K + QUIT_K correspondent à la séquence pour quitter le jeu
                        if prefs.QUIT_K in self.pressed_keys:
                            self.renderer.end()
                            raise Exception("Ending the World")
                    elif event.key == prefs.FLYING_K:
                        self.player.speed_y = 0  # Tout moment est perdu
                        self.player.can_jump = False  # donc le joueur ne peut pas sauter
                        self.flying = not self.flying
                    else:
                        # Dans un cas normal, on ajoute la touche à la liste de touches appuyées
                        self.pressed_keys.add(event.key)

                # ONLY_ON_PRESS_KEYS : {FLYING_K, PAUSE_K, HB_L_K, HB_R_K, HB_U_K, HB_D_K}
                elif event.type == pg.KEYUP and event.key not in prefs.ONLY_ON_PRESS_KEYS:
                    # les ONLY_ON_PRESS_KEYS ne sont pas ajoutées au set
                    # (exception pour les HB mais voir self.hb_select)
                    if event.key in self.pressed_keys:
                        # On peut enlever les autres
                        self.pressed_keys.remove(event.key)

                elif event.type == pg.VIDEORESIZE:
                    # Lors d'un resize de fenêtre il faut mettre àa jour tous les aspect ratio
                    aspect_ratio = event.w/event.h
                    self.fpcamera.inverse_aspect_ratio = 1/aspect_ratio
                    self.renderer.shader_manager.update_uniform(
                        "cross", "AspectRatio", np.float32(aspect_ratio))
                    self.renderer.shader_manager.update_uniform(
                        "hotbar", "AspectRatio", np.float32(aspect_ratio))
                    self.renderer.shader_manager.update_uniform(
                        "hbselection", "AspectRatio", np.float32(aspect_ratio))

                elif event.type == pg.WINDOWMOVED:
                    # Il faut changer la variable du milieu de l'écran si nous le bouogeons
                    # On récupère la position absolue de la fenêtre pygame
                    window_position = GetWindowRect(
                        FindWindow(None, pg.display.get_caption()[0]))
                    self.pg_win_middle = (int((window_position[0]+window_position[2])/2), int(
                        (window_position[1]+window_position[3])/2))  # On calcule le milieu de la fenêtre
                    
            self.update_shaders()  # On met à jour les uniforms des shader
            self.renderer.render()
            # Afin d'avoir les messages les plus récents on lit ceux-ci depuis le data_manager
            data_manager.read_messages()
            if self.previous_player_chunk != self.player.chunk:
                self.previous_player_chunk = self.player.chunk
                # la chunk du joueur est nécéssaire pour la transparence 
                self.renderer.scene.sort_waters(self.player.chunk)
                self.chunk_loop(True, True)  # On éxécute la boucle des chunks
            else:
                self.chunk_loop(False, True)  # On éxécute la boucle des chunks, mais sans besoin de générer, puisque nous n'avons pas fait de changement de chunk

            if self.running:  # Si le jeu n'est pas en pause, on fait la physique et la sélection
                self.physics_loop(deltatime)
                self.hb_select()
                pg.display.set_caption(
                    f"PyCraft - fps: {self.renderer.clock.get_fps().__round__(1)}")  # On met le titre
            else:
                # On met le nom de la fenêtre
                pg.display.set_caption("Jeu en pause")

