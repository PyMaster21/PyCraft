"""
Ce fichier contient les codes glsl utilisés pour les shaders. C'est la seule manière
pour discuter avec le GPU, CEPENDANT pour rester conforme aux règles du concours, avons essayé de ne pas 
coder ces shaders, mais plutôt utiliser une librairie annexe pour les compiler 
(shaderdef) à https://pypi.org/project/shaderdef/
Les fichiers utilisés pour la compilation peuvent être trouvés à shaders/shader_compilation
ATTENTION
Les shaders ci-dessous ne sont pas dans leur forme compilée pure.
Nous les avons en effet légèrement modifiés pour soit fonctionner (c'est quand même mieux) 
ou être optimisés ou encore être plus lisibles (donc réarrangé)
Nous les avons également réarrangés, et enlevé tous les vsin.qqch  (voir les versions compilées)
ainsi qu'enlevé les groupes out VsOut pour mettre des out devant chaque paramètre out (cela ne marchait pas sinon)
Pareil pour les FsIn, mais avec in plutot que out
Nous avons aussi enlevé les layout(location = n) pour les out dans les fragment
Lors de plus grands changements, nous l'écrirons dans le fichier utilisé pour la compilation du shader
À nouveau, il n'y a pas de méthode autre qui permette une discussion avec de GPU, et nous avons fait de notre mieux
pour restreindre l'utilisation de glsl
"""

cross_vert = """
#version 330 core
layout (location = 0) in vec2 pos;
uniform float AspectRatio;
void main() {
    gl_Position = vec4(pos.x, pos.y * AspectRatio, -0.999, 1.0);
}"""
cross_frag = """
#version 330 core
layout (location = 0) out vec4 colour;
void main() {
    colour = vec4(0.8, 0.8, 0.8, 1.0);
}
"""
cube_with_shadows_vert = """#version 330 core

layout (location = 0) in int PackedData;

out vec2 TexCoordinates;
out float TextureIndex;

out float DirX;
out float DirY;
out float DirZ;


uniform ivec2 chunk_coordinates;
uniform vec3 cam_pos;
uniform mat4 m_proj;
uniform mat3 alpha_rot;
uniform mat3 beta_rot;


const float LookupX[16] = float[](-0.5, -0.5, 0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5);
const float LookupY[16] = float[](0.5, 0.5, 0.5, -0.5, -0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, -0.5, -0.5, 0.5, 0.5, 0.5);
const float LookupZ[16] = float[](0.5, 0.5, 0.5, 0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, -0.5, -0.5, -0.5, -0.5);


void main() {
    vec3 position = vec3(float(chunk_coordinates.x * int(16) + ((PackedData >> 8) & int(31))),
                         float(chunk_coordinates.y * int(16) + ((PackedData >> 13) & int(31))),
                         float((PackedData >> 18)));


    gl_Position = m_proj * vec4(beta_rot * alpha_rot * (position - cam_pos), 1.0);
    TexCoordinates = vec2(float((PackedData >> 1) & int(1)) / 17.0, float(PackedData & int(1)));
    TextureIndex = float((PackedData >> 2) & int(63));

    int LookupIndex = gl_VertexID & int(15);

    DirX = LookupX[LookupIndex];
    DirY = LookupY[LookupIndex];
    DirZ = LookupZ[LookupIndex];
}"""
cube_with_shadows_frag = """#version 330 core

layout (location = 0) out vec4 colour;

in vec2 TexCoordinates;
in float TextureIndex;

in float DirX;
in float DirY;
in float DirZ;


uniform sampler2D TextureAtlas;


const vec3 light_source = normalize(vec3(1.0, 2.0, -3.0));


void main() {
    vec3 normal = normalize(vec3(round(DirX * 1.001), round(DirY * 1.001), round(DirZ * 1.001)));
    float lighting = ((dot(normal, light_source) + 1.0) / 2.0) + 0.2;
    lighting = clamp(lighting, 0.0, 1.0);

    vec2 uv = vec2(TextureIndex / 17.0, 0.0) + TexCoordinates;
    colour = vec4(texture(TextureAtlas, uv).rgb * lighting, 1.0);
}"""
hotbar_vert = """#version 330


layout (location = 0) in vec2 pos;
layout (location = 1) in vec2 TextureCoordinates;


out vec2 uv;


uniform float AspectRatio;
uniform int HotbarOffset;


void main() {
    uv = TextureCoordinates + vec2(HotbarOffset * 0.5, 0.0);
    gl_Position = vec4(pos.x / AspectRatio, pos.y, -0.998, 1.0);
}"""
hotbar_frag = """#version 330

layout (location = 0) out vec4 colour;

in vec2 uv;


uniform sampler2D TextureAtlas;


void main() {
    colour = vec4(texture(TextureAtlas, uv).rgb, 1.0);
}"""
selection_square_vert = """#version 330

layout (location = 0) in vec2 pos;


uniform int SelectionIndex;
uniform float AspectRatio;

void main() {
    vec2 position = pos + vec2(SelectionIndex * 0.2, 0);
    gl_Position = vec4(position.x / AspectRatio, position.y, -0.999, 1.0);
}"""
selection_square_frag = """#version 330


out vec4 colour;


void main() {
    colour = vec4(0.8, 0.8, 0.8, 1.0);
}"""
# Ce shader est essentiellement le même que cube_with_shadows (le frag diffère d'une valeur)
# Ainsi, nous n'avons pas compilé de shader en plus, et avons plutôt pris celui de cube_with_shadows, légèrement modifié

