

from moderngl import Context, NEAREST
import pygame as pg


class TextureAtlas:
    """Une classe qui permet de charger et d'utiliser une texture sous forme d'atlas de texture"""
    def __init__(self, ctx: Context, filepath):
        """
        :param ctx: Le contexte graphique OpenGL
        :param filepath: Le chemin du fichier de la texture
        """

        # charge la texture avec pygame
        texture = pg.image.load(filepath)

        # Description du format du fichier de texture
        # Le fichier est RGB => rouge-vert-bleu, et a donc 3 nombres pour décrire la couleur (num_channels)
        image_format = "RGB"
        num_channels = 3

        """
        Le commentaire 'noinspection PyTypeChecker' désactive une option de mon IDE
        ligne # 1 :
        créer une texture dans la mémoire GPU:
        texture.get_size() : les dimensions de la texture
        data : les données de la texture. La fonction tostring convertit la texture en type python 'bytes', 
        le type que requière la méthode 'texture' de l'objet ctx
        """

        # noinspection PyTypeChecker
        self.texture = ctx.texture(texture.get_size(), num_channels, data=pg.image.tostring(texture, image_format))  # 1

        # Change le mode de filtre OpenGL.
        # Le mode de filtre est la manière dont les pixels sont affichés
        self.texture.filter = (NEAREST, NEAREST)

        # Crée des mipmaps de la texture. Il s'agit de copie de la texture avec une résolution de plus en plus basse
        self.texture.build_mipmaps()

        # Change le mode de filtre OpenGL.
        # Le mode de filtre est la manière dont les pixels sont affichés
        # La méthode build_mipmaps() change ce paramètre, c'est pour cela qu'il faut le refaire
        self.texture.filter = (NEAREST, NEAREST)

    def use_texture(self, location):
        """
        :param location: La localisation de la texture dans le contexte OpenGL.
        permet d'indiquer quelle texture utiliser lors de l'affichage.
        """
        self.texture.use(location)
