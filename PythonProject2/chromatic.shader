#version 150

uniform sampler2D tex;
uniform float offset;

in vec2 uv;
out vec4 color;

void main() {
    vec2 rUV = uv + vec2(offset, 0);
    vec2 gUV = uv;
    vec2 bUV = uv - vec2(offset, 0);

    float r = texture(tex, rUV).r;
    float g = texture(tex, gUV).g;
    float b = texture(tex, bUV).b;

    color = vec4(r, g, b, 1.0);
}