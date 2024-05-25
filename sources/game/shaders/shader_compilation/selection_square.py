"""
Ce fichier est celui qui a été utilisé pour compiler du code python
en glsl, pour le shader selection_square, soit celui utilisé pour 
sélectionner un bloc Cette compilation a lieu grâce au module
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
    SelectionIndex = int()
    AspectRatio = float()


def vert_shader(vsin: VsIn, uniform: VsUniform) -> VsOut:
    position = vec2(pos + vec2(SelectionIndex * 0.2, 0))
    return VsOut(gl_Position=vec4(position.x / AspectRatio, position.y, -0.999, 1.0))

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


vertex shader:
--------------
#version 330 core
uniform int SelectionIndex;
uniform float AspectRatio;
layout(location=0) in vec2 pos;
void main() {
    vec2 position = vec2((pos + vec2((SelectionIndex * 0.2), 0)));
    gl_Position = vec4((position.x / AspectRatio), position.y, -0.999, 1.0);
}

fragment shader:
----------------
#version 330 core
layout(location=0) out vec4 colour;
void main() {
    colour = vec4(0.8, 0.8, 0.8, 1.0);
}
"""
