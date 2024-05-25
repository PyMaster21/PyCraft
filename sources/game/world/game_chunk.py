"""
Cette fonction contient le chunk, une classe permettant de lier un array
(issu d'un fichier) à des chunkbatchs du côté rendering
Ceci permet donc effectivement d'afficher le terrain généré à l'écran
"""
import game.settings as settings
import game.rendering.chunk_batch as chunk_batch
import game.rendering.water_batch as water_batch

import random


class Chunk:
    def __init__(self, position, block_array):
        """
        La classe chunk permet de manipuler des blocs aisément en manipulant des tronçons (chunk en anglais)
        :param position: la position du chunk en coordonnées chunks
        :param block_array: un np.array contenant les blocs (x,y,z,id) 
        """
        self.position = position
        self.blocks = set()
        self.blocks_transp = []

        for block in block_array:  # Ce vilain d'Arthur a de vilains duplicats
            if block[3] == settings.BLOC_VERS_ID["eau"] or block[3] == settings.BLOC_VERS_ID["verre"]:
                self.blocks_transp.append(tuple(block))
            else:
                self.blocks.add(tuple(block))
        # les indices dans le chunkbatch de chacun des blocs (chunk_batch_local_id, cube_in_batch_id)
        # avec le chunk_batch_local_id partant de 0 à n pour le nième chunkbatch crée
        self.cube_indices = []
        self.cube_indices_transp = [] # Pareil pour les blocs transparents
        self.cubes_dynamic = []  # Les blocs correctement affichables, et différents de l'air
        self.cubes_dynamic_transp = []  # Les blocs correctement affichables, et différents de l'air
        # Le set des cubes_dynamic, utilisé pour effectuer "in", qui est plus rapide avec des ensembles
        self.cubes_dynamic_set = set()
        self.chunkbatches = []  # Les différents chunkbatches du chunk
        self.transparent_batches = []  # Les différents batchs de blocs transparents du chunk
        self.renderer = None
        self.total_space = 0  # L'espace total disponible, en blocs
        self.total_space_transp = 0  # L'espace total disponible, en blocs, pour les transparents
        self.indices = set()  # Les indices des chunkbatchs dans leur scène

    def load_to_screen(self, renderer):
        """
        Met les cubes dans un chunkbatch
        :param renderer: le renderer dans lequel mettre les blocs
        :return self.index: l'indice du chunkbatch
        """
        self.renderer = renderer
        # On crée le chunkbatch
        self.chunkbatches.append(chunk_batch.ChunkBatch(
            renderer.ctx, renderer.shader_manager["cube"], self.position, len(self.blocks)+settings.CHUNK_BLOCK_MARGIN))
        self.transparent_batches.append(chunk_batch.ChunkBatch(
            renderer.ctx, renderer.shader_manager["transparent_cube"], self.position, len(self.blocks_transp)+settings.CHUNK_BLOCK_MARGIN))
        batch = []  # Le batch que nous mettrons dans le chunkbatch
        transp_batch = []  # Le batch de blocs transparents
        for cube in self.blocks:
            if cube[3] in settings.id_vers_tex:  # Le bloc a un id non corrompu
                self.cubes_dynamic.append(cube)
                self.cubes_dynamic_set.add(cube)
                batch.append((int(cube[0]), int(cube[1]), int(
                    cube[2]), settings.id_vers_tex[cube[3]]))
            elif cube[3] == 0:  # C'est de l'air
                continue
            else:
                self.cubes_dynamic.append(cube)
                self.cubes_dynamic_set.add(cube)
                batch.append((int(cube[0]), int(cube[1]), int(
                    cube[2]), random.randint(0, 7))) # On met un bloc au hasard pour voir le bug
        for cube in self.blocks_transp:
            self.cubes_dynamic_transp.append(cube)
            self.cubes_dynamic_set.add(cube)
            transp_batch.append((int(cube[0]), int(cube[1]), int(
                cube[2]), settings.id_vers_tex[cube[3]]))

        # On récupère les indices des cubes
        self.cube_indices = [(0, i)
                             for i in self.chunkbatches[-1].push_cubes(batch)]
        # On récupère les indices des cubes transparents
        self.cube_indices_transp = [(0, i)
                             for i in self.transparent_batches[-1].push_cubes(transp_batch)]
        # On récupère l'espace total disponible
        self.total_space = len(self.blocks)+settings.CHUNK_BLOCK_MARGIN
        self.total_space_transp = len(self.blocks_transp)+settings.CHUNK_BLOCK_MARGIN

        self.indices.add((0,renderer.scene.add_chunk_batch(
            self.chunkbatches[-1])))  # On ajoute le chunkbatch
        self.indices.add((1,renderer.scene.add_water_batch(
            self.transparent_batches[-1])))  # On ajoute le chunkbatch
            

    def add_block(self, block):
        """
        Ajoute un bloc au chunkbatch
        :param block: le tuple (relx, rely, z, type)
        """
        print(block)

        # Il nous reste de l'espace, le -8 est dû à un bug assez étrange (voir la doc)
        if block[3] == settings.BLOC_VERS_ID["eau"] or block[3] == settings.BLOC_VERS_ID["verre"]:  # Un bloc transparent
            if len(self.cube_indices_transp) < self.total_space_transp-8:
                print("RIEMANN1", len(self.cube_indices_transp), self.total_space_transp)
                index = self.transparent_batches[-1].add_cube(int(block[0]), int(
                    block[1]), int(block[2]), settings.id_vers_tex[block[3]])
                # On ajoute le bloc au chunkbatch
                self.cube_indices_transp.append((len(self.transparent_batches)-1, index))
                self.cubes_dynamic_transp.append(block)
                self.cubes_dynamic_set.add(block)
            else:  # On crée un nouveau chunkbatch
                self.transparent_batches.append(chunk_batch.ChunkBatch(
                    self.renderer.ctx, self.renderer.shader_manager["transparent_cube"], self.position, settings.CHUNK_BLOCK_MARGIN))
                self.indices.add((
                    1,self.renderer.scene.add_water_batch(self.transparent_batches[-1])))
                self.total_space_transp += settings.CHUNK_BLOCK_MARGIN
                self.add_block(block)  # On fait une jolie petite récursion
        else:
            if len(self.cube_indices) < self.total_space-8:
                print("RIEMANN2", len(self.cube_indices), self.total_space)
                if block[3] in settings.id_vers_tex:  # Le bloc a un id existant
                    index = self.chunkbatches[-1].add_cube(int(block[0]), int(
                        block[1]), int(block[2]), settings.id_vers_tex[block[3]])
                else:
                    index = self.chunkbatches[-1].add_cube(int(block[0]), int(
                        block[1]), int(block[2]), random.randint(0, 7))
                # On ajoute le bloc au chunkbatch
                self.cube_indices.append((len(self.chunkbatches)-1, index))
                self.cubes_dynamic.append(block)
                self.cubes_dynamic_set.add(block)
            else:  # On crée un nouveau chunkbatch  
                self.chunkbatches.append(chunk_batch.ChunkBatch(
                    self.renderer.ctx, self.renderer.shader_manager["cube"], self.position, settings.CHUNK_BLOCK_MARGIN))
                self.indices.add((
                    0,self.renderer.scene.add_chunk_batch(self.chunkbatches[-1])))
                self.total_space += settings.CHUNK_BLOCK_MARGIN
                self.add_block(block)  # On fait une jolie petite récursion

    def delete_block(self, block):
        """
        Supprime le bloc de l'écran
        :param block: le tuple (x,y,z,type)
        """
        if block in self.cubes_dynamic_set:
            if block[3] == settings.BLOC_VERS_ID["eau"] or block[3] == settings.BLOC_VERS_ID["verre"]:  # Un bloc transparent
                index = self.cubes_dynamic_transp.index(block)
                self.cubes_dynamic_set.remove(self.cubes_dynamic_transp.pop(index))
                to_del = self.cube_indices_transp.pop(index)
                self.transparent_batches[to_del[0]].delete_cube(to_del[1])
                self.total_space_transp-=1
            else:
                index = self.cubes_dynamic.index(block)
                self.cubes_dynamic_set.remove(self.cubes_dynamic.pop(index))
                to_del = self.cube_indices.pop(index)
                self.chunkbatches[to_del[0]].delete_cube(to_del[1])
                self.total_space-=1
