
import moderngl as mgl
import pygame as pg
from game.rendering.scene import Scene
from game.rendering.shader_manager import ShaderManager
from game.settings import *  # star importing since only constants are defined here


class Renderer:
    """Une classe qui gère les graphismes"""

    def __init__(self):
        # Initialise pygame si ce n'est pas déjà fait
        if not pg.get_init():
            pg.init()

        # Indique que le contexte graphique OpenGL doit être de version 3.3
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 3)

        # Active les fonctionnalités coeur OpenGL
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)

        self.window_dimensions = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.screen = pg.display.set_mode(self.window_dimensions, flags=pg.OPENGL | pg.DOUBLEBUF | pg.RESIZABLE)

        # Associe le contexte OpenGL et le contexte moderngl
        self.ctx = mgl.create_context()

        # Active les fonctionnalités spécifiques
        self.ctx.enable(mgl.BLEND | mgl.DEPTH_TEST | mgl.CULL_FACE)
        self.ctx.gc_mode = None

        # Change l'épaisseur des lignes à 5
        self.ctx.line_width = 5.0

        self.shader_manager = ShaderManager(self.ctx)
        self.scene: Scene = Scene()  # default empty scene

        self.clock = pg.time.Clock()
        self.running = False

    def bind_scene(self, scene):
        """Permet de lier une scène"""
        self.scene = scene

    def render(self):
        """Dessine la nouvelle image à l'écran"""
        self.ctx.clear(color=BACKGROUND_COLOUR)
        self.scene.render()
        pg.display.flip()

    def end(self):
        """Cette fonction est appellée lorsque le jeu se termine. Elle libère les resources et ferme le programme"""
        self.running = False

        # Supprime les éléments de la scène
        self.scene.release()

        # Supprime le contexte OpenGL
        self.ctx.release()

        # Quitte pygame et ferme le programme
        pg.quit()
