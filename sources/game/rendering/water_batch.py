
from game.rendering.batch import Batch
from moderngl import Context, Program, TRIANGLE_STRIP
from numpy import array, zeros, empty, uint32, int32


"""
Ce fichier contient la classe 'WaterBatch' extrêment similaire à la classe 'ChunkBatch'
C'est pourquoi ce fichier est un copié-collé du fichier 'chunk_batch', avec quelques modifications
Garder deux fichiers différents a l'avantage de permettre plus de changements et de modulabilité.

Pour plus de détails voir la classe 'ChunkBatch'.
"""


VERTEX_XYZ_COORD_LOOKUP = ((1, 1, 0), (1, 1, 0), (0, 1, 0), (1, 0, 0), (0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1),
                           (1, 1, 0), (1, 1, 1), (1, 0, 0), (1, 0, 1), (0, 0, 1), (1, 1, 1), (0, 1, 1), (0, 1, 1))
VERTEX_TEX_COORD_LOOKUP = (3, 3, 1, 2, 0, 1, 2, 3, 0, 1, 2, 3, 1, 2, 0, 0)


CUBE_FORMAT = "i4"
BYTES_PER_VERTEX = 4
CUBE_ATTRIBUTES = ("PackedData",)
VERTICES_PER_CUBE = 16

CUBE_SIZE = VERTICES_PER_CUBE * BYTES_PER_VERTEX


