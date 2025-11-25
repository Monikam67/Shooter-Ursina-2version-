#version 150

uniform sampler2D tex;
uniform float time;
uniform float shoot_strength;   // 0.0–1.0

in vec2 uv;
out vec4 color;

void main()
{
    float s = shoot_strength;

    // --- 1. Короткий "удар" камеры (увод UV назад от отдачи) ---
    vec2 recoil_offset = vec2(0.0, -0.015 * s);
    vec2 coords = uv + recoil_offset;

    // --- 2. Яркая белая вспышка ---
    float flash = smoothstep(0.0, 0.3, s);

    // --- 3. Усиленный хрома-шок ---
    float chroma = 0.008 * s;

    float r = texture(tex, coords + vec2(chroma, 0)).r;
    float g = texture(tex, coords).g;
    float b = texture(tex, coords - vec2(chroma, 0)).b;

    vec3 col = vec3(r, g, b);

    // --- 4. Перегрузка яркости ---
    col += flash * 0.8;

    // --- 5. Кровавый тон ---
    col.r += s * 0.15;
    col.g -= s * 0.05;
    col.b -= s * 0.1;

    color = vec4(col, 1.0);
}