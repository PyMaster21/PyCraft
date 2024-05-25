"""
Ce fichier est celui qui a été utilisé pour compiler du code python
en glsl, pour le shader cube_with_shadows, soit celui utilisé pour 
les blocs, qui ont des ombres(ils n'en avaient pas avant)
Cette compilation a lieu grâce au module
shaderdef à https://pypi.org/project/shaderdef/
Nous avons récupéré le code glsl compilé dans la console de ce
code une fois éxécuté, et l'avons modifié en optimisant:
--le chunk_coordinates qui est passé d'un vec2 à un ivec2 (ce sont des nombres entiers)
--les const float LookupX/Y/Z ont été ajoutés après puisque shaderdef ne pouvait pas les compiler
--les /2**n ont été remplacés par des >> n (shaderdef crashait si nous essayions de mettre des décalages de bits)
--Les %2**n ont été remplacés par des &(2**n-1) (shaderdef crashait sinon)
--Nous avons rajouté les crochets pour faire DirX/Y/Z = LookupX/Y/Z[LookupIndex];

Dans le fragment shader
Nous avons rajouté
--uniform sampler2D TextureAtlas;  le sampler2D n'est pas un type de shaderdef
--const vec3 light_source = normalize(vec3(1.0, 2.0, -3.0)); shaderdef n'aime pas les consts
-- nous avons rajouté un vec2 uv devant uv (ça ne marche pas sinon)
"""
from shaderdef import (AttributeBlock, FragmentShaderOutputBlock,
                       ShaderDef, ShaderInterface, UniformBlock)

from shaderdef.glsl_types import vec2, vec3, vec4, mat3, mat4, Array16


class VsIn(AttributeBlock):
    PackedData = int()

class VsOut(ShaderInterface):
    gl_Position = vec4()
    TexCoordinates = vec2()
    TextureIndex = float()
    DirX = float()
    DirY = float()
    DirZ = float()

class VsUniform(UniformBlock):
    chunk_coordinates = vec2()
    cam_pos = vec3()
    m_proj = mat4()
    alpha_rot = mat3()
    beta_rot = mat3()

def vert_shader(vsin: VsIn, uniform: VsUniform) -> VsOut:
    position = vec3(float(chunk_coordinates.x * int(16) + ((PackedData /256) % int(32))),
                         float(chunk_coordinates.y * int(16) + ((PackedData / 8192) % int(32))),
                         float((PackedData / 262144)))

    LookupIndex = gl_VertexID % int(16)
    return VsOut(gl_Position=m_proj * vec4(beta_rot * alpha_rot * (position - cam_pos), 1.0),
    TexCoordinates=vec2(float((PackedData / 2) % int(2)) / 17.0, float(PackedData % int(2))),
    TextureIndex=float((PackedData /4) % int(64)),
    DirX = LookupX[LookupIndex],
    DirY = LookupY[LookupIndex],
    DirZ = LookupZ[LookupIndex])

class FsIn(ShaderInterface):
    TexCoordinates = vec2()
    TextureIndex = float()
    DirX = float()
    DirY = float()
    DirZ = float()
    
class FsOut(FragmentShaderOutputBlock):
    colour = vec4()


def frag_shader(fs_in:FsIn) -> FsOut:
    normal = normalize(vec3(round(DirX * 1.001), round(DirY * 1.001), round(DirZ * 1.001)))
    lighting = float(((dot(normal, light_source) + 1.0) / 2.0) + 0.2)
    lighting = clamp(lighting, 0.0, 1.0)

    uv = vec2(TextureIndex / 17.0, 0.0) + TexCoordinates
    return FsOut(colour=vec4(texture(TextureAtlas, uv).rgb * lighting, 1.0))

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
Out de Console:

vertex shader:
--------------
#version 330 core
uniform vec2 chunk_coordinates;
uniform vec3 cam_pos;
uniform mat4 m_proj;
uniform mat3 alpha_rot;
uniform mat3 beta_rot;
layout(location=0) in int PackedData;
out VsOut {
    vec2 TexCoordinates;
    float TextureIndex;
    float DirX;
    float DirY;
    float DirZ;
} vs_out;
void main() {
    vec3 position = vec3(float(((chunk_coordinates.x * int(16)) + ((PackedData / 256) % int(32)))), float(((chunk_coordinates.y * int(16)) + ((PackedData / 8192) % int(32)))), float((PackedData / 262144)));  
    LookupIndex = (gl_VertexID % int(16));
    gl_Position = (m_proj * vec4(((beta_rot * alpha_rot) * (position - cam_pos)), 1.0));
    vs_out.TexCoordinates = vec2((float(((PackedData / 2) % int(2))) / 17.0), float((PackedData % int(2))));
    vs_out.TextureIndex = float(((PackedData / 4) % int(64)));
    vs_out.DirX = LookupXLookupIndex;
    vs_out.DirY = LookupYLookupIndex;
    vs_out.DirZ = LookupZLookupIndex;
}

fragment shader:
----------------
#version 330 core
in FsIn {
    vec2 TexCoordinates;
    float TextureIndex;
    float DirX;
    float DirY;
    float DirZ;
} fs_in;
layout(location=0) out vec4 colour;
void main() {
    normalize normal = normalize(vec3(round((DirX * 1.001)), round((DirY * 1.001)), round((DirZ * 1.001))));
    float lighting = float((((dot(normal, light_source) + 1.0) / 2.0) + 0.2));
    clamp lighting = clamp(lighting, 0.0, 1.0);
    uv = (vec2((TextureIndex / 17.0), 0.0) + TexCoordinates);
    colour = vec4((texture(TextureAtlas, uv).rgb * lighting), 1.0);
}
"""
