#version 150

uniform sampler2D tex;
uniform float power;
uniform float time;

in vec2 uv;
out vec4 color;

void main() {
    float wave = sin(uv.y * 40 + time * 25) * 0.001 * power;
    vec2 distorted = uv + vec2(wave, 0);

    color = texture(tex, distorted);
}