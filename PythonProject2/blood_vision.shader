uniform sampler2D tex;
uniform float intensity;    // 0.0 - 1.0
uniform float time;

in vec2 uv;
out vec4 color;

void main() {
    vec4 original = texture(tex, uv);

    // Кроваво-красный оттенок
    float redBoost = intensity * 0.8;
    float greenLoss = intensity * 0.4;
    float blueLoss = intensity * 0.6;

    vec3 bloodColor = vec3(
        original.r + redBoost,
        original.g * (1.0 - greenLoss),
        original.b * (1.0 - blueLoss)
    );

    // Кровавая виньетка
    float dist = distance(uv, vec2(0.5));
    float vignette = smoothstep(0.5, 1.0 - intensity * 0.8, dist);
    bloodColor *= vignette;

    color = vec4(bloodColor, 1.0);
}