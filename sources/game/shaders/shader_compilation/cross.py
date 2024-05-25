"""
Ce fichier est celui qui a été utilisé pour compiler du code python
en glsl, pour le shader cross, soit celui utilisé pour la croix grise
au centre de la fenêtre. Cette compilation a lieu grâce au module
shaderdef à https://pypi.org/project/shaderdef/
Nous avons récupéré le code glsl compilé dans la console de ce
code une fois éxécuté
"""
from shaderdef import (AttributeBlock, FragmentShaderOutputBlock,
                       ShaderDef, ShaderInterface, UniformBlock)

from shaderdef.glsl_types import vec2, vec4


class VsIn(AttributeBlock):
    pos = vec2()

class VsOut(ShaderInterface):
    gl_Position = vec4()

class VsUniform(UniformBlock):
    AspectRatio = float()


def vert_shader(vsin: VsIn, uniform: VsUniform) -> VsOut:
    return VsOut(gl_Position=vec4(vsin.pos.x, vsin.pos.y * AspectRatio, -0.999, 1.0))

class FsOut(FragmentShaderOutputBlock):
    colour = vec4()

def frag_shader() -> FsOut:
    return FsOut(colour=vec4(0.8, 0.8, 0.8, 1.0))

def print_shaders():
    sdef = ShaderDef(vert_shader=vert_shader, frag_shader=frag_shader)
    sdef.translate()

    print('\nvertex shader:')
    print('--------------')
    print(sdef.vert_shader)
    print('\nfragment shader:')
    print('----------------')
    print(sdef.frag_shader)


if __name__ == '__main__':
    print_shaders()

"""
Out de console:


#version 330 core
uniform float AspectRatio;
layout(location=0) in vec2 pos;
void main() {
    gl_Position = vec4(vsin.pos.x, (vsin.pos.y * AspectRatio), -0.999, 1.0);
}

fragment shader:
----------------
#version 330 core
layout(location=0) out vec4 colour;
void main() {
    colour = vec4(0.8, 0.8, 0.8, 1.0);
}
"""
