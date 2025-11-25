#version 150

uniform sampler2D tex;
uniform float time;
uniform float base_intensity;
uniform float shoot_strength;
uniform float reload_strength;
uniform float walk_strength;
uniform float grenade_effect;

in vec2 uv;
out vec4 color;

// ===== СЛУЧАЙНАЯ ФУНКЦИЯ =====
float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main()
{
    vec2 uv0 = uv;
    vec3 col;

    //===========================================================================
    // 1) 📡 VHS BLOOD EFFECT (основной постоянный эффект)
    //===========================================================================

    float scanline = sin(uv.y * 1200.0 + time * 300.0) * 0.04 * base_intensity;

    float jitter = sin(time * 20.0) * 0.003 * base_intensity;
    uv0.y += jitter;

    float ca_offset = 0.003 * base_intensity;

    float r = texture(tex, uv0 + vec2(ca_offset, 0)).r;
    float g = texture(tex, uv0).g;
    float b = texture(tex, uv0 - vec2(ca_offset, 0)).b;

    col = vec3(r, g, b);

    // VHS noise/blood
    float noise_val = rand(vec2(uv.x * time, uv.y * time * 0.5));
    col += (noise_val - 0.5) * 0.25 * base_intensity;

    // Blood tint
    col.r += 0.3 * base_intensity;
    col.g -= 0.2 * base_intensity;
    col.b -= 0.25 * base_intensity;

    // Scanline overlay
    col -= scanline;

    //===========================================================================
// 2) 🔄 ULTRAKILL RELOAD EFFECT (сохраняем красный цвет)
//===========================================================================

if (reload_strength > 0.001)
{
    float reload = reload_strength;

    // 🔴 КРАСНАЯ ТЕМА - НИКАКОГО ОСВЕТЛЕНИЯ
    vec3 reload_color = vec3(0.8, 0.1, 0.1);

    // 📊 ПОЛОСКА ПРОГРЕССА СНИЗУ
    float progress_bar = uv.y < 0.02 ? 1.0 : 0.0;
    float slow_reload = reload * 0.67; // Замедление в 1.5 раза
    progress_bar *= step(uv.x, slow_reload);

    // Красная полоса прогресса
    col += reload_color * progress_bar * 0.8;

    // Белый кончик полосы
    float bar_tip = progress_bar * step(uv.x, slow_reload + 0.01) * step(slow_reload - 0.01, uv.x);
    col += vec3(1.0, 1.0, 1.0) * bar_tip * 0.5;

    // 🔴 ВРАЩАЮЩИЙСЯ КРУГ В ЦЕНТРЕ
    vec2 center = vec2(0.5, 0.5);
    float dist = length(uv - center);
    float angle = atan(uv.y - center.y, uv.x - center.x);

    // Красный круг с анимацией
    float circle = step(dist, 0.15) * step(0.12, dist); // Кольцо
    float rotating = sin(angle * 6.0 + time * 8.0) * 0.5 + 0.5;
    circle *= rotating * reload;

    col += reload_color * circle * 0.6;

    // 🔴 КРАСНЫЕ ЧАСТИЦЫ В КРУГЕ
    float particles = rand(vec2(angle * 10.0, time * 5.0));
    particles = step(0.7, particles) * circle * reload;
    col += vec3(1.0, 0.3, 0.3) * particles * 0.4;

    // 🌊 ЛЕГКОЕ КРАСНОЕ ИСКАЖЕНИЕ
    float distortion = sin(uv.y * 10.0 + time * 3.0) * 0.002 * reload;
    uv0.x += distortion;

    // 🔴 КРАСНЫЙ ШУМ
    float reload_noise = rand(uv * 3.0 + time * 5.0) * reload * 0.1;
    col += vec3(reload_noise * 0.5, 0.0, 0.0);

    // 🔴 МИГАНИЕ В КОНЦЕ ПЕРЕЗАРЯДКИ
    if (reload > 0.9) {
        float blink = sin(time * 15.0) * 0.3 + 0.7;
        col += reload_color * blink * (reload - 0.9) * 3.0;
    }

    // НЕ смешиваем с оригинальной текстурой - сохраняем красный цвет
    // Эффекты добавляются поверх существующего изображения
}

    //===========================================================================
    // 3) 💥 GRENADE EFFECT (минимальная красная вспышка)
    //===========================================================================

    if (grenade_effect > 0.001)
    {
        float grenade = grenade_effect;

        // 🔴 МАЛЕНЬКАЯ КРАСНАЯ ВСПЫШКА
        vec2 center = vec2(0.5, 0.5);
        float dist = length(uv - center);
        float flash = (1.0 - dist * 2.0) * grenade * 0.2;
        flash = max(0.0, flash);

        col += vec3(flash * 0.8, 0.0, 0.0);

        // Слабое искажение
        float distortion = sin(uv.y * 15.0 + time * 20.0) * 0.005 * grenade;
        uv0.x += distortion;

        vec3 grenade_tex = texture(tex, uv0).rgb;
        col = mix(col, grenade_tex, 0.9);
    }

    //===========================================================================
    // 4) ⚡ SHOOT EFFECT (тряска и разрывы)
    //===========================================================================

    if (shoot_strength > 0.001)
    {
        vec2 shake;
        shake.x = sin(time * 200.0) * 0.003 * shoot_strength;
        shake.y = cos(time * 180.0) * 0.003 * shoot_strength;

        vec2 uv_shake = uv0 + shake;

        float sshift = 0.006 * shoot_strength;

        float rr = texture(tex, uv_shake + vec2(sshift, 0)).r;
        float gg = texture(tex, uv_shake).g;
        float bb = texture(tex, uv_shake - vec2(sshift, 0)).b;

        vec3 shoot_col = vec3(rr, gg, bb);

        // Применяем красный оттенок
        shoot_col.r += 0.3 * base_intensity;
        shoot_col.g -= 0.2 * base_intensity;
        shoot_col.b -= 0.25 * base_intensity;

        // Легкое затемнение вместо осветления
        shoot_col *= (1.0 - shoot_strength * 0.08);

        col = mix(col, shoot_col, 0.5 * shoot_strength);
    }

    //===========================================================================
    // 5) 🚶 WALK EFFECT (легкая тряска)
    //===========================================================================

    if (walk_strength > 0.001)
    {
        float walk_shake = sin(time * 8.0) * 0.001 * walk_strength;
        uv0.x += walk_shake;

        vec3 walk_col = texture(tex, uv0).rgb;
        col = mix(col, walk_col, 0.2 * walk_strength);
    }

    //===========================================================================
    // 6) ⚡ ULTRAKILL GLITCH TEARING (частые разрывы)
    //===========================================================================

    float glitch = step(0.97, rand(vec2(time * 50.0, uv.y * 1000.0)));

    if (glitch > 0.5)
    {
        float off = rand(vec2(uv.y * 500.0, time)) * 0.03;

        vec3 gcol = vec3(
            texture(tex, uv + vec2(off, 0)).r,
            texture(tex, uv).g,
            texture(tex, uv - vec2(off, 0)).b
        );

        gcol.r += 0.3 * base_intensity;
        gcol.g -= 0.2 * base_intensity;
        gcol.b -= 0.25 * base_intensity;

        col = mix(col, gcol, 0.6);
    }

    //===========================================================================
    // FINISH
    //===========================================================================

    col = clamp(col, 0.0, 1.0);
    color = vec4(col, 1.0);
}