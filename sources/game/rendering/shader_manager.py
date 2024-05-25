

from moderngl import Program


class ShaderManager:
    """Une classe qui gère les shaders"""
    def __init__(self, ctx):
        # Le contexte graphique OpenGL
        self.ctx = ctx

        # Un dictionnaire qui en clef le nom d'un programme GPU et en valeur le programme GPU correspondant
        self._programs: dict[str] = {}

    def __getitem__(self, shader_name) -> Program:
        """
        Permet d'utiliser la syntaxe '[]' pour accéder aux shaders contenus dans le ShaderManager

        Exemple, pour accéder à un programme nommé "test", on peut écrire:
        programme_test = ShaderManager[test]

        au lieu de:
        programme_test = ShaderManager._programs[test]
        """
        return self._programs[shader_name]

    def create_program(self, program_name, vertex_shader, fragment_shader):
        # Créer un programme GPU nommé 'program_name'
        # vertex_shader : le code du 'vertex shader' OpenGL
        # fragment_shader : le code du 'fragment shader' OpenGL
        self._programs[program_name] = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

    def delete_program(self, program_name):
        """Supprime le programme nommé 'program_name'"""
        program = self._programs.pop(program_name)
        program.release()

    def delete_all(self):
        """Supprime tous les programmes GPU"""
        for program in self._programs.values():
            program.release()

        self._programs.clear()

    def update_uniform(self, shader_name: str, uniform: str, data):
        """Modifier un seul 'uniform'"""
        self._programs[shader_name][uniform].write(data)

    def update_uniforms(self, shader_name: str, uniforms: list[str], data):
        """Modifier plusieurs 'uniform' d'un même programme GPU"""
        program = self._programs[shader_name]
        for i, uniform in enumerate(uniforms):
            program[uniform].write(data[i])
