#version 150

uniform sampler2D tex;
uniform float time;
uniform float reload_strength;   // 0.0–1.0

in vec2 uv;
out vec4 color;

void main()
{
    float s = reload_strength;

    // --- 1. Наклон (tilt) как движение камеры вручную ---
    float angle = 0.12 * s;
    mat2 rot = mat2(cos(angle), -sin(angle), sin(angle), cos(angle));

    vec2 centered = uv - 0.5;
    vec2 rotated = rot * centered;
    vec2 coords = rotated + 0.5;

    // --- 2. VHS WARP с вертикальным сжатием ---
    float warp = sin(uv.y * 25.0 + time * 15.0) * 0.02 * s;
    coords.x += warp;

    // --- 3. Хроматический сдвиг ---
    float chroma = 0.004 * s;

    float r = texture(tex, coords + vec2(chroma, 0)).r;
    float g = texture(tex, coords).g;
    float b = texture(tex, coords - vec2(chroma, 0)).b;

    vec3 col = vec3(r, g, b);

    // --- 4. Кровавый насыщенный оттенок ---
    col.r += s * 0.25;
    col.g -= s * 0.15;
    col.b -= s * 0.2;

    // --- 5. Дополнительная "грязь" VHS ---
    float noise = fract(sin(dot(uv * time * 20.0, vec2(45.12, 97.44))) * 10000.0);
    col += (noise - 0.5) * s * 0.15;

    color = vec4(col, 1.0);
}