class WaterBatch(Batch):
    def __init__(self,
                 ctx: Context,
                 program: Program,
                 chunk_coord: tuple,
                 number_of_cubes: int):

        buffer_size = number_of_cubes * CUBE_SIZE
        super().__init__(ctx, program, buffer_size, CUBE_FORMAT, CUBE_ATTRIBUTES, 0, 0)

        self.buffer_size = buffer_size
        self.next_free_index = 0
        self.other_free_indices = []

        self.program = program
        self.chunk_coordinates = array(chunk_coord, dtype=int32)

    def add_cube(self, cube_x, cube_y, cube_z, tex):
        """
        Fonction pour ajouter un seul cube au vbo (vertex buffer object)
        Si de l'espace dans la mémoire est disponible "entre" deux cubes déjà existants, le cube sera placé à cet
        endroit pour éviter de gaspiller de la mémoire et de la fragmenter.

        Les coordonées (cube_x, cube_y, cube_z) représentent le coin inférieur gauche arrière du cube.
        Tex est la coordonné de texture dans l'atlas de textures
        """

        # Si la longueur de other_free_indices est > 0, autrement dit,
        # si de l'espace dans la mémoire est disponible "entre" deux cubes déjà existants ...
        if len(self.other_free_indices):
            # Récupère l'index de cet emplacement.
            index = self.other_free_indices.pop(0)
        else:
            # Sinon l'emplacement et le prochain emplacement libre, juste après le dernier utilisé
            index = self.next_free_index
            # Incrémente 'next_free_index' pour avoir l'index du prochain emplacement libre
            self.next_free_index += 1

        # Alloue un morceau de mémoire CPU dans lequel placer les données qui seront envoyés au GPU.
        vbo_data = empty(VERTICES_PER_CUBE, dtype=uint32)

        # Effectue un décalage de bits de 2 vers la 'gauche'
        # Cela a pour effet de multiplier 'tex' par 4.
        # L'idée est de laisser disponible les deux premiers bits de donnée pour autre chose.
        tex_with_offset = tex << 2

        # Boucle qui calcule les données stockées dans chaque sommet du cube
        for i in range(VERTICES_PER_CUBE):
            # Obtient le résultat de la table précalculée.
            xyz_offset = VERTEX_XYZ_COORD_LOOKUP[i]

            # calcule la position du sommet du cube
            x = cube_x + xyz_offset[0]
            y = cube_y + xyz_offset[1]
            z = cube_z + xyz_offset[2]

            # Organise les données que contient chaque sommet à l'aide de décalages de bits vers la 'gauche'
            # La coordonnée 'z' du cube est stockée du bit 18 au bit 31 inclus
            # La coordonnée 'y' du cube est stockée du bit 13 au bit 17 inclus
            # La coordonnée 'x' du cube est stockée du bit 8 au bit 12 inclus
            # Le numéro de texture du cube est stockée du bit 2 au bit 7 inclus
            # Les coordonnées de texture du cube sont stockées dans les bits 0 et 1
            vbo_data[i] = (((z << 10) + (y << 5) + x) << 8) + tex_with_offset + VERTEX_TEX_COORD_LOOKUP[i]

        # Ecrit les données du cube dans le GPU.
        self.update_vbo(vbo_data, index * CUBE_SIZE)

        # Renvoie là où les données ont été écrites sous forme d'index
        return index

    def push_cubes(self, cubes_data):
        """
        Fonction pour ajouter plusieurs cubes au vbo (vertex buffer object)
        Si de l'espace dans la mémoire est disponible "entre" deux cubes déjà existants, les cubes ne seront 
        pas placé à cet endroit pour des raisons de performances.

        cubes_data : un 'tuple' ou une 'list' de cubes sous la forme (cube_x, cube_y, cube_z, tex)

        Les coordonées (cube_x, cube_y, cube_z) représentent le coin inférieur gauche arrière du cube.
        Tex est la coordonné de texture dans l'atlas de textures
        """

        # Cela peut ammener à un léger gain de performances dut au fonctionnement de l'interpréteur python
        # Plus précisément, l'interpréteur python n'aura pas à accéder au variables globales.
        vertices_per_cube = VERTICES_PER_CUBE

        # Alloue un morceau de mémoire CPU dans lequel placer les données qui seront envoyés au GPU.
        vbo_data = empty(len(cubes_data) * vertices_per_cube, dtype=uint32)

        # Décalage à effectuer au moment d'écrire les données dans le GPU.
        memory_offset_index = self.next_free_index

        # La fonction renvoie un tuple d'indices qui représentent là où chaque cube a été écrit en mémoire GPU.
        # Au lieu de créer une liste et d'y ajouter le nouvel index pour chaque cube, puisque le nombre de
        # cube ajoutés et connu avant l'ajout, les indices peuvent êtres 'calculés' à l'avance
        indices = tuple(range(self.next_free_index, self.next_free_index + len(cubes_data)))
        self.next_free_index += len(cubes_data)

        # Calcule les données de chaque cube
        for index, data in enumerate(cubes_data):
            # Effectue un décalage de bits de 2 vers la 'gauche'
            # Cela a pour effet de multiplier data[3], qui représente le numéro d etexture, par 4.
            # L'idée est de laisser disponible les deux premiers bits de donnée pour autre chose.
            tex_with_offset = data[3] << 2

            # Cette boucle est exactement la même que celle dans la fonction 'add_cube'
            # Mis à part la ligne marquée par deux étoiles (**)
            for i in range(vertices_per_cube):
                xyz_offset = VERTEX_XYZ_COORD_LOOKUP[i]

                x = data[0] + xyz_offset[0]
                y = data[1] + xyz_offset[1]
                z = data[2] + xyz_offset[2]

                # ** La seule chose qui change est l'endroit où les données du cube sont écrites
                # dans la mémoire CPU, pour s'adapter au fait qu'il n'y a pas un, mais plusieurs cubes.
                vbo_data[index * vertices_per_cube + i] = \
                    (((z << 10) + (y << 5) + x) << 8) + tex_with_offset + VERTEX_TEX_COORD_LOOKUP[i]

        # Ecrit au début du morceau de mémoire innocupée
        self.update_vbo(vbo_data, memory_offset_index * CUBE_SIZE)
        return indices

    def edit_cube(self, cube_x, cube_y, cube_z, index):
        vbo_data = empty(VERTICES_PER_CUBE, dtype=uint32)

        for i in range(VERTICES_PER_CUBE):
            xyz_offset = VERTEX_XYZ_COORD_LOOKUP[i]

            x = cube_x + xyz_offset[0]
            y = cube_y + xyz_offset[1]
            z = cube_z + xyz_offset[2]

            vbo_data[i] = (((z << 10) + (y << 5) + x) << 8) + VERTEX_TEX_COORD_LOOKUP[i]

        self.update_vbo(vbo_data, index * CUBE_SIZE)

    def delete_cube(self, index):
        """
        Supprime le cube à l'index spécifié.
        Cela à pour effet de fragmenter la mémoire GPU, autrement dit, un morceau de mémoire localement
        continu sera séparé en deux, et de l'espace sera disponible entre ces deux blocs de mémoire.
        La function add_cube lutte contre cet effet
        """

        # Marque cet index comme étant libre
        self.other_free_indices.append(index)

        # Ecrit des zéros dans la mémoire GPU. Cela a pour effet de supprimé le cube.
        self.update_vbo(zeros(VERTICES_PER_CUBE, dtype=int32), index * CUBE_SIZE)

    def render(self):
        self.program["chunk_coordinates"].write(self.chunk_coordinates)
        self.vao.render(mode=TRIANGLE_STRIP)
