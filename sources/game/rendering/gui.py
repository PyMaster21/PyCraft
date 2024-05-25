

from moderngl import Context, LINES, TRIANGLE_STRIP, LINE_LOOP
from numpy import array, float32


class Gui:
    """Une classe qui affiche les éléments de l'interface utilisateur"""
    def __init__(self, ctx: Context, line_program, hot_bar_program, selection_square_program):
        # line_program, hot_bar_program, selection_square_program : Les différents programmes GPU.
        # Le contexte graphique OpenGL
        self.ctx = ctx

        # Les données qui représentent la croix centrale
        self.cross_buffer = ctx.buffer(array((0, 0.05, 0, -0.05, -0.05, 0, 0.05, 0), dtype=float32))

        # Le vao (vertex array object) qui permet de lier les données qui représentent la croix centrale
        # et le shader qui l'affiche
        self.cross_vao = ctx.vertex_array(line_program, self.cross_buffer, "pos")

        # Les données qui représentent la hotbar
        self.hot_bar_buffer = ctx.buffer(array((-0.8, -0.7, 0, 0, -0.8, -0.9, 0, 1,
                                                0.8, -0.7, 0.5, 0, 0.8, -0.9, 0.5, 1),
                                               dtype=float32))
        
        # Le vao qui permet de lier les données qui représentent la hotbar
        # et le shader qui l'affiche
        self.hot_bar_vao = ctx.vertex_array(hot_bar_program, self.hot_bar_buffer, "pos", "TextureCoordinates")

        # Les données qui représentent le carré de séléction
        self.selection_square_buffer = ctx.buffer(array((-0.8, -0.7, -0.8, -0.9, -0.6, -0.9, -0.6, -0.7),
                                                        dtype=float32))
        
        # Le vao qui permet de lier les données qui représentent le carré de séléction
        # et le shader qui l'affiche
        self.selection_square_vao = ctx.vertex_array(selection_square_program, self.selection_square_buffer, "pos")

    def draw_cross(self):
        # Dessine la croix centrale
        # le commentaire 'noinspection PyTypeChecker' désactive une option de mon IDE
        # noinspection PyTypeChecker
        self.cross_vao.render(mode=LINES)

    def draw_hot_bar(self):
        # Dessine la hotbar
        # le commentaire 'noinspection PyTypeChecker' désactive une option de mon IDE
        # noinspection PyTypeChecker
        self.hot_bar_vao.render(mode=TRIANGLE_STRIP)

    def draw_selection_square(self):
        # Dessine le carré de séléction
        # le commentaire 'noinspection PyTypeChecker' désactive une option de mon IDE
        # noinspection PyTypeChecker
        self.selection_square_vao.render(mode=LINE_LOOP)

    def render(self):
        # Dessine tous les éléments de l'interface utilisateur
        self.draw_cross()
        self.draw_hot_bar()
        self.draw_selection_square()

    def release(self):
        # Libère les ressources alloués pour les éléments de l'interface utilisateur
        self.cross_buffer.release()
        self.cross_vao.release()

        self.hot_bar_buffer.release()
        self.hot_bar_vao.release()

        self.selection_square_buffer.release()
        self.selection_square_vao.release()
