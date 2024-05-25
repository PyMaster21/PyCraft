"""
Ce fichier est celui qui a été utilisé pour compiler du code python
en glsl, pour le shader hotbar, soit celui utilisé pour la barre de choix
de blocs. Cette compilation a lieu grâce au module
shaderdef à https://pypi.org/project/shaderdef/
Nous avons récupéré le code glsl compilé dans la console de ce
code une fois éxécuté

Dans le fragment shader
Nous avons rajouté
--uniform sampler2D TextureAtlas;  le sampler2D n'est pas un type de shaderdef

"""
from shaderdef import (AttributeBlock, FragmentShaderOutputBlock,
                       ShaderDef, ShaderInterface, UniformBlock)

from shaderdef.glsl_types import vec2, vec4


class VsIn(AttributeBlock):
    pos = vec2()
    TextureCoordinates = vec2()

class VsOut(ShaderInterface):
    gl_Position = vec4()
    uv = vec2()

class VsUniform(UniformBlock):
    AspectRatio = float()
    HotbarOffset = int()


def vert_shader(vsin: VsIn, uniform: VsUniform) -> VsOut:
    return VsOut(uv=TextureCoordinates + vec2(HotbarOffset * 0.5, 0.0),
    gl_Position=vec4(pos.x / AspectRatio, pos.y, -0.998, 1.0))

class FsOut(FragmentShaderOutputBlock):
    colour = vec4()

class FsIn(ShaderInterface):
    uv = vec2()

def frag_shader(fsin:FsIn) -> FsOut:
    return FsOut(colour=vec4(texture(TextureAtlas, uv).rgb, 1.0))

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
uniform float AspectRatio;
uniform int HotbarOffset;
layout(location=0) in vec2 pos;
layout(location=1) in vec2 TextureCoordinates;
out VsOut {
    vec2 uv;
} vs_out;
void main() {
    vs_out.uv = (TextureCoordinates + vec2((HotbarOffset * 0.5), 0.0));
    gl_Position = vec4((pos.x / AspectRatio), pos.y, -0.998, 1.0);
}

fragment shader:
----------------
#version 330 core
in FsIn {
    vec2 uv;
} fsin;
layout(location=0) out vec4 colour;
void main() {
    colour = vec4(texture(TextureAtlas, uv).rgb, 1.0);
}
"""
