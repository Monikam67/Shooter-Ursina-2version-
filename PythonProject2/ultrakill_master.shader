#version 130

uniform sampler2D tex;
uniform float time;
uniform float base_intensity;
uniform float shoot_strength;
uniform float reload_strength;

in vec2 uv;
out vec4 color;

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main() {
    // Базовые интенсивности
    float base_red = base_intensity;
    float shoot = shoot_strength * 1.5;
    float reload = reload_strength * 1.5;

    // ЭФФЕКТ СТРЕЛЬБЫ (отдельный)
    vec2 shoot_uv = uv;

    // Сильная тряска при стрельбе
    float shake_x = sin(time * 150.0) * 0.03 * shoot;
    float shake_y = cos(time * 130.0) * 0.025 * shoot;
    shoot_uv += vec2(shake_x, shake_y);

    // VHS эффект - полосы и искажения
    float vhs_distortion = sin(uv.y * 40.0 + time * 15.0) * 0.015 * shoot;
    shoot_uv.x += vhs_distortion;

    // Получаем исходный цвет
    vec4 original = texture(tex, shoot_uv);

    // БАЗОВЫЙ КРАСНЫЙ ЭФФЕКТ
    vec3 red_tint = vec3(1.0, 0.1, 0.1); // очень сильный красный
    vec3 base_col = mix(original.rgb, original.rgb * red_tint, base_red);

    // ЭФФЕКТ СТРЕЛЬБЫ - только затемнение и тряска
    vec3 shoot_col = base_col;

    // Сильное затемнение при стрельбе
    float darken = 0.4; // затемнение на 40%
    shoot_col *= (1.0 - shoot * darken);

    // ТОЛЬКО ТЕМНЫЕ ПОМЕХИ (без светлых)
    // Темный шум (инвертированный)
    float dark_noise = (1.0 - rand(uv * time * 400.0)) * shoot * 0.4;
    shoot_col -= dark_noise * 0.3;

    // Темные горизонтальные линии (VHS помехи)
    float dark_line = mod(uv.y * 0.3 + time * 3.0, 0.08) < 0.01 ? shoot * 0.5 : 0.0;
    shoot_col -= dark_line * 0.4;

    // Темные полосы сканирования
    float dark_scan = sin(uv.y * 800.0 + time * 100.0) * 0.1 * shoot;
    shoot_col -= max(0.0, dark_scan) * 0.2; // только положительные значения (темные)

    // Разрывные помехи (глитч)
    float glitch = rand(vec2(time * 10.0, uv.y)) > 0.7 ? shoot * 0.8 : 0.0;
    shoot_col.r -= glitch * 0.5;

    // Смещение цветов (только для красного канала)
    float rgb_shift = sin(time * 80.0) * 0.01 * shoot;
    float r_shift = texture(tex, shoot_uv + vec2(rgb_shift, 0)).r;
    shoot_col.r = mix(shoot_col.r, r_shift, shoot * 0.3);

    // Смешиваем эффекты
    vec3 final_col = mix(base_col, shoot_col, shoot);

    // Хроматическая аберрация для перезарядки
    float reload_off = 0.004 * reload;
    if (reload > 0.0) {
        float r = texture(tex, uv + vec2(reload_off, 0)).r;
        float g = texture(tex, uv).g;
        float b = texture(tex, uv - vec2(reload_off, 0)).b;
        vec3 reload_col = vec3(r, g, b) * red_tint;
        final_col = mix(final_col, reload_col, reload);
    }

    // Гарантируем преобладание красного и темные тона
    final_col.r = max(final_col.r, final_col.g * 1.5);
    final_col.r = max(final_col.r, final_col.b * 1.5);

    // Дополнительное затемнение красного канала
    final_col.r *= 0.9;

    color = vec4(final_col, 1.0);
}