transparent_vert = """#version 330 core

layout (location = 0) in int PackedData;

out vec2 TexCoordinates;
out float TextureIndex;

out float DirX;
out float DirY;
out float DirZ;


uniform ivec2 chunk_coordinates;
uniform vec3 cam_pos;
uniform mat4 m_proj;
uniform mat3 alpha_rot;
uniform mat3 beta_rot;


const float LookupX[16] = float[](-0.5, -0.5, 0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5);
const float LookupY[16] = float[](0.5, 0.5, 0.5, -0.5, -0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, -0.5, -0.5, 0.5, 0.5, 0.5);
const float LookupZ[16] = float[](0.5, 0.5, 0.5, 0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, 0.5, -0.5, -0.5, -0.5, -0.5, -0.5);


void main() {
    vec3 position = vec3(float(chunk_coordinates.x * int(16) + ((PackedData >> 8) & int(31))),
                         float(chunk_coordinates.y * int(16) + ((PackedData >> 13) & int(31))),
                         float((PackedData >> 18)));


    gl_Position = m_proj * vec4(beta_rot * alpha_rot * (position - cam_pos), 1.0);
    TexCoordinates = vec2(float((PackedData >> 1) & int(1)) / 17.0, float(PackedData & int(1)));
    TextureIndex = float((PackedData >> 2) & int(63));

    int LookupIndex = gl_VertexID & int(15);

    DirX = LookupX[LookupIndex];
    DirY = LookupY[LookupIndex];
    DirZ = LookupZ[LookupIndex];
}"""
transparent_frag = """#version 330 core

layout (location = 0) out vec4 colour;

in vec2 TexCoordinates;
in float TextureIndex;

in float DirX;
in float DirY;
in float DirZ;


uniform sampler2D TextureAtlas;


const vec3 light_source = normalize(vec3(1.0, 2.0, -3.0));


void main() {
    vec3 normal = normalize(vec3(round(DirX * 1.001), round(DirY * 1.001), round(DirZ * 1.001)));
    float lighting = ((dot(normal, light_source) + 1.0) / 2.0) + 0.2;
    lighting = clamp(lighting, 0.0, 1.0);

    vec2 uv = vec2(TextureIndex / 17.0, 0.0) + TexCoordinates;
    colour = vec4(texture(TextureAtlas, uv).rgb * lighting, 0.4);
}"""

