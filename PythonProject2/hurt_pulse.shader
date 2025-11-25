#version 150

uniform sampler2D tex;
uniform float pulse;

in vec2 uv;
out vec4 color;

void main() {
    vec4 original = texture(tex, uv);
    float p = pulse * abs(sin(pulse * 10));

    vec3 redPulse = vec3(original.r + p * 0.8, original.g, original.b);

    color = vec4(redPulse, 1.0);
}