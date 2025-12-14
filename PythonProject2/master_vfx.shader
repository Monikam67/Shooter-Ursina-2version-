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

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main()
{
    vec2 uv0 = uv;
    vec3 col;

    float intensity = base_intensity;

    float scanline = sin(uv.y * 1200.0 + time * 300.0) * 0.04 * intensity;

    float jitter = sin(time * 20.0) * 0.003 * intensity;
    uv0.y += jitter;

    float ca_offset = 0.003 * intensity;

    float r = texture(tex, uv0 + vec2(ca_offset, 0)).r;
    float g = texture(tex, uv0).g;
    float b = texture(tex, uv0 - vec2(ca_offset, 0)).b;

    col = vec3(r, g, b);

    float noise_val = rand(vec2(uv.x * time, uv.y * time * 0.5));
    col += (noise_val - 0.5) * 0.25 * intensity;

    if (intensity > 0.01) {
        col.r += 0.3 * intensity;
        col.g -= 0.2 * intensity;
        col.b -= 0.25 * intensity;
    }

    col -= scanline;

    if (intensity > 1.0) {
        float extra_intensity = intensity - 1.0;

        col.r += 0.4 * extra_intensity;
        col.g -= 0.3 * extra_intensity;
        col.b -= 0.35 * extra_intensity;

        float extra_noise = rand(vec2(uv.x * time * 2.0, uv.y * time));
        col += (extra_noise - 0.5) * 0.2 * extra_intensity;

        float extra_distortion = sin(uv.y * 8.0 + time * 5.0) * 0.01 * extra_intensity;
        uv0.x += extra_distortion;

        float extra_scanline = sin(uv.y * 800.0 + time * 200.0) * 0.03 * extra_intensity;
        col -= extra_scanline;
    }

    if (reload_strength > 0.001)
    {
        float reload = reload_strength;

        // 🔴 КРАСНАЯ ТЕМА - усиливается с общей интенсивностью
        vec3 reload_color = vec3(0.8, 0.1, 0.1) * (1.0 + intensity * 0.5);

        // 📊 ПОЛОСКА ПРОГРЕССА СНИЗУ (ОТ ЛЕВОГО КРАЯ К ПРАВОМУ)
        float progress_bar = uv.y < 0.02 ? 1.0 : 0.0;

        // ЗАМЕДЛЕНИЕ В 2.5 РАЗА
        float slow_reload = reload;

        // ПРАВИЛЬНОЕ НАПРАВЛЕНИЕ: от левого края к правому
        progress_bar *= step(uv.x, slow_reload);

        // Красная полоса прогресса (ДОБАВЛЯЕМ к существующему цвету)
        col += reload_color * progress_bar * 0.8;

        // Белый кончик полосы (на правом конце полоски)
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

        // ДОБАВЛЯЕМ красный круг к существующему цвету
        col += reload_color * circle * 0.6;

        // 🔴 КРАСНЫЕ ЧАСТИЦЫ В КРУГЕ
        float particles = rand(vec2(angle * 10.0, time * 5.0));
        particles = step(0.7, particles) * circle * reload;
        col += vec3(1.0, 0.3, 0.3) * particles * 0.4;

        // 🌊 ЛЕГКОЕ КРАСНОЕ ИСКАЖЕНИЕ (усиливается с интенсивностью)
        float distortion = sin(uv.y * 10.0 + time * 3.0) * 0.002 * reload * (1.0 + intensity);
        uv0.x += distortion;

        // 🔴 КРАСНЫЙ ШУМ (ДОБАВЛЯЕМ к существующему цвету)
        float reload_noise = rand(uv * 3.0 + time * 5.0) * reload * 0.1 * (1.0 + intensity * 0.5);
        col += vec3(reload_noise * 0.5, 0.0, 0.0);

        // 🔴 МИГАНИЕ В КОНЦЕ ПЕРЕЗАРЯДКИ (ДОБАВЛЯЕМ к существующему цвету)
        if (reload > 0.9) {
            float blink = sin(time * 15.0) * 0.3 + 0.7;
            col += reload_color * blink * (reload - 0.9) * 3.0;
        }
    }

    if (grenade_effect > 0.001)
    {
        float grenade = grenade_effect;

        // 🔴 КРАСНАЯ ВСПЫШКА - СОХРАНЯЕМ оригинальный красный эффект
        vec2 center = vec2(0.5, 0.5);
        float dist = length(uv - center);

        // 1. КРАСНАЯ ВСПЫШКА (основной эффект - ДОБАВЛЯЕМ к цвету)
        float red_flash = (1.0 - dist * 2.0) * grenade * 0.5 * (1.0 + intensity * 0.5);
        red_flash = max(0.0, red_flash);

        // Добавляем красный эффект (как в оригинале)
        col += vec3(red_flash * 0.8, red_flash * 0.1, red_flash * 0.1);

        // 2. ⚡ ЯРКАЯ БЕЛАЯ ВСПЫШКА В ЦЕНТРЕ (ПОВЕРХ красного)
        float white_flash = exp(-dist * 25.0) * grenade * 2.0;

        // Добавляем белую вспышку ПОВЕРХ красного (только центр)
        col += vec3(white_flash * 1.0, white_flash * 0.9, white_flash * 0.7);

        // 3. ⚡ ВСПЫШКА СВЕТА ПО ВСЕМУ ЭКРАНУ (кратковременная, ПОВЕРХ всего)
        float screen_flash = smoothstep(0.1, 0.0, dist * 2.5) * grenade * 1.0;
        col += vec3(screen_flash * 0.9, screen_flash * 0.8, screen_flash * 0.6);

        // 4. 🌟 БЛИКИ ВОКРУГ ЦЕНТРА (поверх красного)
        float glare = sin(atan(uv.y - center.y, uv.x - center.x) * 8.0 + time * 10.0) * 0.5 + 0.5;
        glare *= exp(-dist * 12.0) * grenade * 0.5;
        col += vec3(glare * 1.0, glare * 0.9, glare * 0.8);

        // 5. 💥 УСИЛЕННОЕ ИСКАЖЕНИЕ ВОЛНОЙ ОТ ВЗРЫВА
        float wave_distortion = sin(dist * 40.0 - time * 30.0) * 0.015 * grenade * (1.0 + intensity);
        uv0.x += wave_distortion;
        uv0.y += wave_distortion * 0.7;

        // 6. Искажение усиливается с интенсивностью
        float distortion = sin(uv.y * 25.0 + time * 30.0) * 0.01 * grenade * (1.0 + intensity);
        uv0.x += distortion;

        // 7. 🔴 КРАСНОЕ СМЕЩЕНИЕ ЦВЕТА (усиливаем красный)
        float red_shift = grenade * 0.3 * (1.0 + intensity * 0.3);
        col.r += red_shift * 0.9;
        col.g -= red_shift * 0.5;
        col.b -= red_shift * 0.6;

        // 8. Смешиваем с текстурой (но сохраняем наши эффекты)
        vec3 grenade_tex = texture(tex, uv0).rgb;
        col = mix(col, grenade_tex, 0.8);
    }

    //===========================================================================
    // SHOOT EFFECT (тряска и разрывы - усиливаются с интенсивностью)
    //===========================================================================

    if (shoot_strength > 0.001)
    {
        vec2 shake;
        shake.x = sin(time * 200.0) * 0.003 * shoot_strength * (1.0 + intensity);
        shake.y = cos(time * 180.0) * 0.003 * shoot_strength * (1.0 + intensity);

        vec2 uv_shake = uv0 + shake;

        float sshift = 0.006 * shoot_strength * (1.0 + intensity);

        float rr = texture(tex, uv_shake + vec2(sshift, 0)).r;
        float gg = texture(tex, uv_shake).g;
        float bb = texture(tex, uv_shake - vec2(sshift, 0)).b;

        vec3 shoot_col = vec3(rr, gg, bb);

        // Применяем красный оттенок (усиливается с интенсивностью)
        shoot_col.r += 0.3 * intensity;
        shoot_col.g -= 0.2 * intensity;
        shoot_col.b -= 0.25 * intensity;

        // Легкое затемнение вместо осветления
        shoot_col *= (1.0 - shoot_strength * 0.08);

        col = mix(col, shoot_col, 0.5 * shoot_strength);
    }

    //===========================================================================
    // WALK EFFECT (легкая тряска - усиливается с интенсивностью)
    //===========================================================================

    if (walk_strength > 0.001)
    {
        float walk_shake = sin(time * 8.0) * 0.001 * walk_strength * (1.0 + intensity * 0.5);
        uv0.x += walk_shake;

        vec3 walk_col = texture(tex, uv0).rgb;
        col = mix(col, walk_col, 0.2 * walk_strength);
    }

    //===========================================================================
    // ULTRAKILL GLITCH TEARING (частые разрывы - усиливаются с интенсивностью)
    //===========================================================================

    float glitch_frequency = 50.0 * (1.0 + intensity);
    float glitch = step(0.97, rand(vec2(time * glitch_frequency, uv.y * 1000.0)));

    if (glitch > 0.5)
    {
        float off = rand(vec2(uv.y * 500.0, time)) * 0.03 * (1.0 + intensity);

        vec3 gcol = vec3(
            texture(tex, uv + vec2(off, 0)).r,
            texture(tex, uv).g,
            texture(tex, uv - vec2(off, 0)).b
        );

        gcol.r += 0.3 * intensity;
        gcol.g -= 0.2 * intensity;
        gcol.b -= 0.25 * intensity;

        col = mix(col, gcol, 0.6);
    }

    //===========================================================================
    // FINISH
    //===========================================================================

    col = clamp(col, 0.0, 1.0);
    color = vec4(col, 1.0);
}