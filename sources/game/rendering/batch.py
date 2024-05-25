

from moderngl import Context, Program
import numpy as np


class Batch:
    """Une classe qui lie des données et des programmes GPU"""
    def __init__(self,
                 ctx: Context,
                 shader: Program,
                 buffer_size: int,
                 vertex_format: str,
                 attributes: list | tuple,
                 index_element_size: int,
                 vertices_per_object: int,
                 dynamic: bool = True
                 ):
        # Le contexte graphique OpenGL
        self.ctx = ctx

        # Le programme (shader) GPU qui va utiliser les données contenue dans l'attribut vbo
        # pour afficher des choses à l'écran
        self.shader = shader

        # La quantité de mémoire GPU à réserver
        self.buffer_size = buffer_size

        # Bool : Considérer ou non la mémoire GPU comme dynammique.
        # Cela a un impact sur les performances d'écriture et de lecture de la mémoire
        self.dynamic = dynamic

        # Décrit le(s) type(s) de données stockées dans la mémoire GPU.
        self.vertex_format = vertex_format

        # Les attributs qui sont utilisés dans le shader
        self.attributes = attributes

        # La taille en octets des éléments de l' 'element buffer object' ou 'index buffer object'.
        self.index_element_size = index_element_size

        # Le nombre de sommets par élément de géométrie.
        self.vertices_per_object = vertices_per_object

        # créer les différents objets présents dans le GPU.
        self.ibo = self.create_ibo() if index_element_size != 0 else None
        self.vbo = self.create_vbo()
        self.vao = self.create_vao()

    def create_ibo(self):
        # Créer l'ibo (index buffer object) dans la mémoire GPU.
        # L'ibo indique quels sommets doivent être dessinés et dans quel ordre. Il est facultatif.
        return self.ctx.buffer(None, reserve=self.index_element_size * self.vertices_per_object, dynamic=self.dynamic)

    def create_vbo(self):
        # Créer le vbo (vertex buffer object) dans la mémoire GPU.
        # Le vbo contient les données des sommets.
        return self.ctx.buffer(None, reserve=self.buffer_size, dynamic=self.dynamic)

    def create_vao(self):
        # Créer le vao (vertex array object) dans la mémoire GPU
        # Le vao est est l'objet qui lie le vbo, l'ibo, et le shader
        return self.ctx.vertex_array(self.shader,
                                     [(self.vbo, self.vertex_format, *self.attributes)],
                                     index_buffer=self.ibo,
                                     index_element_size=self.index_element_size + 1)

    def update_vbo(self, data, offset: int):
        # Fonction pour modifier les données contenues dans le vbo, écrit 'data' dans le GPU,
        # à l'endroit indiqué par 'offset'
        self.vbo.write(data, offset=offset)

    def update_ibo(self, data, offset: int):
        # Fonction pour modifier les données contenues dans l'ibo, écrit 'data' dans le GPU,
        # à l'endroit indiqué par 'offset'
        self.ibo.write(data, offset=offset)

    def release(self):
        """
        Libére les resources utilisées par l'ibo, le vbo et le vao.
        Cet objet 'batch' est supprimé
        """
        if self.ibo is not None:
            self.ibo.release()
        self.vbo.release()
        self.vao.release()
        del self

    def render(self):
        # Afficher ce 'batch' à l'écran
        self.vao.render()
