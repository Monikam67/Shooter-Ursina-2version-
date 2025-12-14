from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from random import uniform
import math
from ursina.audio import Audio
from panda3d.core import loadPrcFileData
import random
from ursina import application
from ursina import Shader
import os, sys

# ==================== НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ ====================
loadPrcFileData('', 'sync-video False')
loadPrcFileData('', 'clock-frame-rate 800')
loadPrcFileData('', 'show-frame-rate-meter True')


# ==================== ОПТИМИЗИРОВАННЫЕ СИСТЕМЫ ====================

# ==================== ОПТИМИЗИРОВАННЫЕ СИСТЕМЫ ====================

class ObjectManager:
    def __init__(self):
        self.all_entities = []
        self.cleanup_timer = 0
        self.cleanup_interval = 2.0

    def register(self, entity):
        if entity not in self.all_entities:
            self.all_entities.append(entity)

    def safe_destroy(self, entity):
        if not entity:
            return

        if hasattr(entity, 'animate'):
            entity.animate = None

        self.unregister(entity)

        if hasattr(entity, 'enabled') and entity.enabled:
            destroy(entity)

    def unregister(self, entity):
        if entity in self.all_entities:
            self.all_entities.remove(entity)

    def cleanup_dead_objects(self):
        initial_count = len(self.all_entities)
        alive_entities = []

        for entity in self.all_entities:
            if (entity and hasattr(entity, 'enabled') and entity.enabled and
                    hasattr(entity, 'position')):
                alive_entities.append(entity)
            else:
                if entity and hasattr(entity, 'enabled') and entity.enabled:
                    destroy(entity)

        self.all_entities = alive_entities
        cleaned = initial_count - len(self.all_entities)

        if cleaned > 0:
            print(f"🧹 Очищено {cleaned} мертвых объектов")

    def update(self):
        self.cleanup_timer += time.dt
        if self.cleanup_timer >= self.cleanup_interval:
            self.cleanup_dead_objects()
            self.cleanup_timer = 0


object_manager = ObjectManager()


class SafeEntity(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object_manager.register(self)

    def safe_destroy(self):
        object_manager.safe_destroy(self)


class ParticlePool:
    def __init__(self, template_func, initial_size=20, max_size=100):
        self.template_func = template_func
        self.max_size = max_size
        self.available = []
        self.in_use = []

        # Инициализируем начальный пул
        for _ in range(initial_size):
            particle = self._create_particle()
            if particle:
                self.available.append(particle)

    def _create_particle(self):
        try:
            particle = self.template_func()
            if particle:
                # Безопасно отключаем частицу
                if hasattr(particle, 'enabled'):
                    particle.enabled = False
                # Если это Entity, скрываем его
                if hasattr(particle, 'visible'):
                    particle.visible = False
                # Устанавливаем eternal=False для безопасного уничтожения
                if hasattr(particle, 'eternal'):
                    particle.eternal = False
            return particle
        except Exception as e:
            print(f"❌ Ошибка создания частицы в пуле: {e}")
            return None

    def get(self):
        """Получить частицу из пула"""
        # Сначала ищем в доступных
        while self.available:
            particle = self.available.pop()
            if particle and self._is_particle_valid(particle):
                try:
                    self._activate_particle(particle)
                    self.in_use.append(particle)
                    return particle
                except Exception as e:
                    print(f"❌ Ошибка активации частицы: {e}")
                    continue

        # Если нет доступных, создаем новую
        if len(self.in_use) < self.max_size:
            particle = self._create_particle()
            if particle and self._is_particle_valid(particle):
                try:
                    self._activate_particle(particle)
                    self.in_use.append(particle)
                    return particle
                except Exception as e:
                    print(f"❌ Ошибка активации новой частицы: {e}")

        # Если достигли максимума, переиспользуем старую
        if self.in_use:
            particle = self.in_use.pop(0)
            if particle and self._is_particle_valid(particle):
                try:
                    self._deactivate_particle(particle)
                    self._activate_particle(particle)
                    self.in_use.append(particle)
                    return particle
                except Exception as e:
                    print(f"❌ Ошибка переиспользования частицы: {e}")

        return None

    def _is_particle_valid(self, particle):
        """Проверяет, валидна ли частица"""
        if not particle:
            return False
        # Проверяем, не уничтожена ли сущность
        if hasattr(particle, '_destroyed') and particle._destroyed:
            return False
        return True

    def _activate_particle(self, particle):
        """Активирует частицу"""
        if hasattr(particle, 'enabled'):
            particle.enabled = True
        if hasattr(particle, 'visible'):
            particle.visible = True
        # Сбрасываем прозрачность
        if hasattr(particle, 'alpha'):
            particle.alpha = 1.0

    def _deactivate_particle(self, particle):
        """Деактивирует частицу"""
        if hasattr(particle, 'enabled'):
            particle.enabled = False
        if hasattr(particle, 'visible'):
            particle.visible = False

    def return_particle(self, particle):
        """Вернуть частицу в пул"""
        if not particle or not self._is_particle_valid(particle):
            return

        # Удаляем из используемых
        if particle in self.in_use:
            self.in_use.remove(particle)

        # Деактивируем
        self._deactivate_particle(particle)

        # Возвращаем в пул если есть место
        if len(self.available) < self.max_size:
            self.available.append(particle)
        else:
            # Если пул полон, уничтожаем частицу
            try:
                destroy(particle)
            except:
                pass

    def cleanup(self):
        """Очистка невалидных частиц"""
        # Очищаем доступные
        self.available = [p for p in self.available if self._is_particle_valid(p)]
        # Очищаем используемые
        self.in_use = [p for p in self.in_use if self._is_particle_valid(p)]


# Глобальные переменные для оптимизированных систем
optimized_systems_initialized = False
blood_pool = None
muzzle_flash_pool = None
animation_system = None


def init_optimized_systems():
    """Инициализирует все оптимизированные системы"""
    global optimized_systems_initialized, blood_pool, muzzle_flash_pool, animation_system

    if optimized_systems_initialized:
        return

    def create_blood_particle():
        """Создает одну частицу крови"""
        try:
            # Используем SafeEntity для всех частиц
            particle = SafeEntity(
                model='cube',
                color=color.rgba(0.6, 0, 0, 1),
                scale=0.2,
                add_to_scene_entities=True,
                eternal=False,  # Не eternal!
                enabled=False  # Начинаем отключенной
            )
            return particle
        except Exception as e:
            print(f"❌ Ошибка создания частицы крови: {e}")
            return None

    def create_muzzle_particle():
        """Создает одну частицу дульной вспышки"""
        try:
            particle = SafeEntity(
                model='cube',
                color=color.yellow,
                scale=0.05,
                add_to_scene_entities=True,
                eternal=False,  # Не eternal!
                enabled=False  # Начинаем отключенной
            )
            return particle
        except Exception as e:
            print(f"❌ Ошибка создания частицы вспышки: {e}")
            return None

    try:
        blood_pool = ParticlePool(create_blood_particle, 30, 100)
        muzzle_flash_pool = ParticlePool(create_muzzle_particle, 20, 50)

        class AnimationSystem:
            def __init__(self):
                self.animations = []

            def add_animation(self, obj, duration, update_func, on_finished=None):
                if not obj:
                    return None

                animation = {
                    'obj': obj,
                    'duration': duration,
                    'elapsed': 0,
                    'update_func': update_func,
                    'on_finished': on_finished,
                    'active': True
                }
                self.animations.append(animation)
                return animation

            def update(self):
                current_time = time.time()

                for anim in self.animations[:]:
                    if not anim['active']:
                        self.animations.remove(anim)
                        continue

                    anim['elapsed'] += time.dt

                    # Проверяем, существует ли объект
                    obj = anim['obj']
                    if not obj or not self._is_object_valid(obj):
                        anim['active'] = False
                        continue

                    progress = anim['elapsed'] / anim['duration']

                    if progress >= 1.0:
                        if anim['on_finished']:
                            try:
                                anim['on_finished']()
                            except Exception as e:
                                print(f"⚠️ Ошибка в on_finished: {e}")
                        anim['active'] = False
                    else:
                        if anim['update_func']:
                            try:
                                anim['update_func'](progress, obj)
                            except Exception as e:
                                print(f"⚠️ Ошибка в update_func: {e}")

                # Очищаем неактивные анимации
                self.animations = [anim for anim in self.animations if anim['active']]

            def _is_object_valid(self, obj):
                """Проверяет, валиден ли объект"""
                if not obj:
                    return False
                if hasattr(obj, '_destroyed') and obj._destroyed:
                    return False
                if hasattr(obj, 'enabled'):
                    return obj.enabled
                return True

        animation_system = AnimationSystem()
        optimized_systems_initialized = True
        print("✅ Оптимизированные системы инициализированы")

    except Exception as e:
        print(f"❌ Критическая ошибка инициализации оптимизированных систем: {e}")
        # Создаем простые системы в случае ошибки
        optimized_systems_initialized = False


# ==================== ОПТИМИЗИРОВАННЫЕ ВЕРСИИ ФУНКЦИЙ ====================

def create_blood_effect_optimized(position):
    """СУПЕР-ОПТИМИЗИРОВАННАЯ версия создания крови"""
    global blood_pool

    if not blood_pool:
        try:
            init_optimized_systems()
        except:
            print("❌ Не удалось инициализировать пул крови")
            return []

    if not blood_pool:
        print("❌ Пул крови не инициализирован")
        return []

    # ОГРАНИЧИВАЕМ количество частиц
    max_particles = 3  # Вместо 5
    particles_to_create = min(max_particles, blood_pool.max_size - len(blood_pool.in_use))

    if particles_to_create <= 0:
        return []  # Нет доступных частиц

    particles = []

    # ОДНА центральная частица + несколько вокруг
    for i in range(particles_to_create):
        particle = blood_pool.get()
        if not particle:
            continue

        try:
            # Упрощенные свойства
            particle.position = Vec3(
                position.x + uniform(-0.5, 0.5),
                position.y + uniform(0.2, 0.5),
                position.z + uniform(-0.5, 0.5)
            )

            # Фиксированный цвет и размер
            particle.color = color.rgba(0.6, 0, 0, 0.8)  # Меньше прозрачности
            particle.scale = 0.15 if i == 0 else 0.1  # Центральная частица крупнее

            if hasattr(particle, 'alpha'):
                particle.alpha = 0.8

            # Упрощенное направление
            direction = Vec3(
                uniform(-1, 1) if i > 0 else 0,  # Центральная не двигается
                uniform(0.5, 1.5),
                uniform(-1, 1) if i > 0 else 0
            ).normalized()

            # Упрощенные параметры
            speed = uniform(2, 4) if i > 0 else 0  # Центральная не двигается
            lifetime = uniform(0.8, 1.2)  # Короче время жизни

            # Сохраняем начальные значения
            start_scale = particle.scale
            start_time = time.time()

            # Простая функция обновления
            def create_update_func(p=particle, d=direction, s=speed, l=lifetime, st=start_time, sc=start_scale):
                def update_func(progress, obj):
                    if not obj or not obj.enabled:
                        return

                    # Вычисляем время с момента создания
                    elapsed = time.time() - st
                    current_progress = elapsed / l

                    if current_progress >= 1.0:
                        return

                    # Движение только для нецентральных частиц
                    if s > 0:
                        obj.position += d * s * time.dt
                        obj.position.y -= time.dt * 1.5  # Меньше гравитации

                    # Упрощенные анимации
                    obj.alpha = 0.8 * (1.0 - current_progress)
                    obj.scale = sc * (1.0 - current_progress * 0.3)

                return update_func

            update_func = create_update_func()

            # Добавляем анимацию
            anim = animation_system.add_animation(
                particle,
                lifetime,
                update_func,
                on_finished=lambda p=particle: blood_pool.return_particle(p) if blood_pool else None
            )

            if anim:
                particles.append(particle)
            else:
                blood_pool.return_particle(particle)

        except Exception as e:
            print(f"❌ Ошибка настройки кровяной частицы: {e}")
            blood_pool.return_particle(particle)

    # ОГРАНИЧИВАЕМ общее количество эффектов крови
    global blood_effects_count
    if not hasattr(create_blood_effect_optimized, 'blood_effects_count'):
        create_blood_effect_optimized.blood_effects_count = 0

    create_blood_effect_optimized.blood_effects_count += 1

    # Автоматическая очистка если слишком много эффектов
    if create_blood_effect_optimized.blood_effects_count > 10:
        cleanup_excess_blood_effects()

    return particles


def cleanup_excess_blood_effects():
    """Очищает старые эффекты крови если их слишком много"""
    global blood_effects_count

    # Считаем активные частицы крови
    active_particles = 0
    for blood_particles in blood_effects[:]:
        for particle_data in blood_particles[:]:
            if len(particle_data) == 5:
                particle, direction, speed, spawn_time, original_size = particle_data
                if particle and particle.enabled:
                    active_particles += 1
                    # Удаляем старые частицы (> 3 секунд)
                    if time.time() - spawn_time > 3.0:
                        destroy(particle)
                        blood_particles.remove(particle_data)
                        active_particles -= 1

    # Обновляем счетчик
    create_blood_effect_optimized.blood_effects_count = active_particles

    # Очищаем пул крови от неиспользуемых частиц
    if blood_pool and hasattr(blood_pool, 'cleanup'):
        blood_pool.cleanup()

    print(f"🧹 Очистка крови: {active_particles} активных частиц")


def safe_update_enemies_optimized():
    """Безопасное обновление врагов"""
    if not enemies:
        return

    current_time = time.time()

    # Фильтруем только живых врагов
    for enemy in enemies[:]:
        if not enemy or not enemy.entity or not enemy.entity.enabled:
            # Удаляем мертвых врагов из списка
            if enemy in enemies:
                enemies.remove(enemy)
            continue

        dist_to_player = (enemy.entity.position - player.position).length()

        if dist_to_player <= enemy.detection_range:
            enemy.is_chasing = True

            if dist_to_player > enemy.attack_range:

                target_height = 1.5  # На сколько выше ног идти
                target_point = player.position + Vec3(0, target_height, 0)

                # 2. Двигаемся к этой точке
                direction = (target_point - enemy.entity.position).normalized()
                enemy.entity.position += direction * enemy.chase_speed * time.dt

                # 3. Поворачиваемся смотреть на игрока (только горизонталь)
                # Берем направление в 2D (XZ плоскость), игнорируем высоту
                dx = player.position.x - enemy.entity.position.x
                dz = player.position.z - enemy.entity.position.z

                if abs(dz) > 0.001:  # Маленькое число вместо 0
                    angle_y = math.degrees(math.atan2(dx, dz))
                    enemy.entity.rotation_y = angle_y  # Попробуй с минусом или без

                # 4. Убираем наклоны
                enemy.entity.rotation_x = 0
                enemy.entity.rotation_z = 0

            if dist_to_player <= enemy.attack_range:
                if current_time - enemy.last_attack_time >= enemy.attack_cooldown:
                    attack_player(enemy)
                    enemy.last_attack_time = current_time


# ==================== ФУНКЦИЯ ДЛЯ ИНТЕГРАЦИИ В UPDATE ====================

def update_with_optimizations():
    """Вызывать в начале твоего update() для добавления оптимизаций"""
    global optimized_systems_initialized

    if not optimized_systems_initialized:
        init_optimized_systems()

    # Обновляем системы менеджмента
    object_manager.update()
    animation_system.update()

    global create_blood_effect
    if 'create_blood_effect' in globals() and create_blood_effect != create_blood_effect_optimized:
        print("🔄 Заменяем create_blood_effect на оптимизированную версию")
        create_blood_effect = create_blood_effect_optimized


# Остальной код остается без изменений...
# (здесь продолжается твой оригинальный код)

application.development_mode = False


def resource_path(relative_path: str):
    """Получает правильный путь к ресурсам для работы и в exe"""
    if hasattr(sys, '_MEIPASS'):
        # Если запущено как exe
        return os.path.join(sys._MEIPASS, relative_path)
    # Если запущено как скрипт
    return os.path.join(os.path.abspath("."), relative_path)


def load_shader(name):
    """Загружает шейдер из файла"""
    try:
        path = resource_path(name)
        with open(path, encoding="utf-8") as f:
            code = f.read()
        return Shader(fragment=code)
    except FileNotFoundError:
        print(f"⚠️ Файл шейдера '{name}' не найден. Используем простой шейдер.")
        # Возвращаем простой шейдер по умолчанию
        return Shader(language=Shader.GLSL, fragment='''
            #version 140
            uniform sampler2D p3d_Texture0;
            uniform vec4 p3d_Color;
            in vec2 uv;
            out vec4 frag_color;
            void main() {
                frag_color = texture(p3d_Texture0, uv) * p3d_Color;
            }
        ''')


app = Ursina()
walk = Audio('walk.ogg', loop=True, autoplay=False)
jump = Audio('jump.ogg', loop=False, autoplay=False)
shoot_sound = Audio("shoot.ogg", autoplay=False, lood=False)
shoot_sound2 = Audio('shoot2.ogg', loop=False, autoplay=False)
dark_fantasy_shader = Shader(language=Shader.GLSL,
                             fragment='''
#version 140
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_Color;

in vec2 uv;
in vec3 normal;
in vec3 world_position;

out vec4 frag_color;

void main() {
    vec4 tex_color = texture(p3d_Texture0, uv) * p3d_Color;

    // Мрачная цветовая коррекция
    float darkness = 0.6;
    vec3 dark_tint = vec3(0.25, 0.2, 0.35);

    // Увеличиваем контрастность
    tex_color.rgb = (tex_color.rgb - 0.5) * 1.4 + 0.5;

    // Добавляем мрачный оттенок
    tex_color.rgb = mix(tex_color.rgb, dark_tint, 0.3);

    // Затемняем
    tex_color.rgb *= darkness;

    // Стилизованное освещение
    vec3 light_dir = normalize(vec3(0.3, 1.0, 0.2));
    float diff = max(dot(normal, light_dir), 0.0);
    diff = floor(diff * 3.0) / 3.0; // Цел-шейдинг

    vec3 light_color = vec3(0.3, 0.5, 0.7);
    tex_color.rgb *= (0.4 + diff * 0.6) * light_color;

    // Легкий эффект тумана
    float fog = length(world_position) * 0.005;
    tex_color.rgb = mix(tex_color.rgb, vec3(0.08, 0.05, 0.12), min(fog, 0.4));

    frag_color = tex_color;
}
''',
                             vertex='''
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;

out vec2 uv;
out vec3 normal;
out vec3 world_position;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
    normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
    world_position = (p3d_ModelMatrix * p3d_Vertex).xyz;
}
''')

light_pistol_shader = Shader(language=Shader.GLSL,
                             fragment='''
#version 140
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_Color;

in vec2 uv;
in vec3 normal;
in vec3 world_position;

out vec4 frag_color;

void main() {
    vec4 tex_color = texture(p3d_Texture0, uv) * p3d_Color;

    // ОСВЕТЛЕНИЕ - увеличиваем яркость
    float brightness = 1.4;  // Увеличиваем яркость на 40%
    tex_color.rgb *= brightness;

    // Увеличиваем контрастность
    tex_color.rgb = (tex_color.rgb - 0.5) * 1.3 + 0.5;

    // Меньше мрачного оттенка
    vec3 light_tint = vec3(0.4, 0.35, 0.5);  // Более светлый оттенок
    tex_color.rgb = mix(tex_color.rgb, light_tint, 0.15);  // Меньше примеси

    // Меньше затемнения
    float darkness = 0.8;  // Меньше затемнения
    tex_color.rgb *= darkness;

    // Более яркое освещение
    vec3 light_dir = normalize(vec3(0.3, 1.0, 0.2));
    float diff = max(dot(normal, light_dir), 0.0);
    diff = floor(diff * 3.0) / 3.0;

    vec3 light_color = vec3(0.5, 0.7, 0.9);  // Более яркий свет
    tex_color.rgb *= (0.6 + diff * 0.4) * light_color;  // Больше базового света

    // Меньше тумана
    float fog = length(world_position) * 0.003;
    tex_color.rgb = mix(tex_color.rgb, vec3(0.15, 0.1, 0.2), min(fog, 0.3));

    frag_color = tex_color;
}
''',
                             vertex='''
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;

out vec2 uv;
out vec3 normal;
out vec3 world_position;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
    normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
    world_position = (p3d_ModelMatrix * p3d_Vertex).xyz;
}
''')
ground = Entity(color=color.clear, collider='box',
                scale=(10000, 1, 10000), position=(0, 0, 0))

player = FirstPersonController(collider='sphere')
player.position_y = 10
player.position = (0, 86, 0)
player.camera_pivot.y = 3
player.cursor.visible = True

# ---------------------------
# ШЕЙДЕР НАЗНАЧАЕМ ТУТ!!!
# ---------------------------
shader_enabled = False
grenade_effect = 0
shoot_strength = 0
reload_strength = 0
walk_strength = 0
master_shader = load_shader("master_vfx.shader")
camera.shader = master_shader

camera.shader = master_shader
camera.set_shader_input("base_intensity", 1.0)
camera.set_shader_input("shoot_strength", 0.0)
camera.set_shader_input("reload_strength", 0.0)
camera.set_shader_input("walk_strength", 0.0)
camera.set_shader_input("grenade_effect", 0.0)

# Ground может иметь свой отдельный шейдер
ground.shader = dark_fantasy_shader

# НАГРУДНАЯ КАМЕРА - новые координаты
# weapon = Entity(
#     model='weanpo14.glb',
#     parent=camera,  # Прикрепляем к камере
#     position=(0.3, -1.3, 0.8),  # Позиция как нагрудная камера (ниже и сбоку)
#     rotation=(0, 180, 0),  # Поворот для вида с груди
#     scale=2.5,shader=dark_fantasy_shader
# )


# Переменные для тряски КАМЕРЫ и ОРУЖИЯ
camera_base_position = (0, 0, 0)  # Базовая позиция камеры
weapon_base_position = (0.3, -1.3, 0.8)  # ОБНОВЛЕНО
weapon_base_rotation = (0, 180, 0)  # Базовый поворот оружия
is_moving = False
shake_timer = 0

# Параметры тряски для камеры (нормальная сила, но резкая)
camera_body_sway_intensity = 0.015
camera_step_impact_intensity = 0.025
camera_breathing_intensity = 0.008
camera_head_bob_intensity = 0.01

# Параметры тряски для оружия (нормальная сила, но резкая)
weapon_body_sway_intensity = 0.002  # Только небольшие движения
weapon_step_impact_intensity = 0  # Умеренные удары
weapon_breathing_intensity = 0.001  # Минимальное дыхание
weapon_head_bob_intensity = 0.01

# Переменные для анимации выстрела
is_shooting = False
shoot_animation_time = 0
shoot_animation_duration = 0.1
shoot_recoil = 0.1  # Отдача для камеры
weapon_shoot_recoil = 0.2  # Отдача для оружия
shoot_camera_shake_intensity = 0.08  # Основная сила тряски
shoot_camera_kick_intensity = 0.15  # Резкий толчок назад
shoot_camera_roll_intensity = 3.0  # Наклон камеры вбок
shoot_camera_shake_duration = 0.25  # Общая длительность
shoot_camera_kick_duration = 0.1  # Длительность толчка
shoot_camera_roll_duration = 0.15

# ДОБАВИМ ПЕРЕМЕННЫЕ ДЛЯ ОТСТАВАНИЯ ОРУЖИЯ
weapon_lag_speed = 5.0
weapon_lag_intensity = 0.8
weapon_lag_position_intensity = 0.15
target_weapon_rotation = (0, 180, 0)
current_weapon_rotation = (0, 180, 0)
target_weapon_position = (0.3, -1.3, 0.8)
current_weapon_position = (0.3, -1.3, 0.8)
mouse_movement = (0, 0)

# ДОБАВИМ НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ АВТОМАТИЧЕСКОЙ СТРЕЛЬБЫ
is_firing_auto = False

last_fire_time = 0
auto_fire_delay = 0.05

# ДОБАВИМ ПЕРЕМЕННЫЕ ДЛЯ ЭФФЕКТА ОГЛУШЕНИЯ
stun_effect_intensity = 0.3  # Сила эффекта оглушения
stun_effect_duration = 0.1  # Длительность эффекта
stun_effect_time = 0  # Таймер эффекта
is_stunned = False

# ДОБАВИМ ПЕРЕМЕННЫЕ ДЛЯ УПРАВЛЕНИЯ ЗВУКОМ
shoot_sound_duration = 0.05
shoot_sound2_duration = 0.05
last_shoot_sound_time = 0

muzzle_flash_entities = []
bullet_tracers = []
muzzle_flash_duration = 0.1  # Увеличил длительность для частиц
bullet_lifetime = 1.0

# ДОБАВИМ ПЕРЕМЕННЫЕ ДЛЯ NPC И ЭФФЕКТОВ КРОВИ
npcs = []
blood_effects = []
blood_duration = 1.0  # Увеличили длительность
blood_particle_count = 7  # Увеличили количество частиц в 2 раза
blood_speed = 5.0  # Увеличили скорость разлета
blood_gravity = 1.5  # Длительность эффекта крови

enemies = []
enemy_projectiles = []
# ОБНОВЛЯЕМ НАСТРОЙКИ СНАРЯДОВ
ENEMY_PROJECTILE_COOLDOWN = 8.0  # Каждые 8 секунд
ENEMY_PROJECTILE_SPEED = 3.0  # ОЧЕНЬ медленные снаряды
ENEMY_PROJECTILE_DETECTION_RADIUS = 3.0  # Радиус взрыва при приближении
ENEMY_PROJECTILE_MIN_SPEED = 1.5  # Минимальная скорость
ENEMY_PROJECTILE_TURN_SPEED = 1.0  # Очень медленный поворот
enemy_last_shot_time = {}  # Словарь для хранения времени последнего выстрела каждого врага

# ПЕРЕМЕННЫЕ ДЛЯ HUD
player_health = 100
player_max_health = 100
health_bar = None
health_text = None

# ДОБАВЛЯЕМ ПЕРЕМЕННЫЕ ДЛЯ АПТЕЧЕК
heal_pickups = []  # Список всех аптечек на карте
heal_pickup_cooldown = 0
# ДОБАВЛЯЕМ ПЕРЕМЕННЫЕ ДЛЯ ПАЧЕК С ПАТРОНАМИ
ammo_pickups = []  # Список всех пачек патронов на карте
ammo_pickup_cooldown = 0  # Задержка между подборами

# ИДЕАЛЬНЫЕ НАСТРОЙКИ ДЛЯ ПЛАВНОГО ПРЫЖКА
high_jump_power = 3.0  # Высота прыжка
player_gravity = 1  # НИЗКАЯ гравитация - медленное падение

# ИСПРАВЛЕННАЯ СИСТЕМА ВОЛН
current_stage = 1
stage_enemies_spawned = False
stage_enemies_killed = 0
total_enemies_on_map = 0
enemies_to_kill_for_stage = 0  # Общее количество врагов, которое нужно убить для перехода

# ДОБАВЛЯЕМ ПЕРЕМЕННЫЕ ДЛЯ ТРЯСКИ ПРИ ВЗРЫВЕ
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ОБЪЕДИНЕННОЙ СИСТЕМЫ ТРЯСОК
explosion_shake_intensity = 2
explosion_shake_duration = 0.8
explosion_shake_timer = 0
is_explosion_shaking = False
current_explosion_shake = (0, 0, 0)
current_explosion_tilt = (0, 0, 0)

game_started = False
weapon_pedestal = None
pickup_text = None
start_weapon = None
start_zone_center = Vec3(0, 0, 0)
start_zone_radius = 10
start_table_position = Vec3(27, 78, 0)
pickup_radius = 10
weapon_on_table = []
table_highlight = None
sword_on_table = None
axe_on_table = None
pistol_on_table = None
copie_on_table = None
main_weapon_on_table = None

# Добавляем новые глобальные переменные
camera_mode = "player"  # "player" или "table_view"
table_camera_position = Vec3(27.45, 86, -0.4)  # Позиция камеры над столом
table_camera_rotation = Vec3(90, 90, 0)  # Смотрим сверху вниз
is_selecting_weapon = False
weapon_selection_text = None

unlocked_weapons = ["pistol"]  # Изначально только пистолет
weapon_pickups = []  # Список оружия на карте
current_mission_text = None



# Добавляем глобальные переменные для анимаций
hovered_weapon = None
selected_weapon = None
weapon_selection_ui = None

# Добавляем глобальные переменные для триггера
trigger_area = None
trigger_hint_text = None
trigger_congratulation_text = None
trigger_fade_overlay = None
trigger_cooldown = 0
trigger_activated = False
trigger_center = Vec3(26.46, 19.23, 14.34)

stage_spawn_delay = 6.0  # 6 секунд для Stage 1, 3 секунды для остальных

# СИСТЕМА АНИМАЦИЙ СТАДИЙ
stage_animation = {
    "is_playing": False,
    "start_time": 0.0,
    "duration": 0.0,
    "type": "",  # "first_stage" или "next_stage"
    "black_screen": None,
    "stage_text": None
}

stage_start_time = 0.0
enemies_spawned_for_current_stage = False
shader_intensity = 0.0

player.jump_height = high_jump_power

# ДОБАВЛЯЕМ ПЕРЕМЕННЫЕ ДЛЯ СИСТЕМЫ ОРУЖИЯ
current_weapon = "assault_rifle"  # Текущее оружие
weapons = {}  # Словарь для хранения оружий

# ПАРАМЕТРЫ ДЛЯ РАЗНЫХ ВИДОВ ОРУЖИЯ
weapon_data = {
    "assault_rifle": {
        "model": "weanpo14.glb",
        "position": (0.3, -1.3, 0.8),
        "rotation": (0, 180, 0),
        "scale": 2.5,
        "fire_rate": 0.12,  # Очень быстрая стрельба
        "auto_fire": True,
        "recoil": 0.2,
        "camera_shake": 0.08,
        "muzzle_offset": Vec3(-0.01, 0.3, -1.8),
        "bullet_speed": 70,
        "sound_pitch_range": (0.9, 1.1),
        "shader": dark_fantasy_shader,
        "shoot_sound": "shoot.ogg",
        "reload_time": 2.0,
        "ammo_type": "assault_rifle"
    },
    "pistol": {
        "model": "pistol.glb",
        "position": (0.3, -0.7, 1),  # Новая позиция для пистолета
        "rotation": (0, 180, 0),
        "scale": 4,
        "fire_rate": 0.4,  # Медленная стрельба
        "auto_fire": False,
        "recoil": 0.15,
        "camera_shake": 0.05,
        "muzzle_offset": Vec3(-0.08, 0.1, -1.3),
        "bullet_speed": 60,
        "sound_pitch_range": (1.0, 1.2),
        "shader": light_pistol_shader,
        "shoot_sound": "shoot2.ogg",
        "reload_time": 1.5,
        "ammo_type": "pistol"

    },
    "dual_uzi": {
        "model": "dual_uzi.glb",
        "position": (0, -0.6, 2),  # ОБНОВЛЕННАЯ ПОЗИЦИЯ - ближе к камере
        "rotation": (0, 0, 0),
        "scale": 4.0,
        "fire_rate": 0.08,
        "auto_fire": True,
        "recoil": 0.25,
        "camera_shake": 0.12,
        "muzzle_offset_left": Vec3(-0.2, 0.03, 0.7),
        "muzzle_offset_right": Vec3(0.2, 0.03, 0.7),
        "bullet_speed": 65,
        "sound_pitch_range": (0.8, 1.0),
        "shader": dark_fantasy_shader,
        "shoot_sound": "uzi_shoot.mp3",
        "reload_time": 2.5,
        "ammo_type": "dual_uzi",
        "dual_shot": True
    },
    "grenade_launcher": {
        "model": "grenade.glb",  # Нужно создать модель
        "position": (0.7, -1.2, 1.7),  # Указанная позиция
        "rotation": (0, 180, 0),
        "scale": 0.5,
        "fire_rate": 1.5,  # Медленная стрельба
        "auto_fire": False,
        "recoil": 0.4,  # Сильная отдача
        "camera_shake": 0.7,  # Мощная тряска
        "muzzle_offset": Vec3(0, 0.7, -2.0),
        "bullet_speed": 25,  # Медленные снаряды
        "sound_pitch_range": (0.6, 0.8),  # Низкий звук
        "shader": dark_fantasy_shader,
        "shoot_sound": "grenade.ogg",
        "reload_time": 3.0,  # Долгая перезарядка
        "ammo_type": "grenade_launcher",
        "is_explosive": True,  # Флаг взрывного оружия
        "explosion_radius": 8.0,  # Радиус взрыва
        "explosion_damage": 100  # Урон взрыва
    }
}

# ДОБАВЛЯЕМ ПЕРЕМЕННЫЕ ДЛЯ ПАТРОНОВ
ammo_data = {
    "assault_rifle": {
        "current_ammo": 30,
        "max_ammo": 30,
        "ammo_per_mag": 30,
        "reserve_ammo": 90
    },
    "pistol": {
        "current_ammo": 20,
        "max_ammo": 20,
        "ammo_per_mag": 20,
        "reserve_ammo": 60
    },
    "dual_uzi": {
        "current_ammo": 60,
        "max_ammo": 60,
        "ammo_per_mag": 60,
        "reserve_ammo": 180
    },
    "grenade_launcher": {
        "current_ammo": 8,
        "max_ammo": 8,
        "ammo_per_mag": 8,
        "reserve_ammo": 16  # Максимум 16 в запасе
    }
}
explosive_projectiles = []

# ДОБАВИМ ПЕРЕМЕННЫЕ ДЛЯ СПРИНТА
sprint_speed_multiplier = 1.8  # Множитель скорости при спринте
is_sprinting = False
normal_speed = 8  # Обычная скорость игрока
sprint_speed = normal_speed * sprint_speed_multiplier  # Скорость спринта

weapon_hud = None
ammo_text = None
weapon_icons = {}
current_weapon_slot = 1
is_reloading_anim = False
reload_anim_time = 0
reload_anim_duration = 0.6  # Длительность опускания/поднятия оружия
reload_weapon_offset = 2.4


# ДОБАВЛЯЕМ ПЕРЕМЕННЫЕ ДЛЯ АНИМАЦИИ ПЕРЕЗАРЯДКИ


# Исправляем класс Enemy - добавляем все атрибуты в __init__
class Enemy:
    def __init__(self, position, enemy_type="normal"):
        # 🎯 ОСНОВНЫЕ ХАРАКТЕРИСТИКИ
        self.type = enemy_type  # Тип врага: "normal", "medium", "boss"
        self.entity = None  # 3D-объект врага в мире Ursina
        self.health = 0  # Текущее здоровье врага
        self.max_health = 0  # Максимальное здоровье врага
        self.damage = 0  # Урон от атаки ближнего боя
        self.attack_range = 0  # Дистанция для ближней атаки
        self.attack_cooldown = 0  # Время перезарядки между атаками
        self.last_attack_time = 0  # Время последней атаки

        # 🏃‍♂️ ПОВЕДЕНИЕ И ДВИЖЕНИЕ
        self.chase_speed = 0  # Скорость преследования игрока
        self.detection_range = 0  # Дистанция обнаружения игрока
        self.is_chasing = False  # Флаг: преследует ли враг игрока
        self.last_position = Vec3(position)  # Предыдущая позиция для проверки застревания
        self.stuck_timer = 0  # Таймер застревания
        self.stuck_threshold = 2.0  # Время до срабатывания анти-застревания

        self.hit_count = 0  # Количество полученных попаданий

        # ⚡ СПЕЦИАЛЬНЫЕ АТАКИ (в основном для босса)
        self.special_attack_cooldown = 0  # Перезарядка специальной атаки (волны)
        self.last_special_attack_time = 0  # Время последней специальной атаки
        self.charge_attack_cooldown = 0  # Перезарядка атаки с разбегом
        self.last_charge_attack_time = 0  # Время последней атаки с разбегом

        # 🎯 ДИСТАНЦИИ АТАК
        self.wave_attack_range = 0  # Дистанция для активации атаки волной
        self.ranged_attack_range = 0  # Дистанция для стрельбы шарами
        self.last_update_time = 0  # ⬅️ ДОБАВИЛИ для оптимизации
        self.update_interval = 0.1

        self.setup_enemy(position)

    def setup_enemy(self, position):
        if self.type == "normal":
            self.setup_normal(position)
        elif self.type == "medium":
            self.setup_medium(position)
        elif self.type == "boss":
            self.setup_boss(position)

    def setup_normal(self, position):
        self.entity = Entity(
            model='cube',
            color=color.blue,
            scale=(1, 2, 1),
            position=position,
            collider='box'
        )
        self.health = 1
        self.max_health = 1
        self.damage = 10
        self.attack_range = 5
        self.attack_cooldown = 1.5
        self.chase_speed = uniform(6, 9)
        self.detection_range = 1000
        self.wave_attack_range = 0  # ДИСТАНЦИЯ ДЛЯ АТАКИ ВОЛНОЙ
        self.ranged_attack_range = 0

    def setup_medium(self, position):
        self.entity = Entity(
            model='cube',
            color=color.orange,
            scale=(1.5, 3, 1.5),
            position=position,
            collider='box'
        )
        self.health = 2
        self.max_health = 2
        self.damage = 15
        self.attack_range = 5
        self.attack_cooldown = 2.0
        self.chase_speed = uniform(6, 10.8)
        self.detection_range = 1000
        self.wave_attack_range = 0  # Средние враги не используют волну
        self.ranged_attack_range = 50

    def setup_boss(self, position):
        self.entity = Entity(
            model='cube',
            color=color.red,
            scale=(3, 5, 3),
            position=position,
            collider='box'
        )
        self.health = 5
        self.max_health = 5
        self.damage = 25
        self.attack_range = 4.0
        self.attack_cooldown = 3.0
        self.chase_speed = uniform(6.4, 9.6)
        self.detection_range = 1000
        self.special_attack_cooldown = 3.0
        self.last_special_attack_time = 0
        self.charge_attack_cooldown = 8.0
        self.last_charge_attack_time = 0
        self.wave_attack_range = 30  # БОСС использует волну с 18 метров
        self.ranged_attack_range = 50

weapons_data = {
    "axe": {
        "name": "Топор",
        "description": "Мощное рубящее оружие ближнего боя.\nВысокий урон, но медленная атака.",
        "unlocked": False,
        "damage": 45,
        "attack_speed": "Медленная",
        "icon_color": color.rgba(0.9, 0.7, 0.5, 1)  # Коричневатый
    },
    "sword": {
        "name": "Меч",
        "description": "Сбалансированное оружие ближнего боя.\nХорошее сочетание урона и скорости.",
        "unlocked": False,
        "damage": 35,
        "attack_speed": "Средняя",
        "icon_color": color.rgba(0.7, 0.7, 0.9, 1)  # Голубоватый
    },
    "pistol": {
        "name": "Неизвестное оружие",
        "description": "Непонятное приспособление из другого мира \nТочно неизвестно как им пользоваться \nНе рекомендуется",
        "unlocked": True,  # Только пистолет доступен сначала
        "damage": 0,
        "attack_speed": "Неизвестно",
        "ammo_capacity": "Неизвестно",
        "icon_color": color.rgba(1, 0.5, 0, 1)  # Оранжевый
    },
    "copie": {
        "name": "Копье",
        "description": "Длинное оружие дальнего боя.\nОтличная дистанция, но требует пространства.",
        "unlocked": False,
        "damage": 40,
        "attack_speed": "Медленная",
        "range": "Дальняя",
        "icon_color": color.rgba(0.8, 0.6, 0.4, 1)  # Бежевый
    }
}

weapon_selection_ui = None
selected_weapon = None













def create_weapon_colliders():
    """Создает видимые коллайдеры вокруг оружия на столе"""
    weapons_on_table = [
        {
            "entity": main_weapon_on_table,
            "name": "pistol",
            "color": color.clear,
            "position": (27.45, 80, -2),
            "scale": (1.4, 0.6, 0.8)  # Немного больше для пистолета
        },
        {
            "entity": sword_on_table,
            "name": "sword",
            "color": color.clear,
            "position": (27.45, 80, 4.24),
            "scale": (2.5, 0.6, 1.0)  # Увеличиваем для меча
        },
        {
            "entity": axe_on_table,
            "name": "axe",
            "color": color.clear,
            "position": (28, 80, 2.02),
            "scale": (2.0, 0.4, 1.6)  # Увеличиваем для топора
        },
        {
            "entity": copie_on_table,
            "name": "copie",
            "color": color.clear,
            "position": (27.45, 80, -0.28),
            "scale": (3.5, 0.3, 0.3)  # Увеличиваем для копья
        }
    ]

    for weapon_data in weapons_on_table:
        if weapon_data["entity"]:
            # Создаем ВИДИМЫЙ коллайдер
            collider = Entity(
                model='cube',
                color=weapon_data["color"],
                scale=weapon_data["scale"],
                position=weapon_data["position"],
                collider='box',
                eternal=True,
                enabled=True
            )

            # Сохраняем ссылки
            collider.weapon_entity = weapon_data["entity"]
            collider.weapon_name = weapon_data["name"]

            print(f"🎯 Создан коллайдер для {weapon_data['name']}")


def create_start_scene():
    """Создает стартовую сцену с оружием на столе"""
    global sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table
    global table_highlight, pickup_text

    print("🎮 Создаю стартовую сцену...")
    print(f"📍 Стол находится на: {start_table_position}")

    # 1. Подсветка стола
    table_highlight = Entity(
        model='cube',
        color=color.rgba(0.4, 0.4, 0.4, 0.8),
        scale=(6, 0.1, 4),
        position=start_table_position,
        eternal=True
    )

    # 2. МЕЧ на столе (левый угол)
    try:
        sword_on_table = Entity(
            model='sword.glb',
            position=(27.45, 80, 4.24),
            rotation=(90, -5, 45),  # Лежит плашмя под углом
            scale=0.04,
            eternal=True,
            shader=dark_fantasy_shader
        )
        print("✅ Меч добавлен на стол")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить меч: {e}")
        sword_on_table = Entity(
            model='cube',
            color=color.rgba(0.7, 0.7, 0.9, 1),  # Голубоватый цвет для меча
            position=start_table_position + Vec3(-1.2, 0.05, -0.8),
            rotation=(90, 0, 45),
            scale=(1.0, 0.1, 0.2),
            eternal=True
        )

    # 3. ТОПОР на столе (правый угол)
    try:
        axe_on_table = Entity(
            model='axe.glb',
            position=(25.45, 80, 2.02),
            rotation=(90, 0, 90),  # Лежит плашмя
            scale=0.3,
            eternal=True,
            shader=dark_fantasy_shader
        )
        print("✅ Топор добавлен на стол")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить топор: {e}")
        axe_on_table = Entity(
            model='cube',
            color=color.rgba(0.9, 0.7, 0.5, 1),  # Коричневатый цвет для топора
            position=start_table_position + Vec3(1.2, 0.05, -0.4),
            rotation=(90, 0, -30),
            scale=(0.8, 0.1, 0.4),
            eternal=True
        )

    # 4. КОПИЯ на столе (передний центр)
    try:
        copie_on_table = Entity(
            model='copie.glb',
            position=(27.45, 80, -0.28),
            rotation=(0, 0, 30),  # Лежит плашмя
            scale=0.0015,
            eternal=True,
            shader=dark_fantasy_shader
        )
        print("✅ Копия добавлена на стол")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить копию: {e}")
        copie_on_table = Entity(
            model='cube',
            color=color.rgba(0.8, 0.6, 0.4, 1),  # Бежевый цвет для копии
            position=start_table_position + Vec3(0, 0.05, 0.8),
            rotation=(90, 0, 90),
            scale=(0.7, 0.1, 0.7),
            eternal=True
        )

    # 5. ОСНОВНОЕ ОРУЖИЕ (ПИСТОЛЕТ) на столе (центр стола)
    try:
        main_weapon_on_table = Entity(
            model='decore_pistol.glb',  # Это пистолет/основное оружие
            position=(27.45, 80, -0.4),
            rotation=(0, 0, 90),  # Лежит плашмя
            scale=7,
            eternal=True,
            shader=light_pistol_shader
        )
        print("✅ Основное оружие (пистолет) добавлено на стол")
    except Exception as e:
        print(f"⚠️ Не удалось загрузить основное оружие: {e}")
        main_weapon_on_table = Entity(
            model='cube',
            color=color.rgba(1, 0.5, 0, 1),  # Оранжевый цвет для основного оружия
            position=start_table_position + Vec3(0, 0.1, 0),
            rotation=(90, 0, 0),
            scale=(2.0, 0.1, 0.8),
            eternal=True
        )

    # 6. Текст подсказки
    pickup_text = Text(
        parent=camera.ui,
        text="Нажмите E чтобы взять оружие",
        position=(0, 0.3, 0),
        scale=2.5,
        color=color.yellow,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.8),
        enabled=False,
        font='custom2.ttf'
    )

    print("✅ Стартовая сцена создана на столе с оружием")


# ФУНКЦИЯ ПРОВЕРКИ БЛИЗОСТИ К ОРУЖИЮ
def check_weapon_proximity():
    """Оптимизированная проверка близости к столу"""
    global pickup_text, game_started

    # Если игра началась или идет выбор оружия - не проверяем
    if game_started or is_selecting_weapon:
        if pickup_text and pickup_text.enabled:
            pickup_text.enabled = False
        return

    # Используем простую проверку без сложных вычислений
    if not hasattr(check_weapon_proximity, 'last_check'):
        check_weapon_proximity.last_check = 0

    # Проверяем только раз в 0.5 секунды для оптимизации
    current_time = time.time()
    if current_time - check_weapon_proximity.last_check < 0.5:
        return

    check_weapon_proximity.last_check = current_time

    # Простая проверка расстояния
    dx = player.position.x - start_table_position.x
    dz = player.position.z - start_table_position.z
    distance_squared = dx * dx + dz * dz  # Без sqrt для оптимизации

    if distance_squared < pickup_radius * pickup_radius:
        if pickup_text and not pickup_text.enabled:
            pickup_text.enabled = True
            pickup_text.text = "Нажмите E чтобы осмотреть оружие"
    else:
        if pickup_text and pickup_text.enabled:
            pickup_text.enabled = False


# ФУНКЦИЯ ПЕРЕКЛЮЧЕНИЯ НА ВИД СВЕРХУ
def switch_to_table_view():
    """Переключает камеру на вид сверху над столом"""
    global camera_mode, is_selecting_weapon, pickup_text, weapon_selection_text
    global player_camera_position, player_camera_rotation  # Добавляем глобальные переменные

    print("🎬 Переключаюсь на вид сверху над столом...")

    # Сохраняем текущую позицию камеры игрока
    player_camera_position = Vec3(camera.position)
    player_camera_rotation = Vec3(camera.rotation)

    # ОЧЕНЬ ВАЖНО: разблокируем мышь
    mouse.locked = False
    mouse.visible = True  # Делаем курсор видимым!

    # Отключаем управление игроком
    player.enabled = False
    camera_mode = "table_view"
    is_selecting_weapon = True

    # Убираем старый текст
    if pickup_text:
        pickup_text.enabled = False

    # Создаем новый текст для выбора оружия
    weapon_selection_text = Text(
        parent=camera.ui,
        text="Выберите оружие мышкой",
        position=(0, 0.4, 0),
        scale=2.5,
        color=color.yellow,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.8),
        font='custom2.ttf'
    )

    # Анимация подъема камеры
    camera.animate_position(table_camera_position, duration=1.5, curve=curve.in_out_cubic)
    camera.animate_rotation(table_camera_rotation, duration=1.5, curve=curve.in_out_cubic)

    # После анимации разрешаем выбор оружия
    invoke(enable_weapon_selection, delay=1.5)


# ФУНКЦИЯ ВКЛЮЧЕНИЯ ВЫБОРА ОРУЖИЯ
def enable_weapon_selection():
    """Включает возможность выбора оружия мышкой"""
    print("✅ Готово к выбору оружия!")

    if weapon_selection_text:
        weapon_selection_text.text = "Нажмите на оружие для просмотра информации"
        weapon_selection_text.y = 0.4  # Перемещаем вниз
        weapon_selection_text.scale = 2.0  # Уменьшаем немного

    # Инициализируем оружия
    weapons = [sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table]

    for weapon in weapons:
        if weapon:
            # Сохраняем исходные значения
            weapon.original_pos = Vec3(weapon.position)
            weapon.original_color = weapon.color if hasattr(weapon, 'color') else color.white
            weapon.is_selected = False
            weapon.is_hovered = False
            weapon.is_raised = False
            weapon.was_hovered_last_frame = False
            weapon.animating_color = False

    # Создаем коллайдеры
    create_weapon_colliders()

    print("🎮 Выберите оружие для просмотра информации")


# ФУНКЦИЯ ПРОВЕРКИ НАЖАТИЯ МЫШКОЙ
def check_mouse_click():
    """Проверяет клик мышкой по оружию"""
    global selected_weapon, weapon_selection_ui

    if not is_selecting_weapon or camera_mode != "table_view":
        return

    if mouse.left:
        if mouse.hovered_entity and hasattr(mouse.hovered_entity, 'weapon_name'):
            clicked_entity = mouse.hovered_entity
            weapon_name = clicked_entity.weapon_name
            print(f"🎯 Выбрано оружие: {weapon_name}")

            # Сбрасываем все другие оружия
            weapons_list = [sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table]
            for weapon in weapons_list:
                if weapon and weapon != clicked_entity.weapon_entity:
                    # Плавно опускаем и возвращаем цвет
                    if hasattr(weapon, 'original_pos'):
                        weapon.animate_position(weapon.original_pos, duration=0.2, curve=curve.in_quad)
                        weapon.is_raised = False
                        weapon.is_selected = False

                    if hasattr(weapon, 'original_color'):
                        weapon.animate_color(weapon.original_color, duration=0.2, curve=curve.in_quad)

            # Плавно поднимаем выбранное оружие, но не слишком высоко
            clicked_entity.weapon_entity.is_selected = True
            clicked_entity.weapon_entity.is_hovered = False

            # Сохраняем позиции если еще не сохранены
            if not hasattr(clicked_entity.weapon_entity, 'original_pos'):
                clicked_entity.weapon_entity.original_pos = Vec3(clicked_entity.weapon_entity.position)

            # Поднимаем только на 0.3 единицы (меньше чем при наведении)
            selected_pos = Vec3(clicked_entity.weapon_entity.original_pos)
            selected_pos.y += 0.3  # Только 0.3 вместо 1.0

            # Плавная анимация подъема и изменения цвета
            clicked_entity.weapon_entity.animate_position(selected_pos, duration=0.3, curve=curve.out_quad)
            clicked_entity.weapon_entity.animate_color(color.white, duration=0.3, curve=curve.out_quad)
            clicked_entity.weapon_entity.is_raised = True

            # Сохраняем выбранное оружие
            selected_weapon = weapon_name

            # Показываем UI с информацией через небольшую задержку
            invoke(lambda: show_weapon_info(weapon_name), delay=0.2)
            return


def show_weapon_info(weapon_name):
    """Показывает UI с информацией о выбранном оружии"""
    global weapon_selection_ui

    # Скрываем предыдущий UI если есть
    if weapon_selection_ui:
        destroy(weapon_selection_ui)
        weapon_selection_ui = None

    # Получаем данные об оружии
    data = weapons_data[weapon_name]

    # Создаем основной контейнер UI (самый низкий уровень)
    weapon_selection_ui = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0.08, 0.08, 0.12, 0.95),
        scale=(0.6, 0.7),
        position=(0.2, 0, 0),
        eternal=False
    )

    # Темная рамка вокруг (чуть выше основного фона)
    border = Entity(
        parent=weapon_selection_ui,
        model='quad',
        color=color.rgba(0.2, 0.2, 0.3, 0.8),
        scale=(1.05, 1.05),
        z=-0.01
    )

    # Заголовок (название оружия) - фон
    name_bg = Entity(
        parent=weapon_selection_ui,
        model='quad',
        color=color.rgba(0.15, 0.15, 0.2, 1),
        scale=(0.9, 0.12),
        position=(0, 0.35, -0.05),
        z=-0.02
    )

    # Текст названия оружия (посередине своего фона)
    name_text = Text(
        parent=weapon_selection_ui,
        text=data["name"],
        position=(0, 0.35, -0.1),
        scale=3.0,
        color=color.white,
        font='custom2.ttf',
        origin=(0, 0)
    )

    # Окно описания - фон
    desc_bg = Entity(
        parent=weapon_selection_ui,
        model='quad',
        color=color.rgba(0.12, 0.12, 0.16, 0.7),
        scale=(0.85, 0.4),
        position=(0, 0.05, -0.05),
        z=-0.02
    )

    # Описание оружия - текст с увеличенным размером 2.5
    desc_text = Text(
        parent=weapon_selection_ui,
        text=data["description"],
        position=(0, 0.05, -0.1),
        scale=2.5,
        color=color.light_gray,
        wordwrap=25,
        line_height=1.2,
        font='custom2.ttf',
        origin=(0, 0)
    )

    # Статистика - фон
    stats_bg = Entity(
        parent=weapon_selection_ui,
        model='quad',
        color=color.rgba(0.15, 0.15, 0.2, 1),
        scale=(0.85, 0.15),
        position=(0, -0.25, -0.05),
        z=-0.02
    )

    stats_y = -0.25
    stats = [
        f"УРОН: {data['damage']}",
        f"СКОРОСТЬ: {data['attack_speed']}"
    ]

    if weapon_name == "pistol":
        stats.append(f"ПАТРОНЫ: {data['ammo_capacity']}")
    elif weapon_name == "copie":
        stats.append(f"ДАЛЬНОСТЬ: {data['range']}")

    # Распределяем характеристики по вертикали
    stats_height = 0.12
    stat_spacing = stats_height / (len(stats) + 1)

    for i, stat in enumerate(stats):
        y_pos = stats_y + (stats_height / 2) - (i + 1) * stat_spacing

        stat_text = Text(
            parent=weapon_selection_ui,
            text=stat,
            position=(0, y_pos, -0.1),
            scale=1.8,
            color=color.yellow,
            font='custom2.ttf',
            origin=(0, 0)
        )

    # КНОПКА ЗАКРЫТИЯ "X"
    close_button = Button(
        parent=weapon_selection_ui,
        text='X',
        color=color.red,
        scale=(0.08, 0.08),
        position=(0.45, 0.35, -0.5),
        on_click=lambda: close_weapon_info()
    )
    close_button.text_entity.font = 'custom2.ttf'

    # Кнопка выбора/блокировки
    button_y = -0.45

    if weapon_name == "pistol":
        # Кнопка "ВЫБРАТЬ" - создаем обычную кнопку
        select_button = Button(
            parent=weapon_selection_ui,
            text='ВЫБРАТЬ',
            color=color.rgba(0.2, 0.6, 0.2, 1),
            scale=(0.4, 0.12),
            position=(0, button_y, -0.1),
            on_click=lambda: select_weapon(weapon_name),
            font='custom2.ttf'
        )
        select_button.text_entity.font = 'custom2.ttf'

        # Эффект наведения для кнопки (без изменения масштаба текста!)
        def on_hover():
            select_button.color = color.rgba(0.3, 0.8, 0.3, 1)
            select_button.scale = (0.42, 0.13)
            # НЕ меняем масштаб текста - только цвет и тень
            select_button.text_entity.color = color.rgb(240, 255, 240)
            # Добавляем легкую тень
            if not hasattr(select_button.text_entity, 'shadow'):
                select_button.text_entity.shadow = Text(
                    parent=select_button,
                    text='ВЫБРАТЬ',
                    position=(0.005, -0.005, -0.02),
                    scale=2.0,
                    color=color.rgba(0, 0, 0, 0.5),
                    font='custom2.ttf'
                )
                select_button.text_entity.font = 'custom2.ttf'

        def on_exit():
            select_button.color = select_button.original_color
            select_button.scale = select_button.original_scale
            select_button.text_entity.color = color.white
            # Убираем тень
            if hasattr(select_button.text_entity, 'shadow'):
                destroy(select_button.text_entity.shadow)
                delattr(select_button.text_entity, 'shadow')

        select_button.hover = on_hover
        select_button.exit = on_exit

    else:
        locked_button = Button(
            parent=weapon_selection_ui,
            text='ЗАБЛОКИРОВАНО',
            color=color.rgba(0.3, 0.3, 0.3, 1),
            scale=(0.5, 0.12),
            position=(0, button_y, -0.1),
            font='custom2.ttf',
        )
        locked_button.text_entity.font = 'custom2.ttf'

        # Текст о разблокировке
        unlock_text = Text(
            parent=weapon_selection_ui,
            text="Разблокируется на высоких уровнях",
            position=(0.3, button_y - 0.12, -0.1),
            scale=1.3,
            color=color.light_gray,
            font='custom2.ttf',
            origin=(0, 0)
        )

    # Иконка оружия
    icon_size = 0.09
    icon = Entity(
        parent=weapon_selection_ui,
        model='quad',
        color=data["icon_color"],
        scale=(icon_size, icon_size),
        position=(-0.4, 0.35, -0.1),
    )

    print(f"ℹ️ Показана информация о {weapon_name}")


def close_weapon_info():
    """Закрывает UI с информацией и плавно опускает оружие"""
    global weapon_selection_ui, selected_weapon

    if weapon_selection_ui:
        destroy(weapon_selection_ui)
        weapon_selection_ui = None

    # Плавно опускаем выбранное оружие обратно (если оно было поднято)
    if selected_weapon:
        weapons_dict = {
            "pistol": main_weapon_on_table,
            "sword": sword_on_table,
            "axe": axe_on_table,
            "copie": copie_on_table
        }

        weapon_entity = weapons_dict.get(selected_weapon)
        if weapon_entity and hasattr(weapon_entity, 'original_pos'):
            weapon_entity.is_selected = False
            weapon_entity.is_hovered = False

            # Только если оружие было поднято
            if getattr(weapon_entity, 'is_raised', False):
                weapon_entity.animate_position(weapon_entity.original_pos, duration=0.3, curve=curve.in_quad)

            if hasattr(weapon_entity, 'original_color'):
                weapon_entity.animate_color(weapon_entity.original_color, duration=0.3, curve=curve.in_quad)

            weapon_entity.is_raised = False

        selected_weapon = None

    print("📋 Закрыто окно информации об оружии")


def select_weapon(weapon_name):
    """Выбирает оружие и начинает игру"""
    global weapon_selection_ui, selected_weapon

    print(f"✅ Выбрано оружие: {weapon_name}")

    # Проверяем что выбран пистолет
    if weapon_name != "pistol":
        print("❌ Можно выбрать только пистолет для начала игры!")

        # Показываем сообщение об ошибке
        if weapon_selection_text:
            weapon_selection_text.text = "Только пистолет доступен в начале!"
            weapon_selection_text.color = color.red
            weapon_selection_text.y = -0.4  # Перемещаем вниз чтобы не мешать

            # Возвращаем обычный текст через 2 секунды
            invoke(lambda: setattr(weapon_selection_text, 'text',
                                   "Нажмите на оружие для просмотра")
            if weapon_selection_text else None, delay=2.0)
            invoke(lambda: setattr(weapon_selection_text, 'color', color.yellow)
            if weapon_selection_text else None, delay=2.0)
            invoke(lambda: setattr(weapon_selection_text, 'y', 0.3)
            if weapon_selection_text else None, delay=2.0)
        return

    # Закрываем UI
    if weapon_selection_ui:
        destroy(weapon_selection_ui)
        weapon_selection_ui = None

    # Перемещаем подсказку ВНИЗ, чтобы она не мешала
    if weapon_selection_text:
        weapon_selection_text.text = "Начинаем игру..."
        weapon_selection_text.color = color.green
        weapon_selection_text.y = -0.45  # Очень низко

    # НЕ поднимаем оружие - оставляем на том же уровне
    # Просто делаем его белым и немного увеличиваем
    if main_weapon_on_table:
        # Только изменение цвета и небольшое увеличение
        main_weapon_on_table.animate_scale(
            7.5,  # Небольшое увеличение
            duration=0.5,
            curve=curve.out_quad
        )

        # Делаем ярко-белым
        main_weapon_on_table.animate_color(
            color.rgba(1, 1, 1, 1),
            duration=0.5
        )

        # Добавляем легкое свечение без подъема
        glow = Entity(
            parent=main_weapon_on_table,
            model='sphere',
            color=color.rgba(1, 1, 1, 0.2),
            scale=2,
            position=(0, 0, 0)
        )
        glow.animate_scale(4, duration=0.5)
        glow.animate_color(color.rgba(1, 1, 1, 0), duration=0.5)
        invoke(lambda: destroy(glow) if glow else None, delay=0.5)

    # Возвращаем другие оружия на место (если они были подняты)
    weapons_list = [sword_on_table, axe_on_table, copie_on_table]
    for weapon in weapons_list:
        if weapon and hasattr(weapon, 'original_pos'):
            if getattr(weapon, 'is_raised', False):
                weapon.animate_position(weapon.original_pos, duration=0.3, curve=curve.in_quad)
            weapon.is_selected = False
            weapon.is_hovered = False
            weapon.is_raised = False

            if hasattr(weapon, 'original_color'):
                weapon.animate_color(weapon.original_color, duration=0.3, curve=curve.in_quad)

    # Начинаем игру через небольшой промежуток
    print("🎮 Начинаем игру с пистолетом...")
    invoke(start_game_from_weapon, delay=0.7)


def highlight_hovered_weapon():
    """Плавно поднимает и подсвечивает оружие при наведении мыши"""
    # Находим все оружия на столе
    weapons_list = [sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table]

    # Сбрасываем флаг наведения для всех оружий
    for weapon in weapons_list:
        if weapon:
            weapon.was_hovered_last_frame = getattr(weapon, 'is_hovered', False)
            weapon.is_hovered = False

    # Определяем на какое оружие наведен курсор
    hovered_weapon_entity = None
    if mouse.hovered_entity and hasattr(mouse.hovered_entity, 'weapon_name') and not weapon_selection_ui:
        hovered_entity = mouse.hovered_entity
        if hovered_entity.weapon_entity and not getattr(hovered_entity.weapon_entity, 'is_selected', False):
            hovered_weapon_entity = hovered_entity.weapon_entity
            hovered_weapon_entity.is_hovered = True

    # Обрабатываем каждое оружие
    for weapon in weapons_list:
        if not weapon:
            continue

        # Сохраняем оригинальные значения если еще не сохранены
        if not hasattr(weapon, 'original_pos'):
            weapon.original_pos = Vec3(weapon.position)
        if not hasattr(weapon, 'original_color'):
            weapon.original_color = weapon.color if hasattr(weapon, 'color') else color.white

        # Если оружие выбрано - пропускаем (оно обрабатывается отдельно)
        if getattr(weapon, 'is_selected', False):
            continue

        # Если наводимся на это оружие
        if weapon == hovered_weapon_entity:
            # Плавно поднимаем
            target_pos = Vec3(weapon.original_pos)
            target_pos.y += 0.5

            if not getattr(weapon, 'is_raised', False):
                weapon.animate_position(target_pos, duration=0.2, curve=curve.out_quad)
                weapon.is_raised = True

            # Плавно делаем светлее
            target_color = color.rgba(
                min(1.0, weapon.original_color.r * 1.3),
                min(1.0, weapon.original_color.g * 1.3),
                min(1.0, weapon.original_color.b * 1.3),
                weapon.original_color.a if hasattr(weapon.original_color, 'a') else 1.0
            )

            if not hasattr(weapon, 'animating_color') or not weapon.animating_color:
                weapon.animate_color(target_color, duration=0.2, curve=curve.out_quad)
                weapon.animating_color = True

        # Если убрали курсор с этого оружия
        elif getattr(weapon, 'was_hovered_last_frame', False) and not getattr(weapon, 'is_hovered', False):
            # Плавно опускаем обратно
            weapon.animate_position(weapon.original_pos, duration=0.2, curve=curve.in_quad)
            weapon.is_raised = False

            # Плавно возвращаем оригинальный цвет
            weapon.animate_color(weapon.original_color, duration=0.2, curve=curve.in_quad)
            weapon.animating_color = False


def start_game_from_weapon():
    """Начинает игру после выбора пистолета"""
    global game_started, pickup_text, current_stage, enemies_spawned_for_current_stage
    global sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table
    global table_highlight, is_selecting_weapon, weapon_selection_text, camera_mode
    global weapon_hud, ammo_text, weapon_icons, selected_weapon

    if game_started:
        return
    create_trigger_area()

    # Проверяем, что выбран пистолет (только он доступен в начале)
    if selected_weapon != "pistol":
        print(f"❌ Можно выбрать только пистолет для начала игры!")

        # Показываем сообщение
        if weapon_selection_text:
            weapon_selection_text.text = "Только пистолет доступен в начале!"
            weapon_selection_text.color = color.red

            # Через 2 секунды возвращаем обычный текст
            invoke(lambda: setattr(weapon_selection_text, 'text',
                                   "Нажмите на оружие для просмотра информации")
            if weapon_selection_text else None, delay=2.0)
            invoke(lambda: setattr(weapon_selection_text, 'color', color.yellow)
            if weapon_selection_text else None, delay=2.0)
        return

    print("🎮 Начинаем игру с выбранным оружием!")

    # Убираем коллайдеры
    for entity in scene.entities[:]:  # Используем копию списка
        if hasattr(entity, 'weapon_name'):
            destroy(entity)

    # Анимация увеличения пистолета перед началом
    if main_weapon_on_table:
        main_weapon_on_table.animate_scale(main_weapon_on_table.scale * 1.5, duration=0.5)
        main_weapon_on_table.animate_color(color.white, duration=0.5)

    # Ждем завершения анимации
    invoke(finish_game_start, delay=0.7)


def finish_game_start():
    """Завершает начало игры после анимации - ТЕПЕРЬ С ПОЛНОЙ ОЧИСТКОЙ"""
    global game_started, pickup_text, current_stage, enemies_spawned_for_current_stage
    global weapon_hud, ammo_text, weapon_icons  # Добавляем глобальные переменные HUD

    print("🎮 Начинаем игру с выбранным оружием!")

    # =========== ПОЛНАЯ ОЧИСТКА ЛОББИ ===========
    cleanup_lobby_entirely()

    game_started = True
    camera_mode = "player"

    # Включаем управление игроком
    player.enabled = True
    mouse.locked = True
    player.position = Vec3(50, 10, -31)
    camera.position = (0, 0, 0)
    camera.rotation = (0, 0, 0)
    location.enabled=False
    cl2_1.enabled=False

    print(f"📍 Телепортация на: {player.position}")

    # ПРОВЕРЯЕМ, ЧТО HUD ЕЩЕ НЕ СОЗДАН
    if weapon_hud is None:  # Если HUD еще не создан
        # Инициализируем HUD
        create_health_hud()
        create_weapon_hud()
    else:
        # Если HUD уже существует, просто обновляем
        update_health_hud()
        update_weapon_hud()

    # Разблокируем пистолет и переключаемся на него
    if "pistol" not in unlocked_weapons:
        unlocked_weapons.append("pistol")

    switch_weapon("pistol")

    # Даем начальные патроны
    ammo_data["pistol"]["current_ammo"] = 20
    ammo_data["pistol"]["max_ammo"] = 20
    ammo_data["pistol"]["reserve_ammo"] = 60
    ammo_data["pistol"]["ammo_per_mag"] = 20

    # Обновляем HUD
    update_weapon_hud()
    update_health_hud()

    # Инициализируем оптимизированные системы
    if not optimized_systems_initialized:
        init_optimized_systems()

    # Запускаем первую стадию (через небольшую задержку)
    current_stage = 1
    enemies_spawned_for_current_stage = False
    update_shader_intensity()




    print("🎮 Запускаем анимацию Stage 1...")
    start_stage_animation(1)


def cleanup_lobby_entirely():
    """Полностью удаляет ВСЕ ресурсы начального лобби"""
    print("🧹 Начинаю полную очистку лобби...")
    global sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table
    global table_highlight, weapon_selection_text

    # 1. Удаляем все оружие со стола
    lobby_weapons = [sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table]
    for weapon in lobby_weapons:
        if weapon:
            try:
                destroy(weapon)
            except:
                pass

    # 2. Удаляем подсветку стола
    if table_highlight:
        try:
            destroy(table_highlight)
        except:
            pass

    # 3. Удаляем ВСЕ коллайдеры для выбора оружия
    for entity in scene.entities[:]:  # Используем копию списка для безопасного удаления
        if hasattr(entity, 'weapon_name'):
            try:
                destroy(entity)
            except:
                pass

    # 4. Удаляем текст выбора оружия
    if weapon_selection_text:
        try:
            destroy(weapon_selection_text)
        except:
            pass

    # 5. Удаляем pickup_text
    if pickup_text:
        try:
            pickup_text.enabled = False
            destroy(pickup_text)
        except:
            pass

    # 6. Обнуляем все глобальные переменные лобби

    table_highlight.enabled = False
    axe_on_table.enabled = False
    sword_on_table.enabled = False
    main_weapon_on_table.enabled = False
    copie_on_table.enabled = False

    # 7. Выключаем все проверки связанные с лобби
    global is_selecting_weapon, camera_mode
    is_selecting_weapon = False
    camera_mode = "player"

    # 8. Принудительный сбор мусора
    import gc
    gc.collect()

    print("✅ Лобби полностью очищено!")


def create_wall(p1, p2, thickness=0.3, height=1, color_wall=color.gray):
    """
    Создаёт наклонённую стену между точками p1 и p2.

    p1, p2 — (x, y, z)
    thickness — толщина стены
    height — высота стены
    """
    x1, y1, z1 = p1
    x2, y2, z2 = p2

    start = Vec3(x1, y1, z1)
    end = Vec3(x2, y2, z2)

    # Центр стены
    center = (start + end) / 2

    # Длина стены в 3D
    length_3d = distance(start, end)

    # Направление по горизонтали (X, Z)
    horizontal_direction = Vec3(end.x - start.x, 0, end.z - start.z)
    horizontal_length = horizontal_direction.length()

    # Угол поворота вокруг Y (горизонтальная плоскость)
    angle_y = math.degrees(math.atan2(horizontal_direction.z, horizontal_direction.x))

    # Направление по вертикали (ось Y)
    vertical_direction = end.y - start.y

    # Угол наклона по вертикали (ось X)
    angle_x = math.degrees(math.atan2(vertical_direction, horizontal_length))

    # Создаём стену
    wall = Entity(
        model='cube',
        position=center,
        scale=(length_3d, height, thickness),
        rotation=Vec3(angle_x, -angle_y, 0),
        collider='box',
        color=color.clear
    )

    return wall


sky = Sky()
location = Entity(model='1_location.glb', scale=5, position=(0, 150, 0), shader=dark_fantasy_shader)
cl2_1 = Entity(model='cube', scale=(100, 2, 100), position=(0, 76, 0), rotation=(0, 0, 0), color=color.white,
               collider='box')
location2 = Entity(model='locationtest2.glb', scale=80, position=(0, 1, 0), )
cl1 = Entity(model='cube', scale=(1, 20, 40), position=(-16, 0, -290), color=color.clear,
             collider='box')
cl2 = Entity(model='cube', scale=(1, 20, 50), position=(-24, 0, -248), rotation=(0, -20, 0), color=color.clear,
             collider='box')
create_wall((-74, 0, -190), (-60, 0, -120), height=40)
create_wall((-34, 0, -209), (-72, 0, -183), height=40)
create_wall((-34, 0, -208), (-31, 0, -228), height=40)
create_wall((-4, 0, -310), (-6, 0, -223), height=40, thickness=2)
create_wall((-6, 0, -223), (25, 0, -188), height=40, thickness=2)
create_wall((24, 0, -188), (59, 0, -174), height=40, thickness=2)
create_wall((62, 0, -174), (70, 0, -69), height=18)
create_wall((-60, 0, -120), (-29, 0, -129), height=40)
create_wall((-29, 0, -129), (9, 0, -118), height=40)
create_wall((9, 0, -118), (24, 0, -108), height=40)
create_wall((9, 0, -118), (24, 0, -108), height=40)
create_wall((23.34, 0, -107.15), (18.22, 0, -106.65), thickness=0.2, height=40)
create_wall((18.22, 0, -106.65), (18.39, 0, -93.21), thickness=0.2, height=40)
create_wall((18.39, 0, -93.21), (32.71, 0, -93.35), thickness=0.2, height=40)
create_wall((33, 0, -93.35), (41.87, 0, -13), thickness=1, height=40)
create_wall((26, 1, -16), (26, 1, 55), height=80)
create_wall((26, 1, 55), (82, 0, 51), height=80)
create_wall((82, 0, 51), (100, 0, 23), height=40)
create_wall((100, 0, 23), (94, 0, 4), height=40)
create_wall((94, 0, 4), (97, 0, -98), height=40)
create_wall((94, 0, 4), (97, 0, -98), height=40)
create_wall((97, 0, -98), (93, 0, -129), height=40)
create_wall((93, 0, -129), (98, 0, -171), height=40)
create_wall((98, 0, -171), (59.3, 0, -173.54), height=40)
create_wall((10, 1, -10), (41, 1, -14), height=80)

cl3 = Entity(model='cube', scale=(20, 30, 13), position=(-60, 0, -157), rotation=(0, 12, 0), color=color.clear,
             collider='box')
cl4 = Entity(model='cube', scale=(10, 20, 10), position=(60, 0, -173.54), color=color.clear,
             collider='box')
cl5 = Entity(model='cube', scale=(13, 8, 13), position=(25, 0, -100), color=color.clear,
             collider='box')
cl6 = Entity(model='cube', scale=(13, 2, 8), position=(35, 0, -100), rotation=(0, 0, 45), color=color.clear,
             collider='box')
cl7 = Entity(model='cube', scale=(13, 3, 10), position=(30, 0, -108), rotation=(0, 45, 45), color=color.clear,
             collider='box')
cl8 = Entity(model='cube', scale=(2, 10, 2), position=(23.05, 4.16, -107.84), color=color.clear,
             collider='box')
cl9 = Entity(model='cube', scale=(4, 10, 4), position=(20.41, 4, -104.78), color=color.clear,
             collider='box')
cl11 = Entity(model='cube', scale=(110, 2, 39), position=(84, 11, -127), rotation=(-10, 95, 0), color=color.clear,
              collider='box')
cl12 = Entity(model='cube', scale=(25, 4, 26), position=(76.52, 10, -161), rotation=(1, 10, -10), color=color.clear,
              collider='box')
cl13 = Entity(model='cube', scale=(100, 6, 140), position=(91, 2, -2), rotation=(-1, 0, -5), color=color.clear,
              collider='box')
cl14 = Entity(model='cube', scale=(34, 5.5, 45), position=(87, 2.5, -52.41), rotation=(18, 0, -9), color=color.clear,
              collider='box')
cl15 = Entity(model='cube', scale=(100, 5.5, 70), position=(60, 2, 20), rotation=(0, 0, 23), color=color.clear,
              collider='box')
cl16 = Entity(model='cube', scale=(52, 1, 70), position=(-40, 3.5, -140), rotation=(-8, 0, 0), color=color.clear,
              collider='box')
cl17 = Entity(model='cube', scale=(30, 1, 25), position=(-1, 2, -135), rotation=(0, -18, 8), color=color.clear,
              collider='box')
cl18 = Entity(model='cube', scale=(30, 1, 30), position=(-2, 1.5, -159), rotation=(-4, 0, 0), color=color.clear,
              collider='box')
cl19 = Entity(model='cube', scale=(30, 1, 20), position=(45, 0, -15), rotation=(90, 0, 0), color=color.clear,
              collider='box')


hahaluna=Entity(model='cube',scale=(100,0.1,100),position=(-180,80,130),rotation=(90,0,-60),texture='luna.png',collider='box')
# ИСПРАВЛЯЕМ ЦВЕТ НЕБА (от 0 до 1 вместо 0-255)
sky.color = color.rgb(0.12, 0.1, 0.2)
lvl = 1

coordinates_debug_timer = 0.0


def show_coordinates_console():
    """Показывает координаты игрока в консоли каждую секунду"""
    # Используем глобальную переменную для таймера
    global coordinates_debug_timer

    if 'coordinates_debug_timer' not in globals():
        coordinates_debug_timer = 0.0

    coordinates_debug_timer += time.dt

    if coordinates_debug_timer >= 1.0:
        x = round(player.position.x, 2)
        y = round(player.position.y, 2)
        z = round(player.position.z, 2)

        print(f"📍 Координаты: X={x}, Y={y}, Z={z}")
        coordinates_debug_timer = 0.0


window.fullscreen = False

human = Entity(
    parent=scene, position=(-5, 0, 5))
head = Entity(parent=human, model='Sphere', color=color.white, scale=(0.7, 0.7, 0.7), position=(0.5, 2.2, 1))
body = Entity(parent=human, model='Sphere', color=color.white, scale=(2, 1, 1), position=(0.5, 1, 1),
              rotation=(0, 0, 90))
human_collider = Entity(parent=human, model='cube', scale=(2, 1, 1), position=(0.5, 2.2, 1), color=color.clear,
                        collider='box')

press_e_text = Text("Нажмите E", origin=(0, 0), scale=2,
                    position=(0, .2), color=color.white)
press_e_text.enabled = False

dialogue_bg = Entity(parent=camera.ui, model='quad', scale=(1.6, 1), y=-0.6,
                     color=color.black66)
dialogue_bg.enabled = False

npc_name = Text("Человек", parent=dialogue_bg, y=0.45,
                origin=(0, 0), scale=(2, 2), color=color.white, bold=True)

npc_line = Text("...", parent=dialogue_bg, y=0.4,
                origin=(0, 0), scale=1.1, wordwrap=500)

button1 = Button(text='Привет и пока', color=color.green, scale=(0.2, 0.08),
                 position=(-0.15, -0.45), enabled=False)
button2 = Button(text='Пока', color=color.red, scale=(0.2, 0.08),
                 position=(0.15, -0.45), enabled=False)
button1.enabled = False
button2.enabled = False

in_dialogue = False


def safe_update_enemy_projectiles():
    """Безопасное обновление снарядов врагов"""
    current_time = time.time()

    for proj_idx in range(len(enemy_projectiles) - 1, -1, -1):
        projectile = enemy_projectiles[proj_idx]

        if not projectile or not projectile.enabled:
            if proj_idx < len(enemy_projectiles):
                enemy_projectiles.pop(proj_idx)
            continue

        # Проверяем время жизни
        if hasattr(projectile, 'creation_time'):
            age = current_time - projectile.creation_time
            if age >= projectile.lifetime:
                if hasattr(projectile, 'glow') and projectile.glow:
                    destroy(projectile.glow)
                if hasattr(projectile, 'tracer') and projectile.tracer:
                    destroy(projectile.tracer)
                destroy(projectile)
                enemy_projectiles.pop(proj_idx)
                continue

        # Движение снаряда
        projectile.position += projectile.direction * projectile.speed * time.dt

        # Обновляем связанные эффекты
        if hasattr(projectile, 'glow') and projectile.glow and projectile.glow.enabled:
            projectile.glow.position = projectile.position

        if hasattr(projectile, 'tracer') and projectile.tracer and projectile.tracer.enabled:
            projectile.tracer.position = projectile.position - projectile.direction * 0.8
            projectile.tracer.look_at(projectile.position)

        # Проверка попадания в игрока
        distance_to_player = (projectile.position - player.position).length()
        if distance_to_player < 1.5:  # Радиус попадания
            take_damage(projectile.damage)
            print(f"💥 Снаряд попал в вас! Урон: {projectile.damage}")

            # Эффект попадания
            create_blood_effect_optimized(player.position + Vec3(0, 1, 0))

            # Удаляем снаряд
            if hasattr(projectile, 'glow') and projectile.glow:
                destroy(projectile.glow)
            if hasattr(projectile, 'tracer') and projectile.tracer:
                destroy(projectile.tracer)
            destroy(projectile)
            enemy_projectiles.pop(proj_idx)


def safe_update_effects():
    """Обновляет все эффекты (кровь, трассеры, вспышки)"""
    update_blood_effects_optimized()
    update_shot_effects()
    update_explosive_projectiles()


def update_blood_effects_optimized():
    """Оптимизированное обновление эффектов крови"""
    current_time = time.time()

    # ОГРАНИЧИВАЕМ частоту обновления
    if hasattr(update_blood_effects_optimized, 'last_update_time'):
        if current_time - update_blood_effects_optimized.last_update_time < 0.1:  # Только 10 FPS
            return

    update_blood_effects_optimized.last_update_time = current_time

    cleaned = 0
    for blood_idx in range(len(blood_effects) - 1, -1, -1):
        blood_particles = blood_effects[blood_idx]

        if not blood_particles:
            blood_effects.pop(blood_idx)
            cleaned += 1
            continue

        # Быстрая проверка через счетчик
        valid_particles = 0

        for particle_data in blood_particles[:]:
            if len(particle_data) == 5:
                particle, direction, speed, spawn_time, original_size = particle_data

                if particle and particle.enabled:
                    # БЫСТРАЯ проверка времени жизни
                    age = current_time - spawn_time
                    if age < blood_duration:
                        valid_particles += 1

                        # УПРОЩЕННОЕ обновление (только позиция и прозрачность)
                        if speed > 0:
                            particle.position += direction * speed * time.dt
                            particle.position.y -= time.dt * blood_gravity

                        progress = age / blood_duration
                        particle.alpha = 1.0 - progress
                        particle.scale = original_size * (1 - progress * 0.3)
                    else:
                        destroy(particle)
                        cleaned += 1
                else:
                    cleaned += 1

        # Удаляем пустые группы
        if valid_particles == 0:
            blood_effects.pop(blood_idx)
            cleaned += 1

    # Очистка раз в 10 секунд если слишком много
    if cleaned > 0 or len(blood_effects) > 20:
        print(f"🩸 Оптимизация крови: {len(blood_effects)} групп, очищено {cleaned}")


def update_enemies():
    """Обновляет всех врагов"""
    for enemy in enemies[:]:
        if not enemy or not enemy.entity or not enemy.entity.enabled:
            continue

        # Проверяем время последнего обновления для оптимизации
        current_time = time.time()
        if current_time - enemy.last_update_time < enemy.update_interval:
            continue

        enemy.last_update_time = current_time

        dist_to_player = (enemy.entity.position - player.position).length()

        if dist_to_player <= enemy.detection_range:
            enemy.is_chasing = True

            if dist_to_player > enemy.attack_range:
                target_height = 1.5  # На сколько выше ног идти
                target_point = player.position + Vec3(0, target_height, 0)

                # 2. Двигаемся к этой точке
                direction = (target_point - enemy.entity.position).normalized()
                enemy.entity.position += direction * enemy.chase_speed * time.dt

                # 3. Поворачиваемся смотреть на игрока (только горизонталь)
                # Берем направление в 2D (XZ плоскость), игнорируем высоту
                dx = player.position.x - enemy.entity.position.x
                dz = player.position.z - enemy.entity.position.z

                if abs(dz) > 0.001:  # Маленькое число вместо 0
                    angle_y = math.degrees(math.atan2(dx, dz))
                    enemy.entity.rotation_y = angle_y  # Попробуй с минусом или без

                # 4. Убираем наклоны
                enemy.entity.rotation_x = 0
                enemy.entity.rotation_z = 0

            if dist_to_player <= enemy.attack_range:
                if current_time - enemy.last_attack_time >= enemy.attack_cooldown:
                    attack_player(enemy)
                    enemy.last_attack_time = current_time

            # Проверка застревания
            check_enemy_stuck(enemy)

            # Обновляем визуал
            update_enemy_visuals(enemy)

            # Специальные атаки для босса
            if enemy.type == "boss":
                # Атака волной
                if dist_to_player <= enemy.wave_attack_range:
                    if current_time - enemy.last_special_attack_time >= enemy.special_attack_cooldown:
                        boss_special_attack(enemy)
                        enemy.last_special_attack_time = current_time

                # Атака с разбегом
                if dist_to_player <= enemy.ranged_attack_range:
                    if current_time - enemy.last_charge_attack_time >= enemy.charge_attack_cooldown:
                        boss_charge_attack(enemy)
                        enemy.last_charge_attack_time = current_time

                # Дистанционная атака
                if dist_to_player > enemy.attack_range and dist_to_player <= enemy.ranged_attack_range:
                    if current_time - enemy.last_attack_time >= enemy.attack_cooldown * 0.5:
                        boss_ranged_attack(enemy)
                        enemy.last_attack_time = current_time

            # Дистанционная атака для средних врагов
            elif enemy.type == "medium" and dist_to_player > enemy.attack_range and dist_to_player <= enemy.ranged_attack_range:
                if current_time - enemy.last_attack_time >= enemy.attack_cooldown:
                    ranged_attack(enemy)
                    enemy.last_attack_time = current_time


def start_stage_animation(stage_number):
    """Запускает анимацию для стадии"""
    global stage_animation

    print(f"🎬 Запускаем анимацию для Stage {stage_number}")

    # Определяем тип анимации
    if stage_number == 1:
        animation_type = "first_stage"
        duration = 6.0
    else:
        animation_type = "next_stage"
        duration = 3.0

    # Настраиваем анимацию
    stage_animation["is_playing"] = True
    stage_animation["start_time"] = time.time()
    stage_animation["duration"] = duration
    stage_animation["type"] = animation_type

    # Создаем черный экран только для первой стадии
    if animation_type == "first_stage":
        if not stage_animation["black_screen"]:
            stage_animation["black_screen"] = Entity(
                parent=camera.ui,
                model='quad',
                color=color.black,
                scale=(2, 2),
                z=-1
            )
        else:
            stage_animation["black_screen"].enabled = True
            stage_animation["black_screen"].color = color.black

    # Создаем текст стадии
    if stage_animation["stage_text"]:
        destroy(stage_animation["stage_text"])

    stage_animation["stage_text"] = Text(
        parent=camera.ui,
        text=f"STAGE {stage_number}",
        scale=4,
        color=color.white,
        z=-2,
        origin=(0, 0),
        font='custom2.ttf'
    )

    # Начальная прозрачность
    if animation_type == "first_stage":
        stage_animation["stage_text"].alpha = 1.0
    else:
        stage_animation["stage_text"].alpha = 0.0


def update_stage_animation():
    """Обновляет анимацию стадии"""
    global stage_animation

    if not stage_animation["is_playing"]:
        return

    current_time = time.time()
    progress = (current_time - stage_animation["start_time"]) / stage_animation["duration"]

    # Анимация для первой стадии (6 секунд)
    if stage_animation["type"] == "first_stage":
        if progress < 0.5:
            # Первые 3 секунды - показываем текст и черный фон
            stage_animation["stage_text"].alpha = 1.0
            stage_animation["black_screen"].color = color.rgba(0, 0, 0, 1.0)
        else:
            # Последние 3 секунды - плавно исчезаем
            fade_progress = (progress - 0.5) / 0.5
            stage_animation["stage_text"].alpha = 1.0 - fade_progress
            stage_animation["black_screen"].color = color.rgba(0, 0, 0, 1.0 - fade_progress)

    # Анимация для следующих стадий (3 секунды)
    else:
        if progress < 0.3:
            # Появление текста (0.9 сек)
            stage_animation["stage_text"].alpha = progress / 0.3
        elif progress < 0.7:
            # Текст виден (1.2 сек)
            stage_animation["stage_text"].alpha = 1.0
        else:
            # Исчезновение текста (0.9 сек)
            fade_progress = (progress - 0.7) / 0.3
            stage_animation["stage_text"].alpha = 1.0 - fade_progress

    # Завершение анимации
    if progress >= 1.0:
        finish_stage_animation()


def finish_stage_animation():
    """Завершает анимацию и запускает спавн врагов"""
    global stage_animation, enemies_spawned_for_current_stage
    global stage_enemies_spawned, stage_enemies_killed, enemies_to_kill_for_stage

    print(f"✅ Анимация завершена, спавним врагов для Stage {current_stage}...")

    # Скрываем элементы
    if stage_animation["black_screen"]:
        stage_animation["black_screen"].enabled = False
    if stage_animation["stage_text"]:
        stage_animation["stage_text"].enabled = False

    # Завершаем анимацию
    stage_animation["is_playing"] = False

    # СПАВНИМ ВРАГОВ ПОСЛЕ АНИМАЦИИ
    stage_enemies_killed = 0
    spawn_stage_enemies_simple()
    enemies_spawned_for_current_stage = True
    stage_enemies_spawned = True
    enemies_to_kill_for_stage = total_enemies_on_map

    reset_performance()
    update_shader_intensity()

    print(f"🎯 STAGE {current_stage} начался! Убейте {enemies_to_kill_for_stage} врагов")

    # СПЕЦИАЛЬНЫЕ СОБЫТИЯ
    if current_stage == 10 and "assault_rifle" not in unlocked_weapons:
        print("🎉 10 STAGE! Поищите автомат на карте!")
        invoke(spawn_assault_rifle_pickup, delay=2.0)

    elif current_stage == 15 and "dual_uzi" not in unlocked_weapons:
        print("🎉 15 STAGE! Поищите Dual Uzi на карте!")
        invoke(spawn_dual_uzi_pickup, delay=2.0)
        show_mission_text("ЗАДАНИЕ: Найдите Dual Uzi!!!")

    elif current_stage == 20 and "grenade_launcher" not in unlocked_weapons:
        print("🎉 20 STAGE! Поищите гранатомет на карте!")
        invoke(spawn_grenade_launcher_pickup, delay=2.0)
        show_mission_text("Задаааани##$:Na$^%ydi 545t mo45delName:Gre24$^&nade")

    if current_stage % 5 == 0:
        spawn_healkits()
        safe_render_cleanup()
        spawn_ammo_boxes()
        print(f"🎁 Бонусы на stage {current_stage}!")


def update_stage():
    """Простая логика обновления стадии"""
    global stage_enemies_spawned, stage_enemies_killed, enemies_to_kill_for_stage
    global current_mission_text, enemies_spawned_for_current_stage, stage_animation

    # Если враги уже заспавнены или идет анимация - выходим
    if enemies_spawned_for_current_stage or stage_animation["is_playing"]:
        return

    # ЗАПУСКАЕМ АНИМАЦИЮ ДЛЯ ТЕКУЩЕЙ СТАДИИ
    print(f"🎬 Запускаем анимацию для Stage {current_stage}")
    start_stage_animation(current_stage)


def show_mission_text(text):
    global current_mission_text

    # Убираем предыдущий текст задания
    if current_mission_text:
        destroy(current_mission_text)

    # Создаем новый текст задания
    current_mission_text = Text(
        parent=camera.ui,
        text=text,
        position=(-0.8, -0.4, 0),
        scale=2,
        color=color.yellow,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.7),
        font='custom2.ttf'
    )

    # Автоматически убираем через 10 секунд
    invoke(hide_mission_text, delay=10.0)


def hide_mission_text():
    global current_mission_text
    if current_mission_text:
        destroy(current_mission_text)
        current_mission_text = None


def spawn_dual_uzi_pickup():
    """Спавнит Dual Uzi на карте"""
    spawn_position = (-66, 1.5, -163)

    # Создаем модель Dual Uzi
    dual_uzi_pickup = Entity(
        model='decore_dual_uzi.glb',
        position=spawn_position,
        scale=2.0,
        collider='box',
        shader=dark_fantasy_shader
    )

    # АНИМАЦИЯ ВРАЩЕНИЯ
    def rotate_weapon():
        if dual_uzi_pickup and dual_uzi_pickup.enabled:
            dual_uzi_pickup.animate_rotation_y(dual_uzi_pickup.rotation_y + 360, duration=3, curve=curve.linear)
            invoke(rotate_weapon, delay=3)

    # АНИМАЦИЯ ПЛАВАНИЯ ВВЕРХ-ВНИЗ
    def float_weapon():
        if dual_uzi_pickup and dual_uzi_pickup.enabled:
            # Анимация вверх
            dual_uzi_pickup.animate_y(dual_uzi_pickup.y + 0.4, duration=1.5, curve=curve.in_out_quad)
            # Анимация вниз через 1.5 секунды
            invoke(lambda: dual_uzi_pickup.animate_y(dual_uzi_pickup.y - 0.4, duration=1.5, curve=curve.in_out_quad)
            if dual_uzi_pickup and dual_uzi_pickup.enabled else None, delay=1.5)
            # Повторяем всю последовательность через 3 секунды
            invoke(float_weapon, delay=3.0)

    # ЭФФЕКТ СВЕЧЕНИЯ (фиолетовый для Uzi)
    glow = Entity(
        model='sphere',
        color=color.rgba(0.8, 0.2, 1.0, 0.3),  # Фиолетовое свечение
        scale=2.5,
        position=spawn_position,
        add_to_scene_entities=True
    )

    def update_glow():
        if glow and glow.enabled:
            pulse = math.sin(time.time() * 5) * 0.2 + 0.8
            glow.scale = 2.5 * pulse
            invoke(update_glow, delay=1 / 30)

    # ЗАПУСКАЕМ АНИМАЦИИ
    rotate_weapon()
    float_weapon()
    update_glow()

    weapon_pickups.append({
        'entity': dual_uzi_pickup,
        'glow': glow,
        'weapon_type': 'dual_uzi'
    })

    print("🔫 Dual Uzi заспавнен на карте! Найдите его!")
    return dual_uzi_pickup


def spawn_grenade_launcher_pickup():
    """Спавнит гранатомет на карте"""
    spawn_position = find_valid_spawn_position()

    # Создаем модель гранатомета
    grenade_launcher_pickup = Entity(
        model='decore_grenade.glb',  # Используем модель гранаты как временную
        position=spawn_position,
        scale=0.2,
        collider='box',
        shader=dark_fantasy_shader
    )

    # АНИМАЦИЯ ВРАЩЕНИЯ
    def rotate_weapon():
        if grenade_launcher_pickup and grenade_launcher_pickup.enabled:
            grenade_launcher_pickup.animate_rotation_y(grenade_launcher_pickup.rotation_y + 360, duration=3,
                                                       curve=curve.linear)
            invoke(rotate_weapon, delay=3)

    # АНИМАЦИЯ ПЛАВАНИЯ ВВЕРХ-ВНИЗ
    def float_weapon():
        if grenade_launcher_pickup and grenade_launcher_pickup.enabled:
            # Анимация вверх
            grenade_launcher_pickup.animate_y(grenade_launcher_pickup.y + 0.4, duration=1.5, curve=curve.in_out_quad)
            # Анимация вниз через 1.5 секунды
            invoke(lambda: grenade_launcher_pickup.animate_y(grenade_launcher_pickup.y - 0.4, duration=1.5,
                                                             curve=curve.in_out_quad)
            if grenade_launcher_pickup and grenade_launcher_pickup.enabled else None, delay=1.5)
            # Повторяем всю последовательность через 3 секунды
            invoke(float_weapon, delay=3.0)

    # ЭФФЕКТ СВЕЧЕНИЯ (зеленый для гранатомета)
    glow = Entity(
        model='sphere',
        color=color.rgba(0.2, 1.0, 0.2, 0.3),  # Зеленое свечение
        scale=2.5,
        position=spawn_position,
        add_to_scene_entities=True
    )

    def update_glow():
        if glow and glow.enabled:
            pulse = math.sin(time.time() * 5) * 0.2 + 0.8
            glow.scale = 2.5 * pulse
            invoke(update_glow, delay=1 / 30)

    # ЗАПУСКАЕМ АНИМАЦИИ
    rotate_weapon()
    float_weapon()
    update_glow()

    weapon_pickups.append({
        'entity': grenade_launcher_pickup,
        'glow': glow,
        'weapon_type': 'grenade_launcher'
    })

    print("🚀 Гранатомет заспавнен на карте! Найдите его!")
    return grenade_launcher_pickup


# ФУНКЦИЯ СПАВНА ВРАГОВ ДЛЯ ТЕКУЩЕГО СТЕЙДЖА
def spawn_stage_enemies_simple():
    """Простой спавн врагов без сложных проверок"""
    global total_enemies_on_map

    print(f"🔄 Спавн врагов для stage {current_stage}...")

    # ОБЩЕЕ КОЛИЧЕСТВО СЛАБЫХ ВРАГОВ
    total_normal_required = 3 + (current_stage - 1) * 3
    normal_enemies_to_spawn = max(0, total_normal_required - total_enemies_on_map)

    print(f"📌 Должно быть слабых: {total_normal_required}")
    print(f"📌 Сейчас на карте: {total_enemies_on_map}")
    print(f"📌 Нужно доспавнить слабых: {normal_enemies_to_spawn}")

    # СПАВНИМ СЛАБЫХ
    for i in range(normal_enemies_to_spawn):
        if spawn_enemy_at_random_position("normal"):
            total_enemies_on_map += 1

    # СРЕДНИЕ ВРАГИ
    medium_count = current_stage // 5
    current_medium_count = count_enemies_by_type("medium")
    medium_to_spawn = max(0, medium_count - current_medium_count)

    for i in range(medium_to_spawn):
        if spawn_enemy_at_random_position("medium"):
            total_enemies_on_map += 1
            print(f"⚔️ Средний враг добавлен! ({current_medium_count + i + 1}/{medium_count})")

    # БОССЫ
    boss_count = current_stage // 10
    current_boss_count = count_enemies_by_type("boss")
    boss_to_spawn = max(0, boss_count - current_boss_count)

    for i in range(boss_to_spawn):
        if spawn_enemy_at_random_position("boss"):
            total_enemies_on_map += 1
            print(f"👑 БОСС добавлен! ({current_boss_count + i + 1}/{boss_count})")

    print(f"📊 Теперь врагов на карте: {total_enemies_on_map}")
    print(
        f"🎯 Состав: {count_enemies_by_type('normal')} слабых, {count_enemies_by_type('medium')} средних, {count_enemies_by_type('boss')} боссов")


# ФУНКЦИЯ ДЛЯ ПОДСЧЕТА ВРАГОВ ПО ТИПУ
def count_enemies_by_type(enemy_type):
    count = 0
    for enemy in enemies:
        if enemy and enemy.type == enemy_type and enemy.entity.enabled:
            count += 1
    return count


def check_stage_completion():
    global stage_enemies_spawned, current_stage, enemies_spawned_for_current_stage
    global stage_start_time, stage_animation

    # Проверяем только если враги заспавнены и все убиты
    if not enemies_spawned_for_current_stage or stage_animation["is_playing"]:
        return

    if stage_enemies_killed >= enemies_to_kill_for_stage:
        print(f"🎉 Stage {current_stage} завершён!")

        # Сбрасываем флаги для следующей стадии
        stage_enemies_spawned = False
        enemies_spawned_for_current_stage = False

        # Переходим к следующей стадии
        current_stage += 1

        # ОБНОВЛЯЕМ ИНТЕНСИВНОСТЬ ШЕЙДЕРА ДЛЯ НОВОГО УРОВНЯ
        update_shader_intensity()

        # Сразу запускаем анимацию для новой стадии
        if current_stage > 1:  # Для Stage 2+ сразу запускаем анимацию
            start_stage_animation(current_stage)

        print(f"🔄 Stage {current_stage} начинается...")


def spawn_enemy_at_random_position(enemy_type):
    try:
        # Генерируем случайную позицию на карте
        x = random.uniform(-20, 20)
        z = random.uniform(-20, 20)

        # Проверяем, чтобы враг не заспавнился слишком близко к игроку
        spawn_pos = Vec3(x, 1, z)
        if (spawn_pos - player.position).length() < 8:
            # Если слишком близко, пробуем еще раз
            return spawn_enemy_at_random_position(enemy_type)

        create_enemy(spawn_pos, enemy_type)
        return True
    except:
        return False


def spawn_healkits():
    print(f"💚 Спавн 2 хилки на stage {current_stage}")

    spawned_count = 0
    for i in range(2):
        position = find_valid_spawn_position()

        if is_position_in_spawn_area(position):
            create_heal_pickup(position)
            spawned_count += 1
            print(f"  Аптечка {i + 1}: X={position.x:.1f}, Z={position.z:.1f}")
        else:
            print(f"❌ Аптечка вне зон: X={position.x:.1f}, Z={position.z:.1f}")
            # Исправляем позицию
            corrected_pos = find_valid_spawn_position()
            create_heal_pickup(corrected_pos)
            spawned_count += 1

    print(f"✅ Заспавнено {spawned_count} аптечек")


def spawn_ammo_boxes():
    print(f"🔫 Спавн 4 коробки патронов на stage {current_stage}")

    spawned_count = 0
    for i in range(4):
        position = find_valid_spawn_position()

        if is_position_in_spawn_area(position):
            create_ammo_pickup(position)
            spawned_count += 1
            print(f"  Патроны {i + 1}: X={position.x:.1f}, Z={position.z:.1f}")
        else:
            print(f"❌ Патроны вне зон: X={position.x:.1f}, Z={position.z:.1f}")
            # Исправляем позицию
            corrected_pos = find_valid_spawn_position()
            create_ammo_pickup(corrected_pos)
            spawned_count += 1

    print(f"✅ Заспавнено {spawned_count} коробок патронов")


def is_position_in_spawn_area(position):
    """Проверяет, находится ли позиция в одной из двух областей спавна"""
    # ПРОВЕРКА ПЕРВОЙ ЗОНЫ
    in_zone1 = (43 <= position.x <= 63 and -116 <= position.z <= -46)

    # ПРОВЕРКА ВТОРОЙ ЗОНЫ
    in_zone2 = (-56 <= position.x <= -6 and -203 <= position.z <= -153)

    return in_zone1 or in_zone2


# ОБНОВЛЯЕМ ФУНКЦИЮ УБИЙСТВА ВРАГА
def on_enemy_killed():
    global stage_enemies_killed, total_enemies_on_map

    stage_enemies_killed += 1
    total_enemies_on_map -= 1

    print(f"💀 Враг убит! Прогресс: {stage_enemies_killed}/{enemies_to_kill_for_stage}")

    check_stage_completion()


# ИСПРАВЛЕННАЯ ФУНКЦИЯ СОЗДАНИЯ ВРАГА
def create_enemy(position, enemy_type="normal"):
    enemy = Enemy(position, enemy_type)
    enemies.append(enemy)

    # Сохраняем оригинальную сущность врага
    enemy_entity = enemy.entity

    # Переопределяем метод уничтожения для отслеживания убийств
    def custom_destroy():
        on_enemy_killed()
        if enemy_entity and enemy_entity.enabled:
            enemy_entity.enabled = False
            # Удаляем из списка врагов
            if enemy in enemies:
                enemies.remove(enemy)

    # Присваиваем кастомную функцию уничтожения
    enemy_entity.destroy = custom_destroy

    return enemy


def create_homing_enemy_projectile(position, target_position, speed=ENEMY_PROJECTILE_SPEED, damage=8,
                                   color_type=color.rgba(1, 0.6, 0.2, 1), homing_strength=1.0, explosion_radius=3.0):
    """Создает снаряд врага который целится в тело игрока"""

    # Целимся в тело (высота 1.8 вместо ног)
    corrected_target = Vec3(
        target_position.x,
        target_position.y + 1.8,  # ТЕЛО, а не ноги
        target_position.z
    )

    actual_speed = uniform(ENEMY_PROJECTILE_MIN_SPEED, speed)

    projectile = Entity(
        model='sphere',
        color=color_type,
        scale=0.9,
        position=position,
        add_to_scene_entities=True,
        eternal=False
    )

    glow = Entity(
        model='sphere',
        color=color.rgba(color_type[0], color_type[1], color_type[2], 0.5),
        scale=1.2,
        position=position,
        add_to_scene_entities=True,
        eternal=False
    )

    # Направление к телу
    direction = (corrected_target - position).normalized()

    projectile.direction = direction
    projectile.speed = actual_speed
    projectile.damage = damage
    projectile.creation_time = time.time()
    projectile.lifetime = 8.0
    projectile.homing_strength = homing_strength
    projectile.glow = glow
    projectile.explosion_radius = explosion_radius
    projectile.homing_active = True
    projectile.turn_speed = ENEMY_PROJECTILE_TURN_SPEED
    projectile.detection_radius = ENEMY_PROJECTILE_DETECTION_RADIUS
    projectile.has_exploded = False

    enemy_projectiles.append(projectile)
    return projectile


# Функция для создания лужи крови
def create_blood_puddle(position):
    puddle = Entity(
        model='circle',
        color=color.rgba(0.6, 0, 0, 1),
        scale=uniform(1.5, 2.5),
        position=(position.x, 0.01, position.z),  # Чуть выше земли
        rotation=(90, 0, 0),
        add_to_scene_entities=True
    )

    # Добавляем в эффекты крови для автоматического удаления
    blood_particles = [(puddle, Vec3(0, 0, 0), 0, time.time(), 1.0)]
    blood_effects.append(blood_particles)


# Функция для создания брызг крови на стены
def create_blood_splatters(position):
    splatter_count = 8

    for k in range(splatter_count):  # меняем i на k
        splatter_direction = Vec3(
            uniform(-1, 1),
            uniform(0.5, 1.5),
            uniform(-1, 1)
        ).normalized()

        splatter_pos = position + splatter_direction * uniform(0.5, 2.0)
        splatter_pos.y = uniform(0.5, 2.0)

        splatter = Entity(
            model='cube',
            color=color.rgba(0.6, 0, 0, 1),
            scale=(uniform(0.1, 0.3), uniform(0.1, 0.3), 0.01),
            position=splatter_pos,
            add_to_scene_entities=True
        )

        splatter.look_at(splatter_pos + splatter_direction)
        blood_particles = [(splatter, Vec3(0, 0, 0), 0, time.time(), 1.0)]
        blood_effects.append(blood_particles)


# Функция для проверки попаданий в NPC
# ИСПРАВЛЕННАЯ ФУНКЦИЯ ПРОВЕРКИ ПОПАДАНИЙ
def check_bullet_hits():
    for bullet_idx in range(len(bullet_tracers) - 1, -1, -1):
        tracer_data = bullet_tracers[bullet_idx]

        if not tracer_data or len(tracer_data) != 2:
            continue

        tracer, spawn_time = tracer_data

        if not tracer or not tracer.enabled:
            continue

        for enemy_idx in range(len(enemies) - 1, -1, -1):
            enemy = enemies[enemy_idx]

            if not enemy or not enemy.entity or not enemy.entity.enabled:
                continue

            dist_to_enemy = (tracer.position - enemy.entity.position).length()
            if dist_to_enemy < (1.0 if enemy.type == "normal" else 2.0 if enemy.type == "medium" else 4.0):
                enemy.hit_count += 1
                enemy.health -= 1

                print(f"🎯 Попадание в {enemy.type} врага! Здоровье: {enemy.health}/{enemy.max_health}")

                try:
                    create_blood_effect_optimized(enemy.entity.position + Vec3(0, 1, 0))
                except Exception as e:
                    print(f"⚠️ Ошибка создания эффекта крови: {e}")

                if enemy.health <= 0:
                    print(f"💀 {enemy.type.capitalize()} враг уничтожен!")

                    try:
                        create_blood_effect_optimized(enemy.entity.position + Vec3(0, 1, 0))
                    except:
                        pass

                    # ВЫЗЫВАЕМ ФУНКЦИЮ УБИЙСТВА ПЕРЕД УДАЛЕНИЕМ
                    on_enemy_killed()

                    # Уничтожаем врага
                    try:
                        destroy(enemy.entity)
                    except:
                        pass

                    if enemy in enemies:
                        enemies.remove(enemy)

                try:
                    destroy(tracer)
                except:
                    pass

                bullet_tracers.pop(bullet_idx)
                break


def update_enemy_projectiles():
    """Обновляет снаряды врагов с очень слабым наведением"""
    current_time = time.time()

    for proj_idx in range(len(enemy_projectiles) - 1, -1, -1):
        projectile = enemy_projectiles[proj_idx]

        if not projectile or not projectile.enabled:
            cleanup_projectile_effects(projectile)
            enemy_projectiles.pop(proj_idx)
            continue

        # Обеспечиваем наличие всех атрибутов
        ensure_projectile_attributes(projectile)

        age = current_time - projectile.creation_time

        # Проверка времени жизни
        if age >= projectile.lifetime:
            explosion_radius = getattr(projectile, 'explosion_radius', 3.0)
            create_projectile_explosion(projectile.position, explosion_radius)
            cleanup_projectile_effects(projectile)
            enemy_projectiles.pop(proj_idx)
            continue

        # ВАЖНОЕ ИЗМЕНЕНИЕ: ОЧЕНЬ СЛАБЫЙ ХОМИНГ
        if hasattr(projectile, 'is_homing') and projectile.is_homing:
            # Проверяем расстояние до игрока - наводимся только если близко
            distance_to_player = (projectile.position - player.position).length()

            # Наводимся только если снаряд далеко от игрока (> 10 единиц) или первые 2 секунды полета
            if distance_to_player > 10 or age < 2.0:
                # Очень слабое наведение
                if not hasattr(projectile, 'turn_speed'):
                    projectile.turn_speed = ENEMY_PROJECTILE_TURN_SPEED

                # Направление к игроку
                to_player = (player.position - projectile.position).normalized()

                # Очень медленная коррекция (10% от обычной)
                correction_strength = 0.1 * projectile.turn_speed * time.dt
                projectile.direction = lerp(projectile.direction, to_player, correction_strength).normalized()
            else:
                # Близко к игроку - летим прямо
                pass

        # ДВИЖЕНИЕ СНАРЯДА С ГРАВИТАЦИЕЙ
        if hasattr(projectile, 'direction') and hasattr(projectile, 'speed'):
            # Обновляем вертикальную скорость от гравитации
            if hasattr(projectile, 'gravity'):
                projectile.velocity_y += projectile.gravity * time.dt
                # Обновляем направление с учетом вертикальной скорости
                move_direction = Vec3(
                    projectile.direction.x,
                    projectile.direction.y + projectile.velocity_y * 0.1,
                    projectile.direction.z
                ).normalized()
            else:
                move_direction = projectile.direction

            # Медленное движение
            projectile.position += move_direction * projectile.speed * time.dt

        # ВРАЩЕНИЕ (медленное)
        projectile.rotation_x += time.dt * 50
        projectile.rotation_y += time.dt * 40

        # ОБНОВЛЕНИЕ СВЕЧЕНИЯ
        if hasattr(projectile, 'glow') and projectile.glow and projectile.glow.enabled:
            projectile.glow.position = projectile.position

            # Мерцание
            pulse = math.sin(time.time() * 3) * 0.1 + 0.9
            projectile.glow.scale = 1.3 * pulse
            projectile.glow.color = color.rgba(
                projectile.glow.color.r,
                projectile.glow.color.g,
                projectile.glow.color.b,
                0.3 + 0.2 * pulse
            )

        # Проверка приближения к игроку
        distance_to_player = (projectile.position - player.position).length()
        detection_radius = getattr(projectile, 'detection_radius', ENEMY_PROJECTILE_DETECTION_RADIUS)

        # Если снаряд близко к игроку - взрыв
        if distance_to_player < detection_radius and not getattr(projectile, 'has_exploded', False):
            print(f"💥 Снаряд приблизился на {distance_to_player:.1f} единиц!")

            damage = getattr(projectile, 'damage', 8)
            take_damage(damage)

            # Взрыв
            explosion_radius = getattr(projectile, 'explosion_radius', 3.0)
            create_projectile_explosion(projectile.position, explosion_radius)

            projectile.has_exploded = True
            cleanup_projectile_effects(projectile)
            enemy_projectiles.pop(proj_idx)
            continue

        # Столкновение с землей
        if projectile.position.y < 0.5:
            explosion_radius = getattr(projectile, 'explosion_radius', 3.0)
            create_projectile_explosion(projectile.position, explosion_radius)
            cleanup_projectile_effects(projectile)
            enemy_projectiles.pop(proj_idx)


def ensure_projectile_attributes(projectile):
    """Обеспечивает, что у снаряда есть все необходимые атрибуты"""
    if not hasattr(projectile, 'explosion_radius'):
        projectile.explosion_radius = 3.0
    if not hasattr(projectile, 'detection_radius'):
        projectile.detection_radius = ENEMY_PROJECTILE_DETECTION_RADIUS
    if not hasattr(projectile, 'speed'):
        projectile.speed = uniform(ENEMY_PROJECTILE_MIN_SPEED, ENEMY_PROJECTILE_SPEED)
    if not hasattr(projectile, 'damage'):
        projectile.damage = 8
    if not hasattr(projectile, 'lifetime'):
        projectile.lifetime = 10.0
    if not hasattr(projectile, 'has_exploded'):
        projectile.has_exploded = False
    if not hasattr(projectile, 'is_homing'):
        projectile.is_homing = True
    if not hasattr(projectile, 'turn_speed'):
        projectile.turn_speed = ENEMY_PROJECTILE_TURN_SPEED
    if not hasattr(projectile, 'direction'):
        projectile.direction = Vec3(0, 0, -1)
    if not hasattr(projectile, 'gravity'):
        projectile.gravity = -0.5
    if not hasattr(projectile, 'velocity_y'):
        projectile.velocity_y = 0
    if not hasattr(projectile, 'homing_strength'):
        projectile.homing_strength = 0.5


def cleanup_projectile_effects(projectile):
    """Очищает все эффекты связанные со снарядом"""
    if not projectile:
        return

    # Список связанных объектов
    related_objects = []

    # Добавляем все возможные связанные объекты
    if hasattr(projectile, 'glow'):
        related_objects.append(projectile.glow)

    if hasattr(projectile, 'tracer'):
        related_objects.append(projectile.tracer)
    if hasattr(projectile, 'particles'):
        related_objects.extend(projectile.particles)

    # Уничтожаем основной снаряд
    try:
        destroy(projectile)
    except:
        pass

    # Уничтожаем связанные объекты
    for obj in related_objects:
        if obj and hasattr(obj, 'enabled') and obj.enabled:
            try:
                destroy(obj)
            except:
                pass


def convert_old_projectiles():
    """Преобразует старые снаряды в новые с атрибутами"""
    for projectile in enemy_projectiles:
        if not hasattr(projectile, 'turn_speed'):
            # Добавляем недостающие атрибуты
            projectile.turn_speed = 5.0
            projectile.homing_strength = 1.0
            projectile.homing_active = True
            projectile.explosion_radius = 3.0

            # Если нет направления, создаем случайное
            if not hasattr(projectile, 'direction'):
                projectile.direction = Vec3(
                    uniform(-0.5, 0.5),
                    uniform(-0.2, 0.5),
                    uniform(-1, -0.5)
                ).normalized()

            # Если нет скорости
            if not hasattr(projectile, 'speed'):
                projectile.speed = uniform(8, 12)

            # Если нет урона
            if not hasattr(projectile, 'damage'):
                projectile.damage = 10

            # Если нет времени создания
            if not hasattr(projectile, 'creation_time'):
                projectile.creation_time = time.time()

            # Если нет времени жизни
            if not hasattr(projectile, 'lifetime'):
                projectile.lifetime = 4.0

            print(f"🔧 Преобразован старый снаряд")


def create_bounce_effect(position):
    for bounce_idx in range(6):  # меняем j на bounce_idx
        bounce_particle = Entity(
            model='sphere',
            color=color.rgba(0.8, 0.6, 0.2, 1),
            scale=uniform(0.2, 0.4),
            position=position,
            add_to_scene_entities=True
        )

        bounce_direction = Vec3(  # меняем dir на bounce_direction
            uniform(-1, 1),
            uniform(0.2, 0.8),
            uniform(-1, 1)
        ).normalized()

        def animate_bounce(particle=bounce_particle, direction=bounce_direction):  # меняем dir на direction
            start_time = time.time()
            lifetime = 0.8
            start_scale = particle.scale

            def update_bounce():
                current_time = time.time()
                age = current_time - start_time

                if age < lifetime and particle.enabled:
                    particle.position += direction * 4 * time.dt
                    progress = age / lifetime
                    particle.scale = start_scale * (1 - progress)
                    particle.alpha = 1 - progress
                    invoke(update_bounce, delay=1 / 60)
                else:
                    destroy(particle)

            update_bounce()

        animate_bounce()


def check_projectile_hit(projectile, old_pos, new_pos):
    # Простая проверка расстояния до игрока
    distance_to_player = (projectile.position - player.position).length()
    if distance_to_player < 1.8:  # Увеличил зону попадания для снарядов
        return True

    # Дополнительная проверка пересечения луча
    ray_direction = (new_pos - old_pos).normalized()
    ray_distance = (new_pos - old_pos).length()

    hit_info = raycast(old_pos, ray_direction, distance=ray_distance + 1.0)
    if hit_info.hit:
        player_collider_distance = (player.position - hit_info.point).length()
        if player_collider_distance < 2.0:
            return True

    return False


def create_projectile_explosion(position, radius=3.0):
    """Создает эффект взрыва снаряда"""
    # ВСЕГДА используем защиту от ошибок
    try:
        if not position:
            position = Vec3(0, 0, 0)

        print(f"💥 Взрыв снаряда! Радиус: {radius}")

        # Основной взрыв
        explosion = Entity(
            model='sphere',
            color=color.orange,
            scale=0.1,
            position=position,
            add_to_scene_entities=True,
            eternal=False
        )

        # Анимация расширения взрыва
        explosion.animate_scale(radius * 2, duration=0.3, curve=curve.out_quad)
        explosion.animate_color(color.red, duration=0.2)

        # Вспышка в центре
        flash = Entity(
            model='sphere',
            color=color.yellow,
            scale=0.2,
            position=position,
            add_to_scene_entities=True,
            eternal=False
        )
        flash.animate_scale(radius, duration=0.15)
        flash.animate_color(color.rgba(1, 1, 0, 0), duration=0.15)

        # Партиклы взрыва
        for i in range(8):  # Меньше частиц для производительности
            particle = Entity(
                model='cube',
                color=lerp(color.orange, color.yellow, random.random()),
                scale=uniform(0.2, 0.4),
                position=position,
                add_to_scene_entities=True,
                eternal=False
            )

            direction = Vec3(
                uniform(-1, 1),
                uniform(0, 1),
                uniform(-1, 1)
            ).normalized()

            speed = uniform(3, 8)
            lifetime = uniform(0.5, 1.0)

            animate_explosion_particle(particle, direction, speed, lifetime)

        # Удаление эффектов
        def cleanup_explosion():
            try:
                if explosion and explosion.enabled:
                    destroy(explosion)
                if flash and flash.enabled:
                    destroy(flash)
            except:
                pass

        invoke(cleanup_explosion, delay=1.0)

        # Урон игроку если он в радиусе взрыва
        try:
            distance_to_player = (position - player.position).length()
            if distance_to_player < radius:
                damage = int(25 * (1 - distance_to_player / radius))
                if damage > 0:
                    print(f"💥 Взрывная волна! Урон: {damage}")
                    take_damage(damage)

                    # Отбрасывание игрока
                    push_direction = (player.position - position).normalized()
                    push_strength = 8 * (1 - distance_to_player / radius)
                    player.position += push_direction * push_strength * time.dt * 3
        except:
            pass

    except Exception as e:
        print(f"⚠️ Ошибка при создании взрыва: {e}")

    # Удаление эффектов
    def cleanup_explosion():
        if explosion and explosion.enabled:
            destroy(explosion)
        if flash and flash.enabled:
            destroy(flash)

    invoke(cleanup_explosion, delay=1.0)

    # Урон игроку если он в радиусе взрыва
    distance_to_player = (position - player.position).length()
    if distance_to_player < radius:
        damage = int(30 * (1 - distance_to_player / radius))  # Уменьшение урона с расстоянием
        if damage > 0:
            print(f"💥 Взрывная волна! Урон: {damage}")
            take_damage(damage)

            # Отбрасывание игрока
            push_direction = (player.position - position).normalized()
            push_strength = 10 * (1 - distance_to_player / radius)
            player.position += push_direction * push_strength * time.dt * 5


def boss_ranged_attack(enemy):
    """Атака босса снарядами в тело"""
    for i in range(3):
        delay = i * 0.3

        def create_delayed_shot(d=i):
            if enemy not in enemies or not enemy.entity.enabled:
                return

            offset = Vec3(
                (d - 1) * 1.5,
                3,
                0
            )

            projectile = create_homing_enemy_projectile(
                position=enemy.entity.position + offset,
                target_position=Vec3(player.position.x, player.position.y + 1.8, player.position.z),  # ТЕЛО
                speed=12.0,
                damage=15,
                color_type=color.rgba(1, 0.1, 0.1, 1),
                homing_strength=1.5,
                explosion_radius=4.0
            )

        invoke(create_delayed_shot, delay=delay)


def ranged_attack(enemy):
    """Атака среднего врага снарядами в тело"""
    current_time = time.time()

    if not hasattr(enemy, 'last_ranged_attack_time'):
        enemy.last_ranged_attack_time = 0

    if current_time - enemy.last_ranged_attack_time < ENEMY_PROJECTILE_COOLDOWN:
        return

    enemy.last_ranged_attack_time = current_time

    projectile = create_homing_enemy_projectile(
        position=enemy.entity.position + Vec3(0, 2, 0),
        target_position=Vec3(player.position.x, player.position.y + 1.8, player.position.z),  # ТЕЛО
        speed=ENEMY_PROJECTILE_SPEED,
        damage=8,
        color_type=color.rgba(1, 0.6, 0.2, 1),
        homing_strength=1.0,
        explosion_radius=3.5
    )


def attack_player(enemy):
    dist = (enemy.entity.position - player.position).length()
    if dist <= enemy.attack_range:
        take_damage(enemy.damage)  # Используем новую функцию

        # Визуальный эффект попадания
        if enemy.type == "normal":
            create_blood_effect_optimized(player.position + Vec3(0, 1, 0))  # <-- ИСПОЛЬЗУЕМ _optimized версию
        elif enemy.type == "medium":
            create_blood_effect_optimized(player.position + Vec3(0, 1.5, 0))  # <-- ИСПОЛЬЗУЕМ _optimized версию
        else:
            create_blood_effect_optimized(player.position + Vec3(0, 2, 0))  # <-- ИСПОЛЬЗУЕМ _optimized версию


def ranged_attack(enemy):
    # Оранжевые снаряды среднего врага
    medium_color = color.rgba(1, 0.6, 0.2, 1)

    create_homing_projectile(
        enemy.entity.position + Vec3(0, 2, 0),
        (player.position - enemy.entity.position).normalized(),
        speed=13.0,
        damage=5,
        color_type=medium_color,
        homing_strength=2.0
    )
    print(f"🎯 Средний враг выстрелил в вас!")


def create_homing_projectile(position, direction, speed, damage, color_type, homing_strength=1.0):
    projectile = Entity(
        model='sphere',
        color=color_type,
        scale=0.8,  # Восстанавливаем красивый размер
        position=position,
        add_to_scene_entities=True
    )

    # Эффект свечения (красивый)
    glow = Entity(
        model='sphere',
        color=lerp(color_type, color.white, 0.3),
        scale=1.2,
        position=position,
        add_to_scene_entities=True
    )
    glow.alpha = 0.5

    # # Трассер за снарядом
    # tracer = Entity(
    #     model='cube',
    #     color=lerp(color_type, color.yellow, 0.5),
    #     scale=(0.3, 0.3, 1.0),
    #     position=position - direction * 0.6,
    #     add_to_scene_entities=True
    # )

    projectile.direction = direction
    projectile.speed = speed * 1.5
    projectile.damage = damage
    projectile.creation_time = time.time()
    projectile.lifetime = 4.0  # Оптимальное время жизни
    projectile.glow = glow
    # projectile.tracer = tracer
    projectile.homing_strength = homing_strength * 2.5
    projectile.homing_active = True
    projectile.ground_bounce = True
    projectile.bounce_count = 0
    projectile.max_bounces = 2

    enemy_projectiles.append(projectile)
    return projectile


# ПОЛНОСТЬЮ ЗАМЕНЯЕМ СПЕЦИАЛЬНУЮ АТАКУ БОССА
def boss_special_attack(enemy):
    print("🌊 БОСС создает круговую волну!")
    create_shockwave(enemy.entity.position, enemy)


# УБИРАЕМ СТАРУЮ ФУНКЦИЮ С ШАРАМИ И ДЕЛАЕМ КРАСИВУЮ ВОЛНУ
def create_shockwave(center_position, enemy):
    """Создает красивую круговую волну-кольцо"""

    # Основные параметры волны
    wave_color = color.rgba(0.8, 0.1, 0.1, 0.8)  # Темно-красный
    glow_color = color.rgba(1.0, 0.3, 0.1, 0.4)  # Оранжевое свечение
    wave_height = 0.1
    expansion_time = 10
    max_radius = 40

    # 1. ОСНОВНОЕ КОЛЬЦО (внешний круг)
    outer_ring = Entity(
        model='circle',
        color=wave_color,
        scale=2.0,  # Начинаем с небольшого размера
        position=Vec3(center_position.x, wave_height, center_position.z),
        rotation=(90, 0, 0),
        add_to_scene_entities=True
    )

    # 2. СВЕЧЕНИЕ вокруг кольца
    glow_ring = Entity(
        model='circle',
        color=glow_color,
        scale=2.3,  # Немного больше основного кольца
        position=Vec3(center_position.x, wave_height - 0.01, center_position.z),
        rotation=(90, 0, 0),
        add_to_scene_entities=True
    )

    # 3. ЦЕНТРАЛЬНАЯ ЗОНА (безопасная зона - темный круг)
    safe_zone = Entity(
        model='circle',
        color=color.rgba(0.1, 0.1, 0.1, 0.6),  # Темный полупрозрачный
        scale=1.6,  # Меньше основного кольца
        position=Vec3(center_position.x, wave_height + 0.01, center_position.z),
        rotation=(90, 0, 0),
        add_to_scene_entities=True
    )

    # 4. ЭНЕРГЕТИЧЕСКИЕ ЧАСТИЦЫ по краю волны
    energy_particles = []
    for i in range(24):
        angle = (i / 24) * 360
        angle_rad = math.radians(angle)

        particle = Entity(
            model='sphere',
            color=color.rgba(1, 0.8, 0.2, 1),  # Золотистый
            scale=uniform(0.4, 0.7),
            position=center_position + Vec3(
                math.sin(angle_rad) * 1.0,
                wave_height + 0.2,
                math.cos(angle_rad) * 1.0
            ),
            add_to_scene_entities=True
        )
        energy_particles.append(particle)

    # АНИМАЦИЯ ВОЛНЫ
    def animate_wave(outer=outer_ring, glow=glow_ring, safe=safe_zone, particles=energy_particles, boss=enemy):
        start_time = time.time()
        wave_thickness = 0.8  # Толщина опасной зоны

        def update_wave():
            current_time = time.time()
            age = current_time - start_time

            if age < expansion_time and outer.enabled:
                progress = age / expansion_time

                # Расширяем все элементы
                current_scale = 2.0 + (max_radius * progress)
                outer.scale = current_scale
                glow.scale = current_scale + 0.3
                safe.scale = current_scale - wave_thickness

                # Эффекты прозрачности
                wave_alpha = 0.8 * (1 - progress * 0.7)
                glow_alpha = 0.4 * (1 - progress * 0.8)
                safe_alpha = 0.6 * (1 - progress * 0.5)

                outer.color = color.rgba(0.8, 0.1, 0.1, wave_alpha)
                glow.color = color.rgba(1.0, 0.3, 0.1, glow_alpha)
                safe.color = color.rgba(0.1, 0.1, 0.1, safe_alpha)

                # Анимация частиц
                for i, particle in enumerate(particles):
                    if particle.enabled:
                        angle = (i / len(particles)) * 360
                        angle_rad = math.radians(angle)
                        particle_radius = 1.0 + (max_radius * progress)

                        particle.position = center_position + Vec3(
                            math.sin(angle_rad) * particle_radius,
                            wave_height + 0.2 + math.sin(age * 8 + i) * 0.3,  # Плавное движение вверх-вниз
                            math.cos(angle_rad) * particle_radius
                        )

                        # Пульсация частиц
                        pulse = math.sin(age * 10 + i) * 0.3 + 0.7
                        particle.scale = particle.scale * pulse
                        particle.alpha = 1 - progress * 0.6

                # ПРОВЕРКА СТОЛКНОВЕНИЯ С ВОЛНОЙ
                check_wave_collision(center_position, current_scale, wave_thickness, boss, progress)

                invoke(update_wave, delay=1 / 60)
            else:
                # Удаляем все элементы волны
                destroy(outer)
                destroy(glow)
                destroy(safe)
                for particle in particles:
                    destroy(particle)

        update_wave()

    animate_wave()

    # ДОПОЛНИТЕЛЬНЫЙ ВИЗУАЛЬНЫЙ ЭФФЕКТ - ВСПЫШКА ПРИ СОЗДАНИИ
    create_wave_impact_effect(center_position)


# ФУНКЦИЯ ПРОВЕРКИ СТОЛКНОВЕНИЯ С ВОЛНОЙ
def check_wave_collision(center_position, current_scale, wave_thickness, enemy, progress):
    if progress < 0.2 or progress > 0.9:  # Волна неактивна в начале и конце
        return

    distance_to_center = (player.position - center_position).length()
    outer_radius = current_scale / 2
    inner_radius = (current_scale - wave_thickness) / 2

    # Игрок получает урон если находится в кольцевой зоне и на земле
    if inner_radius <= distance_to_center <= outer_radius:
        if player.position.y < 2.0:  # На земле или низко
            global player_health
            player_health -= enemy.damage
            print(
                f"🌊 Кольцевая волна поразила вас! Урон: {enemy.damage}. Здоровье: {player_health}/{player_max_health}")
            create_blood_effect_optimized(player.position + Vec3(0, 0.5, 0))


# ФУНКЦИЯ СОЗДАНИЯ ЭФФЕКТА УДАРА ВОЛНЫ
def create_wave_impact_effect(position):
    """Создает вспышку при появлении волны"""
    for i in range(12):
        impact_particle = Entity(
            model='cube',
            color=color.rgba(1, 0.6, 0.2, 1),
            scale=uniform(0.5, 1.0),
            position=position + Vec3(0, 0.5, 0),
            add_to_scene_entities=True
        )

        # Разлет частиц
        direction = Vec3(
            uniform(-1, 1),
            uniform(0, 1),
            uniform(-1, 1)
        ).normalized()

        def animate_impact(particle=impact_particle, dir=direction):
            start_time = time.time()
            lifetime = 1.0

            def update_impact():
                current_time = time.time()
                age = current_time - start_time

                if age < lifetime and particle.enabled:
                    particle.position += dir * 8 * time.dt
                    particle.alpha = 1 - (age / lifetime)
                    particle.scale = particle.scale * (1 - age / lifetime * 0.5)
                    invoke(update_impact, delay=1 / 60)
                else:
                    destroy(particle)

            update_impact()

        animate_impact()


# ИСПРАВЛЯЕМ ФУНКЦИЮ boss_charge_attack
def boss_charge_attack(enemy):
    print("🚀 БОСС готовится к атаке с разбегом!")

    # Босс готовится к атаке (меняет цвет)
    enemy.entity.color = color.white

    # Через 1 секунду бросок
    def charge():
        # ПРОВЕРЯЕМ ЧТО ВРАГ ЕЩЕ СУЩЕСТВУЕТ
        if enemy not in enemies or not enemy.entity or not enemy.entity.enabled:
            return

        direction_to_player = (player.position - enemy.entity.position).normalized()
        enemy.entity.color = color.red

        # ОДИНОЧНЫЙ быстрый бросок к игроку (фиксированная дистанция)
        charge_distance = 5.0
        enemy.entity.position += direction_to_player * charge_distance

        # ПРОВЕРЯЕМ ЧТО ВРАГ ВСЕ ЕЩЕ СУЩЕСТВУЕТ ПОСЛЕ ДВИЖЕНИЯ
        if enemy not in enemies or not enemy.entity or not enemy.entity.enabled:
            return

        # Если попал в игрока
        distance = (enemy.entity.position - player.position).length()
        if distance <= enemy.attack_range * 2:
            global player_health
            player_health -= enemy.damage * 2
            print(f"💢 БОСС атаковал с разбега! Урон: {enemy.damage * 2}. Здоровье: {player_health}/{player_max_health}")

    invoke(charge, delay=1.0)


def check_enemy_stuck(enemy):
    current_pos = Vec3(enemy.entity.position)
    distance_moved = (current_pos - enemy.last_position).length()

    if distance_moved < 0.1:
        enemy.stuck_timer += time.dt
    else:
        enemy.stuck_timer = 0

    if enemy.stuck_timer >= enemy.stuck_threshold:
        escape_direction = Vec3(uniform(-1, 1), 0, uniform(-1, 1)).normalized()
        enemy.entity.position += escape_direction * 1.0 * time.dt
        enemy.stuck_timer = 0

    enemy.last_position = current_pos


def update_enemy_visuals(enemy):
    if enemy.is_chasing:
        if enemy.type == "normal":
            enemy.entity.color = color.rgba(1, 0, 0, 1)  # Красный
        elif enemy.type == "medium":
            enemy.entity.color = color.rgba(1, 0.5, 0, 1)  # Оранжевый
        else:
            enemy.entity.color = color.rgba(1, 0, 0, 1)  # Красный
    else:
        if enemy.type == "normal":
            enemy.entity.color = color.rgba(0, 0, 1, 1)  # Синий
        elif enemy.type == "medium":
            enemy.entity.color = color.rgba(1, 0.65, 0, 1)  # Оранжевый
        else:
            enemy.entity.color = color.rgba(0.5, 0, 0, 1)  # Темно-красный


# Функция создания NPC на карте


# Функция для обновления эффектов крови
def update_blood_effects():
    """Оптимизированная версия обновления эффектов"""
    safe_update_effects()  # Обновляет все эффекты (кровь + трассеры + вспышки)


# УЛУЧШЕННЫЙ ЭФФЕКТ ДУЛЬНОГО ПЛАМЕНИ
def create_muzzle_flash(muzzle_offset=None):
    data = weapon_data[current_weapon]

    # Если позиция не указана, используем стандартную
    if muzzle_offset is None:
        muzzle_offset = data.get("muzzle_offset", Vec3(0, 0, 0))

    particles = []

    # Создаем несколько частиц для эффекта взрыва
    for i in range(8):
        particle_size = uniform(0.01, 0.04)

        particle = Entity(
            model='cube',
            color=lerp(color.yellow, color.orange, random.random()),
            scale=(particle_size, particle_size, particle_size),
            parent=weapon,
            position=muzzle_offset,
            add_to_scene_entities=False
        )

        # Случайное направление для частиц
        particle_direction = Vec3(
            uniform(-0.2, 0.2),
            uniform(-0.1, 0.2),
            uniform(0.3, 0.8)
        )

        particles.append((particle, particle_direction, particle_size))

    muzzle_flash_entities.append((particles, time.time()))
    return particles


# ОБНОВЛЕННАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ ТРАССЕРОВ

def create_weapon(weapon_type):
    data = weapon_data[weapon_type]

    weapon_entity = Entity(
        model=data["model"],
        parent=camera,
        position=data["position"],
        rotation=data["rotation"],
        scale=data["scale"],
        shader=data["shader"]
    )

    return weapon_entity


# ФУНКЦИЯ СМЕНЫ ОРУЖИЯ
# ОБНОВЛЯЕМ ФУНКЦИЮ ПЕРЕКЛЮЧЕНИЯ ОРУЖИЯ
def switch_weapon(weapon_type):
    global current_weapon, weapon, is_firing_auto, auto_fire_delay

    # ПРОВЕРЯЕМ РАЗБЛОКИРОВАНО ЛИ ОРУЖИЕ
    if weapon_type not in unlocked_weapons:
        print(f"❌ Оружие {weapon_type} еще не разблокировано!")
        return

    # СБРАСЫВАЕМ АВТОМАТИЧЕСКУЮ СТРЕЛЬБУ ПРИ ПЕРЕКЛЮЧЕНИИ
    is_firing_auto = False

    # Скрываем текущее оружие
    if weapon and weapon.enabled:
        weapon.enabled = False

    # Создаем новое оружие если его еще нет
    if weapon_type not in weapons:
        weapons[weapon_type] = create_weapon(weapon_type)

    # Активируем выбранное оружие
    weapon = weapons[weapon_type]
    weapon.enabled = True

    data = weapon_data[weapon_type]
    auto_fire_delay = data["fire_rate"]

    # ⚠️ ВАЖНО: НЕ ПЕРЕЗАПИСЫВАЕМ ГЛОБАЛЬНЫЕ weapon_base_position и weapon_base_rotation
    # Вместо этого используем данные из weapon_data для текущего оружия

    # Сбрасываем текущие позиции и вращения
    global current_weapon_position, current_weapon_rotation
    global target_weapon_position, target_weapon_rotation

    # Берем позиции ИЗ weapon_data для текущего оружия
    current_weapon_position = data["position"]
    current_weapon_rotation = data["rotation"]
    target_weapon_position = data["position"]
    target_weapon_rotation = data["rotation"]

    current_weapon = weapon_type
    update_weapon_parameters()
    print(f"🔫 Сменил оружие на: {weapon_type}")


# ФУНКЦИЯ ПЕРЕЗАГРУЗКИ ПАРАМЕТРОВ СТРЕЛЬБЫ ДЛЯ ТЕКУЩЕГО ОРУЖИЯ
def update_weapon_parameters():
    global auto_fire_delay, weapon_shoot_recoil, shoot_camera_shake_intensity

    data = weapon_data[current_weapon]
    auto_fire_delay = data["fire_rate"]
    weapon_shoot_recoil = data["recoil"]
    shoot_camera_shake_intensity = data["camera_shake"]


# ИНИЦИАЛИЗАЦИЯ ОРУЖИЯ ПРИ ЗАПУСКЕ
def init_weapons():
    global weapon, weapons, current_weapon

    # Создаем все виды оружия, но скрываем их
    for weapon_type in weapon_data.keys():
        weapons[weapon_type] = create_weapon(weapon_type)
        weapons[weapon_type].enabled = False

    # ⚠️ ВАЖНО: Активируем пистолет как стартовое оружие
    weapon = weapons["pistol"]
    weapon.enabled = True
    current_weapon = "pistol"

    # Устанавливаем правильные позиции для пистолета
    global current_weapon_position, current_weapon_rotation
    global target_weapon_position, target_weapon_rotation

    data = weapon_data["pistol"]
    current_weapon_position = data["position"]
    current_weapon_rotation = data["rotation"]
    target_weapon_position = data["position"]
    target_weapon_rotation = data["rotation"]

    update_weapon_parameters()


def create_bullet_tracer(muzzle_offset=None):
    data = weapon_data[current_weapon]

    # Если позиция не указана, используем стандартную
    if muzzle_offset is None:
        muzzle_offset = data.get("muzzle_offset", Vec3(0, 0, 0))

    # Мировая позиция дула с учетом текущего оружия
    muzzle_world_pos = weapon.world_position + weapon.right * muzzle_offset[0] + weapon.up * \
                       muzzle_offset[1] + weapon.forward * muzzle_offset[2]

    direction = camera.forward

    tracer = Entity(
        model='cube',
        color=color.yellow,
        scale=(0.06, 0.06, 0.4),
        position=muzzle_world_pos,
        add_to_scene_entities=True,
        eternal=False, shader=Shader(language=Shader.GLSL, fragment='''
            #version 140
            uniform sampler2D p3d_Texture0;
            uniform vec4 p3d_Color;
            in vec2 uv;
            out vec4 frag_color;

            void main() {
                vec4 tex_color = texture(p3d_Texture0, uv) * p3d_Color;
                // Делаем трассер ярким и с свечением
                float glow = 1.5;
                tex_color.rgb *= glow;

                // Градиент от ярко-желтого к оранжевому
                float gradient = uv.y;
                vec3 start_color = vec3(1.0, 1.0, 0.2); // Ярко-желтый
                vec3 end_color = vec3(1.0, 0.5, 0.0);   // Оранжевый
                tex_color.rgb = mix(start_color, end_color, gradient) * tex_color.a;

                frag_color = tex_color;
            }
        ''')
    )

    # Сохраняем начальную позицию и направление
    tracer.start_position = Vec3(muzzle_world_pos)
    tracer.direction = Vec3(direction)
    tracer.speed = data["bullet_speed"]

    bullet_tracers.append((tracer, time.time()))
    return tracer


# Функция для обновления эффектов
def update_shot_effects():
    if not muzzle_flash_entities and not bullet_tracers:
        return
    current_time = time.time()

    for flash_idx in range(len(muzzle_flash_entities) - 1, -1, -1):  # меняем i на flash_idx
        particles, spawn_time = muzzle_flash_entities[flash_idx]
        age = current_time - spawn_time

        if age < muzzle_flash_duration:
            progress = age / muzzle_flash_duration

            for particle, direction, original_size in particles:
                particle.position += direction * time.dt * 5
                particle.alpha = 1 - progress
                current_size = original_size * (1 - progress)
                particle.scale = (current_size, current_size, current_size)

                if progress < 0.3:
                    particle.color = lerp(color.yellow, color.orange, progress * 3)
                else:
                    particle.color = lerp(color.orange, color.red, (progress - 0.3) * 1.5)

        else:
            for particle, direction, original_size in particles:
                destroy(particle)
            muzzle_flash_entities.pop(flash_idx)

    for tracer_idx in range(len(bullet_tracers) - 1, -1, -1):  # меняем i на tracer_idx
        tracer_data = bullet_tracers[tracer_idx]

        if not tracer_data or len(tracer_data) != 2:
            bullet_tracers.pop(tracer_idx)
            continue

        tracer, spawn_time = tracer_data

        if not tracer or tracer.enabled == False:
            bullet_tracers.pop(tracer_idx)
            continue

        age = current_time - spawn_time

        if age < bullet_lifetime:
            tracer.position += tracer.direction * time.dt * tracer.speed
            progress = age / bullet_lifetime
            tracer.alpha = 1 - progress * 0.8
            tracer.color = lerp(color.yellow, color.orange, progress)
            tracer.scale_z = lerp(0.2, 0.05, progress)

            if hasattr(tracer, 'direction'):
                tracer.look_at(tracer.position + tracer.direction)

        else:
            destroy(tracer)
            bullet_tracers.pop(tracer_idx)


def check_sprint_collisions():
    # Проверяем столкновения с основными объектами
    collision_objects = []

    # Добавляем блоки платформы

    # Добавляем врагов (чтобы не проходить сквозь них)
    for enemy in enemies:
        if enemy and enemy.entity and enemy.entity.enabled:
            collision_objects.append(enemy.entity)

    for obj in collision_objects:
        if obj and hasattr(obj, 'collider') and obj.collider:
            # Простая проверка расстояния
            distance = (player.position - obj.position).length()
            collision_distance = 2.0  # Дистанция столкновения

            if distance < collision_distance:
                # Выталкиваем игрока от объекта
                direction_away = (player.position - obj.position).normalized()
                push_distance = collision_distance - distance + 0.1
                player.position += direction_away * push_distance


# ОБНОВЛЯЕМ ФУНКЦИЮ perform_shot ДЛЯ DUAL UZI
def perform_shot():
    global is_shooting, shoot_animation_time, grenade_effect

    # ПРОВЕРЯЕМ ПАТРОНЫ ПЕРЕД ВЫСТРЕЛОМ
    if not use_ammo():
        return

    is_shooting = True
    shoot_animation_time = 0

    data = weapon_data[current_weapon]

    # ЕСЛИ ЭТО DUAL UZI - ДВОЙНОЙ ВЫСТРЕЛ
    if current_weapon == "dual_uzi" and data.get("dual_shot", False):
        create_muzzle_flash(data["muzzle_offset_left"])
        create_bullet_tracer(data["muzzle_offset_left"])

        def second_shot():
            create_muzzle_flash(data["muzzle_offset_right"])
            create_bullet_tracer(data["muzzle_offset_right"])

        invoke(second_shot, delay=0.02)

        ammo_type = weapon_data[current_weapon]["ammo_type"]
        ammo_info = ammo_data[ammo_type]
        if ammo_info['current_ammo'] > 0:
            ammo_info['current_ammo'] -= 1


    # ЕСЛИ ЭТО ГРАНАТОМЕТ - СОЗДАЕМ ВЗРЫВНОЙ СНАРЯД
    elif current_weapon == "grenade_launcher" and data.get("is_explosive", False):
        create_grenade_shot()

    else:
        # Обычный одиночный выстрел для других оружий
        create_muzzle_flash()
        create_bullet_tracer()

    # ЗВУК ВЫСТРЕЛА
    try:
        if current_weapon == "dual_uzi":
            weapon_sound = Audio('uzi_shoot.mp3', loop=False, autoplay=False)
        elif current_weapon == "grenade_launcher":
            weapon_sound = Audio('grenade.ogg', loop=False, autoplay=False)
        elif current_weapon == "assault_rifle":
            weapon_sound = Audio('shoot.ogg', loop=False, autoplay=False)
        else:
            weapon_sound = Audio('shoot2.ogg', loop=False, autoplay=False)

        pitch_range = data["sound_pitch_range"]
        weapon_sound.pitch = random.uniform(pitch_range[0], pitch_range[1])
        weapon_sound.volume = data.get("sound_volume", 0.8)
        weapon_sound.play()
        print(f"🔫 Звук для {current_weapon}")

    except Exception as e:
        print(f"❌ Ошибка загрузки звука: {e}")
        shoot_sound.pitch = random.uniform(data["sound_pitch_range"][0], data["sound_pitch_range"][1])
        shoot_sound.play()

    # ОТДАЧА
    global shoot_camera_shake_intensity, shoot_camera_roll_intensity
    shoot_camera_shake_intensity = data["camera_shake"] * uniform(0.8, 1.2)
    shoot_camera_roll_intensity = 3.0 * uniform(0.9, 1.1)


def create_grenade_shot():
    global grenade_effect
    data = weapon_data[current_weapon]

    # Мировая позиция дула
    muzzle_world_pos = weapon.world_position + weapon.right * data["muzzle_offset"][0] + weapon.up * \
                       data["muzzle_offset"][1] + weapon.forward * data["muzzle_offset"][2]

    direction = camera.forward

    # Создаем гранату (большая сфера)
    grenade = Entity(
        model='sphere',
        color=color.green,
        scale=0.5,
        position=muzzle_world_pos,
        add_to_scene_entities=True
    )

    # Эффект свечения гранаты
    glow = Entity(
        model='sphere',
        color=color.rgba(0, 1, 0, 0.3),
        scale=0.7,
        position=muzzle_world_pos,
        add_to_scene_entities=True
    )

    # Траектория гранаты
    tracer = Entity(
        model='cube',
        color=color.green,
        scale=(0.2, 0.2, 0.8),
        position=muzzle_world_pos - direction * 0.5,
        add_to_scene_entities=True
    )

    grenade.direction = direction
    grenade.speed = data["bullet_speed"]
    grenade.creation_time = time.time()
    grenade.lifetime = 5.0  # Время до автоматического взрыва
    grenade.glow = glow
    grenade.tracer = tracer
    grenade.explosion_radius = data["explosion_radius"]
    grenade.explosion_damage = data["explosion_damage"]
    grenade.gravity = -9.8  # Гравитация для гранаты

    explosive_projectiles.append(grenade)

    # Эффект выстрела для гранатомета
    create_muzzle_flash()
    grenade_effect = 1.0


def update_explosive_projectiles():
    current_time = time.time()

    for proj_idx in range(len(explosive_projectiles) - 1, -1, -1):
        grenade = explosive_projectiles[proj_idx]

        if not grenade or not grenade.enabled:
            if proj_idx < len(explosive_projectiles):
                explosive_projectiles.pop(proj_idx)
            continue

        # Движение гранаты с гравитацией
        grenade.position += grenade.direction * time.dt * grenade.speed
        grenade.position.y += grenade.gravity * time.dt  # Применяем гравитацию

        # Обновляем эффекты
        if hasattr(grenade, 'glow') and grenade.glow and grenade.glow.enabled:
            grenade.glow.position = grenade.position

        if hasattr(grenade, 'tracer') and grenade.tracer and grenade.tracer.enabled:
            grenade.tracer.position = grenade.position - grenade.direction * 0.8
            grenade.tracer.look_at(grenade.position)

        # Проверка времени жизни или столкновения
        age = current_time - grenade.creation_time
        hit_ground = grenade.position.y <= 0.5  # Столкновение с землей

        if age >= grenade.lifetime or hit_ground:
            # ВЗРЫВ!
            create_explosion(grenade.position, grenade.explosion_radius, grenade.explosion_damage)

            # Уничтожаем гранату и эффекты
            destroy(grenade)
            if hasattr(grenade, 'glow') and grenade.glow:
                destroy(grenade.glow)
            if hasattr(grenade, 'tracer') and grenade.tracer:
                destroy(grenade.tracer)

            if proj_idx < len(explosive_projectiles):
                explosive_projectiles.pop(proj_idx)


def create_explosion(position, radius, damage):
    print(f"💥 ВЗРЫВ! Радиус: {radius}, Урон: {damage}")

    # ЗАПУСКАЕМ ТРЯСКУ КАМЕРЫ
    start_explosion_shake()

    # Визуальный эффект взрыва
    explosion_effect = Entity(
        model='sphere',
        color=color.orange,
        scale=0.1,
        position=position,
        add_to_scene_entities=True
    )

    # Анимация расширения взрыва
    def animate_explosion():
        explosion_effect.animate_scale(radius * 2, duration=0.3, curve=curve.out_quad)
        explosion_effect.animate_color(color.red, duration=0.2)

        # Исчезновение
        def fade_out():
            explosion_effect.animate_scale(0, duration=0.2)
            explosion_effect.animate_color(color.rgba(1, 0, 0, 0), duration=0.2)
            invoke(lambda: destroy(explosion_effect), delay=0.5)

        invoke(fade_out, delay=0.3)

    animate_explosion()

    # Звук взрыва
    try:
        explosion_sound = Audio('explosion.ogg', loop=False, autoplay=False)
        explosion_sound.volume = 0.8
        explosion_sound.play()
    except:
        print("💥 Звук взрыва не найден")

    # ПРОВЕРКА ПОПАДАНИЯ ПО ВРАГАМ В РАДИУСЕ ВЗРЫВА
    for enemy_idx in range(len(enemies) - 1, -1, -1):
        enemy = enemies[enemy_idx]

        if not enemy or not enemy.entity or not enemy.entity.enabled:
            continue

        distance_to_explosion = (enemy.entity.position - position).length()

        if distance_to_explosion <= radius:
            print(f"💥 Враг попал в радиус взрыва! Дистанция: {distance_to_explosion}")

            # УБИВАЕМ ВРАГА МГНОВЕННО
            create_blood_effect_optimized(enemy.entity.position + Vec3(0, 1, 0))
            on_enemy_killed()

            # Уничтожаем врага
            destroy(enemy.entity)
            if enemy in enemies:
                enemies.remove(enemy)


def start_explosion_shake(intensity_factor=1.0):
    global is_explosion_shaking, explosion_shake_timer, explosion_shake_intensity
    is_explosion_shaking = True
    explosion_shake_timer = 0

    # Умножаем интенсивность на коэффициент расстояния
    explosion_shake_intensity = 0.3 * intensity_factor

    print(f"📳 Тряска от взрыва! Интенсивность: {intensity_factor:.2f}")


# ФУНКЦИЯ ОБНОВЛЕНИЯ ТРЯСКИ ОТ ВЗРЫВА
def update_explosion_shake():
    global is_explosion_shaking, explosion_shake_timer, current_explosion_shake, current_explosion_tilt

    if is_explosion_shaking:
        explosion_shake_timer += time.dt

        if explosion_shake_timer < explosion_shake_duration:
            # Вычисляем прогресс тряски (от 1 до 0)
            progress = 1 - (explosion_shake_timer / explosion_shake_duration)

            # Интенсивность тряски уменьшается со временем
            current_intensity = explosion_shake_intensity * progress

            # Случайные смещения для тряски (высокочастотные для взрыва)
            shake_x = math.sin(time.time() * 50) * current_intensity * 0.5
            shake_y = math.cos(time.time() * 45) * current_intensity * 0.7
            shake_z = math.sin(time.time() * 55) * current_intensity * 0.3

            # Наклон камеры от взрыва
            tilt_x = math.sin(time.time() * 30) * current_intensity * 2
            tilt_z = math.cos(time.time() * 25) * current_intensity * 3

            # Сохраняем текущую тряску для использования в основном update
            current_explosion_shake = (shake_x, shake_y, shake_z)
            current_explosion_tilt = (tilt_x, 0, tilt_z)

        else:
            # Завершаем тряску
            is_explosion_shaking = False
            explosion_shake_timer = 0
            current_explosion_shake = (0, 0, 0)
            current_explosion_tilt = (0, 0, 0)


# ОБНОВЛЯЕМ ФУНКЦИЮ handle_shooting
def handle_shooting():
    global is_shooting, last_fire_time, is_firing_auto

    # Если идет анимация выстрела или перезарядки - выходим
    if is_shooting or is_reloading_anim:
        return

    # Проверяем патроны
    ammo_type = weapon_data[current_weapon]["ammo_type"]
    ammo_info = ammo_data[ammo_type]

    if ammo_info['current_ammo'] <= 0:
        if is_firing_auto:
            is_firing_auto = False
            print("💥 Нет патронов!")
        return

    # Только для автоматического оружия
    data = weapon_data[current_weapon]
    if data["auto_fire"] and is_firing_auto:
        current_time = time.time()
        if current_time - last_fire_time >= auto_fire_delay:
            perform_shot()
            last_fire_time = current_time


# ФУНКЦИЯ СОЗДАНИЯ HUD ДЛЯ ОРУЖИЯ (УВЕЛИЧЕННАЯ ВЕРСИЯ)
def create_weapon_hud():
    global weapon_hud, ammo_text, weapon_icons

    # ОСНОВНОЙ КОНТЕЙНЕР HUD ОРУЖИЯ (больше и ближе к центру)
    weapon_hud = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0.1, 0.1, 0.1, 0.8),  # Более темный и непрозрачный
        scale=(0.3, 0.2),  # УВЕЛИЧИЛИ РАЗМЕР
        position=(0.7, -0.36, 0)  # СДВИНУЛИ БЛИЖЕ К ЦЕНТРУ
    )

    # ТЕКСТ ПАТРОНОВ (крупнее и жирнее)
    ammo_text = Text(
        parent=camera.ui,  # Родитель - camera.ui чтобы был поверх всего
        text="30/30",
        position=(0.71, -0.15, 0),  # ВЫШЕ И ПРАВЕЕ
        scale=2,  # УВЕЛИЧИЛИ РАЗМЕР ТЕКСТА
        color=color.white,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.5),
        font='custom2.ttf'
    )

    # ИКОНКИ ОРУЖИЯ (1, 2, 3) - УВЕЛИЧИЛИ
    weapon_slots = [
        {"key": "1", "weapon": "assault_rifle", "pos": (0.67, -0.3, -0.9), "color": color.dark_gray, "name": "АВТОМАТ"},
        {"key": "2", "weapon": "pistol", "pos": (0.67, -0.35, -0.9), "color": color.dark_gray, "name": "ПИСТОЛЕТ"},
        {"key": "3", "weapon": "dual_uzi", "pos": (0.67, -0.4, -0.9), "color": color.dark_gray, "name": "DUAL UZI"}
    ]

    weapon_icons = {}

    for slot in weapon_slots:
        # Фон слота (увеличили)
        slot_bg = Entity(
            parent=camera.ui,
            model='quad',
            color=slot["color"],
            scale=(0.04, 0.04),  # УВЕЛИЧИЛИ ИКОНКИ
            position=slot["pos"],
            z=-0.01
        )

        # Текст номера слота (увеличили)
        slot_text = Text(
            parent=camera.ui,
            text=slot["key"],
            position=(slot["pos"][0], slot["pos"][1], -0.5),  # ТА ЖЕ ПОЗИЦИЯ ЧТО И У ФОНА
            scale=1.5,
            color=color.white,
            origin=(0, 0),
            font='custom2.ttf'
        )

        # Название оружия под иконкой
        # weapon_name = Text(
        #     parent=weapon_hud,
        #     text=slot["name"],
        #     position=(slot["pos"][0], slot["pos"][1] - 0.15, -0.02),
        #     scale=1.2,  # УВЕЛИЧИЛИ НАЗВАНИЕ
        #     color=color.white
        # )

        weapon_icons[slot["weapon"]] = {
            "bg": slot_bg,
            "text": slot_text,
            "key": slot["key"]
        }

    # БОЛЬШАЯ ИКОНКА ТЕКУЩЕГО ОРУЖИЯ (справа)
    weapon_icon = Entity(
        parent=camera.ui,
        model='quad',
        color=color.white,
        scale=(0.2, 0.2),  # УВЕЛИЧИЛИ ИКОНКУ
        position=(0.8, -0.36),
        z=-0.01,

    )

    # Попробуем загрузить текстуры для иконок
    try:
        weapon_icon.texture = 'rifle_icon.png'
    except:
        print("⚠️ Текстура иконки автомата не найдена")

    weapon_icons["current_weapon"] = weapon_icon

    # КРУПНЫЙ ТЕКСТ НАЗВАНИЯ ОРУЖИЯ
    # weapon_name_text = Text(
    #     parent=camera.ui,
    #     text="АВТОМАТ",
    #     position=(0, 0, 0),  # ПОД ПАТРОНАМИ
    #     scale=2.2,  # УВЕЛИЧИЛИ НАЗВАНИЕ
    #     color=color.orange,
    #     background=True,
    #     background_color=color.rgba(0, 0, 0, 0.5)
    # )

    # weapon_icons["weapon_name"] = weapon_name_text

    # ТЕКСТ ПЕРЕЗАРЯДКИ (будет появляться при перезарядке)
    reload_text = Text(
        parent=camera.ui,
        text="",
        position=(0.7, 0.1, 0),
        scale=1.8,
        color=color.yellow,
        background_color=color.rgba(0, 0, 0, 0.7),
        font='custom2.ttf'
    )

    weapon_icons["reload_text"] = reload_text


# ФУНКЦИЯ ОБНОВЛЕНИЯ HUD ОРУЖИЯ
def update_weapon_hud():
    global ammo_text, weapon_icons, current_weapon, is_reloading

    if not weapon_hud or not ammo_text:
        return

    # ИСПОЛЬЗУЕМ ПРАВИЛЬНЫЙ ТИП ПАТРОНОВ ИЗ weapon_data
    ammo_type = weapon_data[current_weapon]["ammo_type"]
    ammo_info = ammo_data[ammo_type]

    # ОБНОВЛЯЕМ ПАТРОНЫ
    ammo_text.text = f"{ammo_info['current_ammo']} / {ammo_info['max_ammo']}"

    # ОБНОВЛЯЕМ ЗАПАСНЫЕ ПАТРОНЫ
    reserve_text = f"Запас: {ammo_info['reserve_ammo']}"
    if not hasattr(update_weapon_hud, 'reserve_text_created'):
        update_weapon_hud.reserve_text = Text(
            parent=camera.ui,
            text=reserve_text,
            position=(0.7, 0, 0),
            scale=1.5,
            color=color.light_gray,
            background=True,
            background_color=color.rgba(0, 0, 0, 0.5),
            font='custom2.ttf'
        )
        update_weapon_hud.reserve_text_created = True
    else:
        update_weapon_hud.reserve_text.text = reserve_text

    # ПОДСВЕЧИВАЕМ ТЕКУЩИЙ СЛОТ
    for weapon_type, icon_data in weapon_icons.items():
        if weapon_type in ["assault_rifle", "pistol", "dual_uzi"]:
            if weapon_type == current_weapon:
                # Текущее оружие - серый фон
                icon_data["bg"].color = color.gray
            else:
                # Не выбранное оружие - темно-серый фон
                icon_data["bg"].color = color.dark_gray

            # ЦИФРЫ ВСЕГДА БЕЛЫЕ (не меняем цвет текста)
            icon_data["text"].color = color.white
            # icon_data["name"].color = color.white

    # ОБНОВЛЯЕМ БОЛЬШОЕ НАЗВАНИЕ ОРУЖИЯ
    # weapon_names = {
    #     "assault_rifle": "АВТОМАТ",
    #     "pistol": "ПИСТОЛЕТ"
    # }
    # weapon_icons["weapon_name"].text = weapon_names.get(current_weapon, "ОРУЖИЕ")

    # ЦВЕТ НАЗВАНИЯ В ЗАВИСИМОСТИ ОТ ОРУЖИЯ
    # if current_weapon == "assault_rifle":
    #     weapon_icons["weapon_name"].color = color.orange
    # else:
    #     weapon_icons["weapon_name"].color = color.cyan

    # МЕНЯЕМ ЦВЕТ ПАТРОНОВ
    if ammo_info['current_ammo'] == 0:
        ammo_text.color = color.red
        update_weapon_hud.reserve_text.color = color.red
    elif ammo_info['current_ammo'] <= ammo_info['max_ammo'] * 0.3:
        ammo_text.color = color.orange
        update_weapon_hud.reserve_text.color = color.orange
    else:
        ammo_text.color = color.white
        update_weapon_hud.reserve_text.color = color.light_gray

    # ОБНОВЛЯЕМ ИКОНКУ ТЕКУЩЕГО ОРУЖИЯ
    try:
        if current_weapon == "assault_rifle":
            weapon_icons["current_weapon"].texture = 'rifle_icon.png'
        elif current_weapon == "pistol":
            weapon_icons["current_weapon"].texture = 'pistol_icon.png'
        elif current_weapon == "dual_uzi":
            weapon_icons["current_weapon"].texture = 'dual_uzi_icon.jpg'  # Нужно создать иконку
        weapon_icons["current_weapon"].color = color.white
    except:
        # Если текстур нет, используем цветные квадраты
        if current_weapon == "assault_rifle":
            weapon_icons["current_weapon"].color = color.orange
        elif current_weapon == "pistol":
            weapon_icons["current_weapon"].color = color.cyan
        elif current_weapon == "dual_uzi":
            weapon_icons["current_weapon"].color = color.red  # Фиолетовый для UZI

    # ПОКАЗЫВАЕМ ПЕРЕЗАРЯДКУ
    if is_reloading_anim:
        weapon_icons["reload_text"].text = "ПЕРЕЗАРЯДКА..."
        weapon_icons["reload_text"].color = color.yellow
        # Мигающий эффект
        pulse = math.sin(time.time() * 2) * 0.08 + 0.1
        weapon_icons["reload_text"].scale = 3.8 * pulse
    else:
        weapon_icons["reload_text"].text = ""


# ФУНКЦИЯ ИСПОЛЬЗОВАНИЯ ПАТРОНОВ ПРИ СТРЕЛЬБЕ
def use_ammo():
    global current_weapon

    ammo_type = weapon_data[current_weapon]["ammo_type"]
    ammo_info = ammo_data[ammo_type]

    # ДЛЯ DUAL UZI НУЖНО МИНИМУМ 2 ПАТРОНА ДЛЯ ВЫСТРЕЛА
    if current_weapon == "dual_uzi":
        if ammo_info['current_ammo'] >= 2:  # Проверяем что есть минимум 2 патрона
            ammo_info['current_ammo'] -= 1  # Первый патрон тратится здесь
            # Второй патрон будет потрачен в perform_shot()
            return True
        else:
            # Не хватает патронов для выстрела из двух стволов
            try:
                empty_sound = Audio(('empty_click.ogg'), loop=False, autoplay=False)
                empty_sound.play()
            except:
                print("💥 Не хватает патронов для Dual UZI!")
            return False
    else:
        # Для других оружий - 1 патрон за выстрел
        if ammo_info['current_ammo'] > 0:
            ammo_info['current_ammo'] -= 1
            return True
        else:
            try:
                empty_sound = Audio('empty_click.ogg', loop=False, autoplay=False)
                empty_sound.play()
            except:
                print("💥 Щелчек пустого оружия")
            return False


# ФУНКЦИЯ ПЕРЕЗАРЯДКИ
# ИСПРАВЛЯЕМ ФУНКЦИЮ reload_weapon
# ИСПРАВЛЯЕМ СИСТЕМУ ПЕРЕЗАРЯДКИ
def reload_weapon():
    global is_reloading_anim, reload_anim_time, current_weapon, reload_strength
    reload_strength = 1

    if is_reloading_anim:
        return

    ammo_type = weapon_data[current_weapon]["ammo_type"]
    ammo_info = ammo_data[ammo_type]
    weapon_info = weapon_data[current_weapon]

    # Проверяем, нужна ли перезарядка
    if ammo_info['current_ammo'] >= ammo_info['max_ammo'] or ammo_info['reserve_ammo'] <= 0:
        print("❌ Перезарядка не нужна")
        return

    # Начинаем анимацию перезарядки
    is_reloading_anim = True
    reload_anim_time = 0

    print(f"🔃 Начата перезарядка {current_weapon}...")
    print(f"📊 До перезарядки: {ammo_info['current_ammo']}/{ammo_info['max_ammo']}, Запас: {ammo_info['reserve_ammo']}")

    # Звук перезарядки
    try:
        reload_sound = Audio('reload.ogg', loop=False, autoplay=False)
        reload_sound.play()
    except:
        print("🔃 Звук перезарядки не найден")


def update_reload_animation():
    global is_reloading_anim, reload_anim_time, current_weapon_position

    if is_reloading_anim:
        reload_anim_time += time.dt

        if reload_anim_time < reload_anim_duration:
            # ФАЗА 1: ОПУСКАНИЕ ОРУЖИЯ ВНИЗ
            progress = reload_anim_time / reload_anim_duration
            down_offset = reload_weapon_offset * progress

            weapon.position = (
                current_weapon_position[0],
                current_weapon_position[1] - down_offset,
                current_weapon_position[2]
            )

        elif reload_anim_time < reload_anim_duration * 2:
            # ФАЗА 2: ОРУЖИЕ ОСТАЕТСЯ ВНИЗУ
            weapon.position = (
                current_weapon_position[0],
                current_weapon_position[1] - reload_weapon_offset,
                current_weapon_position[2]
            )

        elif reload_anim_time < reload_anim_duration * 3:
            # ФАЗА 3: ПОДНЯТИЕ ОРУЖИЯ ОБРАТНО
            progress = (reload_anim_time - reload_anim_duration * 2) / reload_anim_duration
            up_offset = reload_weapon_offset * (1 - progress)

            weapon.position = (
                current_weapon_position[0],
                current_weapon_position[1] - up_offset,
                current_weapon_position[2]
            )

        else:
            # ФАЗА 4: ЗАВЕРШЕНИЕ АНИМАЦИИ И ДОБАВЛЕНИЕ ПАТРОНОВ
            is_reloading_anim = False
            reload_anim_time = 0
            weapon.position = current_weapon_position

            # ТЕПЕРЬ ДОБАВЛЯЕМ ПАТРОНЫ ПОСЛЕ ЗАВЕРШЕНИЯ АНИМАЦИИ
            finish_reload()


# ФУНКЦИЯ ЗАВЕРШЕНИЯ ПЕРЕЗАРЯДКИ
def finish_reload():
    global current_weapon

    ammo_type = weapon_data[current_weapon]["ammo_type"]
    ammo_info = ammo_data[ammo_type]

    # Вычисляем сколько патронов нужно дозарядить
    ammo_needed = ammo_info['max_ammo'] - ammo_info['current_ammo']
    ammo_to_add = min(ammo_needed, ammo_info['reserve_ammo'])

    if ammo_to_add > 0:
        # Сохраняем старые значения для отладки
        old_current = ammo_info['current_ammo']
        old_reserve = ammo_info['reserve_ammo']

        # Добавляем патроны
        ammo_info['current_ammo'] += ammo_to_add
        ammo_info['reserve_ammo'] -= ammo_to_add

        print(f"✅ Перезарядка завершена!")
        print(f"📊 {old_current} → {ammo_info['current_ammo']}/{ammo_info['max_ammo']}")
        print(f"📦 Запас: {old_reserve} → {ammo_info['reserve_ammo']}")
        print(f"🔫 Добавлено патронов: {ammo_to_add}")
    else:
        print("❌ Не удалось добавить патроны - проверь настройки")


# ФУНКЦИЯ СОЗДАНИЯ HUD ДЛЯ ЗДОРОВЬЯ С ТЕКСТУРАМИ
# ФУНКЦИЯ СОЗДАНИЯ HUD ДЛЯ ЗДОРОВЬЯ С ТЕКСТУРАМИ
def create_health_hud():
    global health_bar, health_text, heart_icon, stage_text, enemies_text

    # Полоска здоровья
    health_bar = Entity(
        parent=camera.ui,
        model='quad',
        color=color.green,
        scale=(0.28, 0.04),
        position=(-0.7, 0.45, -0.01)
    )

    # Текст здоровья
    health_text = Text(
        parent=camera.ui,
        text=f"HP: {player_health}/{player_max_health}",
        position=(-0.87, 0.39, -0.02),
        scale=1.58,
        color=color.white,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.5),
        font='custom2.ttf'
    )

    # Иконка сердца с защитой от ошибок текстур
    try:
        heart_icon = Entity(
            parent=camera.ui,
            model='quad',
            texture='full_heart.png',
            scale=(0.05, 0.05),
            position=(-0.75, 0.45, -0.02)
        )
    except:
        # Если текстура не найдена, используем цветной квадрат
        heart_icon = Entity(
            parent=camera.ui,
            model='quad',
            color=color.red,
            scale=(0.05, 0.05),
            position=(-0.88, 0.45, -0.02)
        )
        print("⚠️ Текстура сердца не найдена, используем цветной квадрат")

    # Текст текущего стейджа
    stage_text = Text(
        parent=camera.ui,
        text=f"STAGE: 1",
        position=(-0.85, 0.25, -0.02),
        scale=1.5,
        color=color.yellow,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.5),
        font='custom2.ttf'
    )

    # Текст прогресса врагов
    enemies_text = Text(
        parent=camera.ui,
        text="Враги: 0/0",
        position=(-0.85, 0.13, -0.02),
        scale=1.2,
        color=color.white,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.5),
        font='custom2.ttf'
    )


# ФУНКЦИЯ ОБНОВЛЕНИЯ HUD
def update_health_hud():
    global health_bar, health_text, heart_icon, player_health, player_max_health, stage_text, enemies_text

    # ОБНОВЛЯЕМ И
    # НФОРМАЦИЮ О СТЕЙДЖЕ И ВРАГАХ
    if stage_text:
        stage_text.text = f"STAGE: {current_stage}"

    if enemies_text:
        enemies_text.text = f"Враги: {stage_enemies_killed}/{enemies_to_kill_for_stage}"

    # ОБНОВЛЯЕМ ЗДОРОВЬЕ
    if health_bar and health_text and heart_icon:
        # Обновляем полоску здоровья
        health_percentage = player_health / player_max_health
        health_bar.scale_x = 0.28 * health_percentage
        health_bar.x = -0.75 + (0.28 * (1 - health_percentage)) / 2

        # Меняем цвет полоски в зависимости от здоровья
        if health_percentage > 0.6:
            health_bar.color = color.green
        elif health_percentage > 0.3:
            health_bar.color = color.orange
        else:
            health_bar.color = color.red

        # МЕНЯЕМ ТЕКСТУРУ СЕРДЦА В ЗАВИСИМОСТИ ОТ ЗДОРОВЬЯ
        if player_health <= 20:
            try:
                heart_icon.texture = 'low_hp_heart.png'
            except:
                heart_icon.color = color.red
        else:
            try:
                heart_icon.texture = 'full_heart.png'
            except:
                heart_icon.color = color.red

        # Обновляем текст
        health_text.text = f"HP: {player_health}/{player_max_health}"

        # Эффект пульсации при низком здоровье
        if health_percentage < 0.3:
            pulse = math.sin(time.time() * 8) * 0.1 + 0.9
            health_bar.color = color.red * pulse
            health_text.color = color.red * pulse

            # Анимация сердца
            heart_pulse = math.sin(time.time() * 10) * 0.2 + 0.8
            new_scale_x = 0.05 * heart_pulse
            new_scale_y = 0.05 * heart_pulse
            heart_icon.scale = (new_scale_x, new_scale_y)
        else:
            health_text.color = color.white
            heart_icon.scale = (0.05, 0.05)  # Возвращаем нормальный размер


# ФУНКЦИЯ НАНЕСЕНИЯ УРОНА
def take_damage(amount):
    global player_health
    player_health = max(0, player_health - amount)

    # Безопасное обновление HUD
    if 'update_health_hud' in globals():
        update_health_hud()

    # Эффект при получении урона
    if 'create_damage_effect' in globals():
        create_damage_effect()

    print(f"💔 Получено урона: {amount}. Здоровье: {player_health}/{player_max_health}")


# ФУНКЦИЯ ЛЕЧЕНИЯ
def heal(amount):
    global player_health
    player_health = min(player_max_health, player_health + amount)
    update_health_hud()

    # Эффект лечения
    create_heal_effect()

    print(f"💚 Восстановлено: {amount}. Здоровье: {player_health}/{player_max_health}")


# ЭФФЕКТ ПРИ ПОЛУЧЕНИИ УРОНА
def create_damage_effect():
    global heart_icon

    # Красная вспышка по краям экрана
    damage_overlay = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(1, 0, 0, 0.3),
        scale=(2, 2),
        position=(0, 0, -0.1)
    )

    # Анимация сердца при получении урона
    if heart_icon:
        original_scale = heart_icon.scale
        # ИСПРАВЛЕННОЕ УМНОЖЕНИЕ - каждый компонент отдельно
        new_scale_x = original_scale[0] * 1.3
        new_scale_y = original_scale[1] * 1.3
        heart_icon.scale = (new_scale_x, new_scale_y)

        def reset_heart():
            if heart_icon and heart_icon.enabled:
                heart_icon.scale = original_scale

        invoke(reset_heart, delay=0.3)

    # Анимация исчезновения
    def fade_damage_effect():
        start_time = time.time()
        duration = 0.5

        def update_fade():
            current_time = time.time()
            progress = (current_time - start_time) / duration

            if progress < 1 and damage_overlay.enabled:
                damage_overlay.color = color.rgba(1, 0, 0, 0.3 * (1 - progress))
                invoke(update_fade, delay=1 / 60)
            else:
                destroy(damage_overlay)

        update_fade()

    fade_damage_effect()


# ЭФФЕКТ ЛЕЧЕНИЯ
def create_heal_effect():
    global heart_icon

    # Зеленая вспышка
    heal_overlay = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 1, 0, 0.2),
        scale=(2, 2),
        position=(0, 0, -0.1)
    )

    # Анимация сердца при лечении
    if heart_icon:
        original_scale = heart_icon.scale
        # ИСПРАВЛЕННОЕ УМНОЖЕНИЕ
        new_scale_x = original_scale[0] * 1.5
        new_scale_y = original_scale[1] * 1.5
        heart_icon.scale = (new_scale_x, new_scale_y)

        def reset_heart():
            if heart_icon and heart_icon.enabled:
                heart_icon.scale = original_scale

        invoke(reset_heart, delay=0.5)

    # Частицы лечения
    for i in range(8):
        heal_particle = Text(
            parent=camera.ui,
            text="+",
            color=color.green,
            scale=3,
            position=(uniform(-0.5, 0.5), uniform(-0.3, 0.3), -0.05),
            font='custom2.ttf'
        )

        def animate_heal_particle(particle=heal_particle):
            start_time = time.time()
            duration = 1.0

            def update_particle():
                current_time = time.time()
                progress = (current_time - start_time) / duration

                if progress < 1 and particle.enabled:
                    particle.y += 0.5 * time.dt
                    particle.alpha = 1 - progress
                    particle.scale = 3 * (1 - progress * 0.5)
                    invoke(update_particle, delay=1 / 60)
                else:
                    destroy(particle)

            update_particle()

        animate_heal_particle()

    # Анимация исчезновения
    def fade_heal_effect():
        start_time = time.time()
        duration = 0.8

        def update_fade():
            current_time = time.time()
            progress = (current_time - start_time) / duration

            if progress < 1 and heal_overlay.enabled:
                heal_overlay.color = color.rgba(0, 1, 0, 0.2 * (1 - progress))
                invoke(update_fade, delay=1 / 60)
            else:
                destroy(heal_overlay)

        update_fade()

    fade_heal_effect()


def heal_player(amount=10):
    global player_health, player_max_health

    old_health = player_health
    player_health = min(player_health + amount, player_max_health)

    # Создаем эффект лечения только если здоровье действительно увеличилось
    if player_health > old_health:
        create_heal_effect()
        print(f"💚 Исцеление! +{amount} HP. Теперь {player_health}/{player_max_health} HP")
        return True
    else:
        print("💔 Здоровье уже максимальное!")
        return False


# ФУНКЦИЯ ПРОВЕРКИ НАЖАТИЯ КЛАВИШИ J ДЛЯ ЛЕЧЕНИЯ

# ФУНКЦИЯ СОЗДАНИЯ АПТЕЧКИ
def create_heal_pickup(position):
    heal_pickup = Entity(
        model='heal_pickup.glb',
        position=position,
        scale=1,
        collider='sphere'
    )

    # ПЕРЕМЕННЫЕ ДЛЯ УПРАВЛЕНИЯ АНИМАЦИЯМИ
    heal_pickup.is_animating = True

    # ДОБАВЛЯЕМ АНИМАЦИЮ ВРАЩЕНИЯ ДЛЯ АПТЕЧКИ
    def rotate_heal():
        if heal_pickup and heal_pickup.enabled and heal_pickup.is_animating:
            heal_pickup.animate_rotation_y(heal_pickup.rotation_y + 360, duration=3, curve=curve.linear)
            # ПОВТОРЯЕМ АНИМАЦИЮ ЧЕРЕЗ 3 СЕКУНДЫ
            invoke(rotate_heal, delay=3)

    # ДОБАВЛЯЕМ АНИМАЦИЮ ПЛАВАНИЯ ВВЕРХ-ВНИЗ
    def float_heal():
        if heal_pickup and heal_pickup.enabled and heal_pickup.is_animating:
            # Анимация вверх
            heal_pickup.animate_y(heal_pickup.y + 0.3, duration=1, curve=curve.in_out_quad)
            # Анимация вниз через 1 секунду
            invoke(lambda: heal_pickup.animate_y(heal_pickup.y - 0.3, duration=1,
                                                 curve=curve.in_out_quad) if heal_pickup and heal_pickup.enabled and heal_pickup.is_animating else None,
                   delay=1)
            # Повторяем всю последовательность через 2 секунды
            invoke(float_heal, delay=2)

    # ЗАПУСКАЕМ АНИМАЦИИ
    rotate_heal()
    float_heal()

    heal_pickups.append(heal_pickup)
    return heal_pickup


# ФУНКЦИЯ ПРОВЕРКИ СТОЛКНОВЕНИЙ С АПТЕЧКАМИ
def check_heal_pickup_collisions():
    global heal_pickup_cooldown, player_health

    # Обновляем кулдаун
    if heal_pickup_cooldown > 0:
        heal_pickup_cooldown -= time.dt
        return

    # Проверяем каждую аптечку
    for pickup in heal_pickups[:]:  # Используем копию списка для безопасного удаления
        if not pickup or not pickup.enabled:
            continue

        # Проверяем расстояние до игрока
        distance = (player.position - pickup.position).length()

        if distance < 2.0:  # Дистанция подбора
            # Подбираем аптечку
            pickup_heal(pickup)


# ФУНКЦИЯ ПОДБОРА АПТЕЧКИ
def pickup_heal(pickup):
    global player_health, player_max_health, heal_pickup_cooldown

    # Проверяем, нужно ли лечение
    if player_health >= player_max_health:
        print("💚 Здоровье уже полное!")
        return

    # ОСТАНАВЛИВАЕМ АНИМАЦИИ ПЕРЕД УНИЧТОЖЕНИЕМ
    if pickup:
        pickup.is_animating = False

    # Лечим игрока
    old_health = player_health
    player_health = min(player_health + 30, player_max_health)  # +30 HP
    heal_amount = player_health - old_health

    # Эффекты подбора
    create_heal_effect()
    create_pickup_effect(pickup.position)

    # УДАЛЯЕМ АПТЕЧКУ БЕЗОПАСНЫМ СПОСОБОМ
    if pickup:
        pickup.enabled = False
        destroy(pickup)

    # Удаляем из списка
    if pickup in heal_pickups:
        heal_pickups.remove(pickup)

    # Устанавливаем кулдаун
    heal_pickup_cooldown = 0.5

    print(f"💊 Подобрана аптечка! +{heal_amount} HP. Теперь {player_health}/{player_max_health} HP")

    # Переспавним аптечку через некоторое время


# ФУНКЦИЯ СОЗДАНИЯ ЭФФЕКТА ПОДБОРА
# ФУНКЦИЯ СОЗДАНИЯ ЭФФЕКТА ПОДБОРА
def create_pickup_effect(position):
    # Создаем частицы подбора
    for i in range(8):
        particle = Entity(
            model='sphere',
            color=color.green,
            scale=random.uniform(0.1, 0.3),
            position=position,
            add_to_scene_entities=True
        )

        # Направление разлета частиц
        direction = Vec3(
            random.uniform(-1, 1),
            random.uniform(0.5, 1.5),
            random.uniform(-1, 1)
        ).normalized()

        def animate_particle(p=particle, d=direction):
            start_time = time.time()
            lifetime = 1.5

            def update_particle():
                current_time = time.time()
                age = current_time - start_time

                # ПРОВЕРЯЕМ ЧТО ЧАСТИЦА СУЩЕСТВУЕТ
                if p and p.enabled and age < lifetime:
                    p.position += d * 3 * time.dt
                    p.alpha = 1 - (age / lifetime)
                    p.scale = p.scale * (1 - age / lifetime * 0.5)
                    invoke(update_particle, delay=1 / 60)
                elif p:
                    destroy(p)

            update_particle()

        animate_particle()

    # Звук подбора (если есть)
    try:
        pickup_sound = Audio('pickup.ogg', loop=False, autoplay=False)
        pickup_sound.play()
    except:
        print("💊 Звук подбора не найден")


def create_ammo_pickup(position):
    # КОРРЕКТИРУЕМ ПОЗИЦИЮ - смещаем на 4 единицы по X чтобы триггер совпадал с моделью
    corrected_position = (position[0] - 3, position[1], position[2])

    ammo_pickup = Entity(
        model='ammo_pickup2.glb',
        position=corrected_position,  # Используем скорректированную позицию
        scale=0.02,
        collider='sphere'
    )

    # ПЛАВАНИЕ ВВЕРХ-ВНИЗ
    def float_ammo():
        if ammo_pickup and ammo_pickup.enabled:
            start_y = corrected_position[1]
            # Анимация вверх
            ammo_pickup.animate_y(start_y + 0.3, duration=1.5, curve=curve.in_out_quad)
            # Анимация вниз
            invoke(lambda: ammo_pickup.animate_y(start_y, duration=1.5,
                                                 curve=curve.in_out_quad) if ammo_pickup and ammo_pickup.enabled else None,
                   delay=1.5)
            # Повторяем
            invoke(float_ammo, delay=3.0)

    float_ammo()

    ammo_pickups.append(ammo_pickup)
    return ammo_pickup


# ФУНКЦИЯ СОЗДАНИЯ НЕСКОЛЬКИХ ПАЧЕК ПАТРОНОВ НА КАРТЕ


# ФУНКЦИЯ ПРОВЕРКИ СТОЛКНОВЕНИЙ С ПАТРОНАМИ
# ФУНКЦИЯ ПРОВЕРКИ СТОЛКНОВЕНИЙ С ПАТРОНАМИ
def check_ammo_pickup_collisions():
    global ammo_pickup_cooldown

    # Обновляем кулдаун
    if ammo_pickup_cooldown > 0:
        ammo_pickup_cooldown -= time.dt
        return

    # Проверяем каждую пачку патронов
    for pickup in ammo_pickups[:]:  # Используем копию списка для безопасного удаления
        if not pickup or not pickup.enabled:
            continue

        # Проверяем расстояние до игрока
        distance = (player.position - pickup.position).length()

        if distance < 2.0:  # Дистанция подбора
            # Подбираем патроны
            pickup_ammo(pickup)


# ФУНКЦИЯ ПОДБОРА ПАТРОНОВ
def pickup_ammo(pickup):
    global ammo_pickup_cooldown

    # Определяем тип патронов ТОЛЬКО для разблокированного оружия
    available_ammo_types = []

    # Проверяем какое оружие разблокировано и добавляем соответствующие типы патронов
    if "assault_rifle" in unlocked_weapons:
        available_ammo_types.append("assault_rifle")
    if "pistol" in unlocked_weapons:
        available_ammo_types.append("pistol")
    if "dual_uzi" in unlocked_weapons:
        available_ammo_types.append("dual_uzi")
    if "grenade_launcher" in unlocked_weapons:
        available_ammo_types.append("grenade_launcher")

    # Если нет разблокированного оружия, выходим
    if not available_ammo_types:
        print("❌ Нет разблокированного оружия для патронов!")
        return

    # Выбираем случайный тип патронов ИЗ РАЗБЛОКИРОВАННЫХ
    ammo_type = random.choice(available_ammo_types)
    ammo_info = ammo_data[ammo_type]

    # Количество патронов в пачке в зависимости от типа оружия
    ammo_amounts = {
        "assault_rifle": 60,
        "pistol": 40,
        "dual_uzi": 90,
        "grenade_launcher": 4
    }

    ammo_amount = ammo_amounts.get(ammo_type, 20)

    # Добавляем патроны в запас
    old_reserve = ammo_info['reserve_ammo']
    ammo_info['reserve_ammo'] += ammo_amount

    # Эффекты подбора
    create_ammo_pickup_effect(pickup.position, ammo_type)

    # Скрываем пачку патронов
    pickup.enabled = False

    # Удаляем из списка
    if pickup in ammo_pickups:
        ammo_pickups.remove(pickup)

    # Устанавливаем кулдаун
    ammo_pickup_cooldown = 0.5

    # Названия оружия для сообщения
    weapon_names = {
        "assault_rifle": "АВТОМАТ",
        "pistol": "ПИСТОЛЕТ",
        "dual_uzi": "DUAL UZI",
        "grenade_launcher": "ГРАНАТОМЕТ"
    }

    weapon_name = weapon_names.get(ammo_type, ammo_type)

    print(f"🔫 Подобраны патроны для {weapon_name}! +{ammo_amount}. Запас: {old_reserve} → {ammo_info['reserve_ammo']}")

    # Переспавним пачку через некоторое время
    invoke(respawn_ammo_pickup, delay=45.0)  # Респавн через 45 секунд


# ФУНКЦИЯ РЕСПАВНА ПАЧКИ ПАТРОНОВ
def respawn_ammo_pickup():
    # Определяем границы обеих зон вместе
    x_min, x_max = -56, 63  # общие границы по X для обеих зон
    z_min, z_max = -203, -46  # общие границы по Z для обеих зон

    attempts = 0
    max_attempts = 20  # Увеличиваем количество попыток

    while attempts < max_attempts:
        # Генерируем случайную позицию в общих границах
        x = random.uniform(x_min, x_max)
        z = random.uniform(z_min, z_max)
        position = (x, 0.5, z)

        # Проверяем, что позиция находится в одной из зон
        if is_position_in_spawn_area(Vec3(position)):
            # Проверяем расстояние до игрока
            if (Vec3(position) - player.position).length() >= 5:
                # Нашли подходящую позицию
                create_ammo_pickup(position)
                print(f"🔫 Новая пачка патронов зареспавнилась! Позиция: {position}")
                return

        attempts += 1

    # Если не нашли подходящую позицию
    invoke(respawn_ammo_pickup, delay=10.0)
    print("⚠️ Не удалось найти подходящее место для спавна патронов, пробуем снова через 10 сек")


# ФУНКЦИЯ СОЗДАНИЯ ЭФФЕКТА ПОДБОРА ПАТРОНОВ
def create_ammo_pickup_effect(position, ammo_type):
    # Цвет эффекта в зависимости от типа патронов
    effect_colors = {
        "assault_rifle": color.orange,
        "pistol": color.cyan,
        "dual_uzi": color.yellow,
        "grenade_launcher": color.green
    }

    effect_color = effect_colors.get(ammo_type, color.orange)

    # Названия для текста
    weapon_names = {
        "assault_rifle": "АВТОМАТ",
        "pistol": "ПИСТОЛЕТ",
        "dual_uzi": "DUAL UZI",
        "grenade_launcher": "ГРАНАТОМЕТ"
    }

    weapon_name = weapon_names.get(ammo_type, "ПАТРОНЫ")

    # Создаем частицы подбора
    for i in range(6):
        particle = Entity(
            model='cube',
            color=effect_color,
            scale=random.uniform(0.08, 0.15),
            position=position,
            add_to_scene_entities=True
        )

        # Направление разлета частиц
        direction = Vec3(
            random.uniform(-1, 1),
            random.uniform(0.5, 1.2),
            random.uniform(-1, 1)
        ).normalized()

        def animate_particle(p=particle, d=direction, color=effect_color):
            start_time = time.time()
            lifetime = 1.2

            def update_particle():
                current_time = time.time()
                age = current_time - start_time

                if p and p.enabled and age < lifetime:
                    p.position += d * 2 * time.dt
                    p.alpha = 1 - (age / lifetime)
                    p.scale = p.scale * (1 - age / lifetime * 0.5)
                    invoke(update_particle, delay=1 / 60)
                elif p:
                    destroy(p)

            update_particle()

        animate_particle()

    # Текст подбора
    ammo_amounts = {
        "assault_rifle": 30,
        "pistol": 20,
        "dual_uzi": 40,
        "grenade_launcher": 4
    }

    ammo_amount = ammo_amounts.get(ammo_type, 20)

    ammo_text = Text(
        parent=camera.ui,
        text=f"+{ammo_amount} {weapon_name}",
        position=(0, 0.1, -0.01),
        scale=2.0,
        color=effect_color,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.7),
        font='custom2.ttf'
    )

    # Анимация текста
    def animate_text():
        ammo_text.animate_position((0, 0.3, -0.01), duration=1.5, curve=curve.out_quad)
        ammo_text.animate_scale(0.5, duration=1.5, curve=curve.out_quad)
        invoke(lambda: destroy(ammo_text), delay=1.5)

    animate_text()

    # Звук подбора (если есть)
    try:
        ammo_pickup_sound = Audio('ammo_pickup.ogg', loop=False, autoplay=False)
        ammo_pickup_sound.play()
    except:
        print("🔫 Звук подбора патронов не найден")


# ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДОСТУПНЫХ ПАТРОНОВ (для отладки)
def print_available_ammo():
    print("🔫 Доступные типы патронов:")
    for weapon_type in unlocked_weapons:
        ammo_info = ammo_data[weapon_type]
        print(
            f"  {weapon_type}: {ammo_info['current_ammo']}/{ammo_info['max_ammo']} (запас: {ammo_info['reserve_ammo']})")


def spawn_assault_rifle_pickup():
    global current_mission_text

    # Создаем сообщение задания
    current_mission_text = Text(
        parent=camera.ui,
        text="ЗАДАНИЕ: Найдите автомат!!!",
        position=(-0.8, -0.4, 0),
        scale=2.5,
        color=color.yellow,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.7),
        font='custom2.ttf'
    )

    # Спавним автомат в случайном месте (но не слишком близко к игроку)
    spawn_position = (26, 20, 2)

    # Создаем модель автомата
    assault_rifle_pickup = Entity(
        model='decore_weanpo.glb',  # Модель автомата
        position=spawn_position,
        scale=1.5,
        collider='box',
        shader=dark_fantasy_shader
    )

    # АНИМАЦИЯ ВРАЩЕНИЯ
    def rotate_weapon():
        if assault_rifle_pickup and assault_rifle_pickup.enabled:
            assault_rifle_pickup.animate_rotation_y(assault_rifle_pickup.rotation_y + 360, duration=3,
                                                    curve=curve.linear)
            invoke(rotate_weapon, delay=3)

    # АНИМАЦИЯ ПЛАВАНИЯ ВВЕРХ-ВНИЗ
    def float_weapon():
        if assault_rifle_pickup and assault_rifle_pickup.enabled:
            # Анимация вверх
            assault_rifle_pickup.animate_y(assault_rifle_pickup.y + 0.4, duration=1.5, curve=curve.in_out_quad)
            # Анимация вниз через 1.5 секунды
            invoke(lambda: assault_rifle_pickup.animate_y(assault_rifle_pickup.y - 0.4, duration=1.5,
                                                          curve=curve.in_out_quad) if assault_rifle_pickup and assault_rifle_pickup.enabled else None,
                   delay=1.5)
            # Повторяем всю последовательность через 3 секунды
            invoke(float_weapon, delay=3.0)

    # ЭФФЕКТ СВЕЧЕНИЯ
    glow = Entity(
        model='sphere',
        color=color.rgba(1, 0.5, 0, 0.3),  # Оранжевое свечение
        scale=2.5,
        position=spawn_position,
        add_to_scene_entities=True
    )

    def update_glow():
        if glow and glow.enabled:
            pulse = math.sin(time.time() * 5) * 0.2 + 0.8
            glow.scale = 2.5 * pulse
            invoke(update_glow, delay=1 / 30)

    # ЗАПУСКАЕМ АНИМАЦИИ
    rotate_weapon()
    float_weapon()
    update_glow()

    weapon_pickups.append({
        'entity': assault_rifle_pickup,
        'glow': glow,
        'weapon_type': 'assault_rifle'
    })

    print("🔫 Автомат заспавнен на карте! Найдите его!")
    return assault_rifle_pickup


def find_valid_spawn_position():
    """Находит валидную позицию для спавна в одной из двух областей"""
    # Случайно выбираем зону спавна: 0 - основная зона, 1 - вторая зона
    zone_choice = random.randint(0, 1)

    if zone_choice == 0:
        # ПЕРВАЯ ЗОНА: основная (как было)
        center_x = 53
        center_y = 1.5
        center_z = -81

        # Размеры области
        width = 20  # ширина по оси X (от 43 до 63)
        length = 70  # длина по оси Z (от -116 до -46)

        zone_name = "ОСНОВНАЯ ЗОНА"
    else:
        # ВТОРАЯ ЗОНА: радиус 25 от точки (-31, 1, -178)
        center_x = -31
        center_y = 1.5
        center_z = -178

        # Размеры области (радиус 25, значит квадрат 50x50)
        width = 50  # от -56 до -6 по X
        length = 50  # от -203 до -153 по Z

        zone_name = "ВТОРАЯ ЗОНА (радиус 25)"

    # ЖЕСТКОЕ ограничение только выбранной областью
    for attempt in range(30):
        # Генерируем строго в выбранной области
        x = random.uniform(center_x - width / 2, center_x + width / 2)
        z = random.uniform(center_z - length / 2, center_z + length / 2)
        position = Vec3(x, center_y, z)

        # Проверяем что точно в пределах выбранной зоны
        if zone_choice == 0:
            in_zone = (43 <= x <= 63 and -116 <= z <= -46)
        else:
            in_zone = (-56 <= x <= -6 and -203 <= z <= -153)

        if in_zone:
            # Проверяем дистанцию до игрока
            distance_to_player = (position - player.position).length()
            if distance_to_player > 10:  # Не ближе 10 единиц
                print(f"✅ {zone_name}: X={x:.1f}, Z={z:.1f}")
                return position

    # Если не нашли - возвращаем центр выбранной зоны
    print(f"❌ Не нашли позицию в {zone_name}, возвращаем центр зоны")
    return Vec3(center_x, center_y, center_z)


def check_weapon_pickup_collisions():
    """Проверяет столкновения с оружием на карте"""
    for pickup_data in weapon_pickups[:]:
        if not pickup_data or not pickup_data['entity'] or not pickup_data['entity'].enabled:
            continue

        pickup = pickup_data['entity']

        # ИСПРАВЛЯЕМ: вызываем функцию distance()
        dist = distance(player.position, pickup.position)

        if dist < 3.0:  # Дистанция подбора
            pickup_weapon(pickup_data)


def pickup_weapon(pickup_data):
    """Подбирает оружие с карты"""
    global unlocked_weapons, current_mission_text

    weapon_type = pickup_data['weapon_type']

    # РАЗБЛОКИРОВЫВАЕМ ОРУЖИЕ
    if weapon_type not in unlocked_weapons:
        unlocked_weapons.append(weapon_type)

        # Сообщения для разных оружий
        weapon_names = {
            "assault_rifle": "АВТОМАТ",
            "dual_uzi": "DUAL UZI",
            "grenade_launcher": "ГРАНАТОМЕТ"
        }

        weapon_name = weapon_names.get(weapon_type, weapon_type)
        print(f"🎉 Вы нашли {weapon_name}! Оружие разблокировано!")

    # ЭФФЕКТ ПОДБОРА
    create_weapon_pickup_effect(pickup_data['entity'].position, weapon_type)

    # УДАЛЯЕМ С КАРТЫ
    if pickup_data['entity']:
        destroy(pickup_data['entity'])
    if pickup_data['glow']:
        destroy(pickup_data['glow'])

    # Удаляем из списка
    if pickup_data in weapon_pickups:
        weapon_pickups.remove(pickup_data)

    # УБИРАЕМ ТЕКСТ ЗАДАНИЯ
    if current_mission_text:
        destroy(current_mission_text)
        current_mission_text = None

    # АВТОМАТИЧЕСКИ ПЕРЕКЛЮЧАЕМСЯ НА НОВОЕ ОРУЖИЕ
    switch_weapon(weapon_type)


def create_weapon_pickup_effect(position, weapon_type):
    """Создает эффект при подборе оружия"""
    # Цвета для разных оружий
    effect_colors = {
        "assault_rifle": color.orange,
        "dual_uzi": color.yellow,
        "grenade_launcher": color.green
    }

    effect_color = effect_colors.get(weapon_type, color.orange)

    # Названия оружий
    weapon_names = {
        "assault_rifle": "АВТОМАТ",
        "dual_uzi": "DUAL UZI",
        "grenade_launcher": "ГРАНАТОМЕТ"
    }

    weapon_name = weapon_names.get(weapon_type, "ОРУЖИЕ")

    # Частицы
    for i in range(12):
        particle = Entity(
            model='sphere',
            color=effect_color,
            scale=random.uniform(0.1, 0.3),
            position=position,
            add_to_scene_entities=True
        )

        direction = Vec3(
            random.uniform(-1, 1),
            random.uniform(0.5, 1.5),
            random.uniform(-1, 1)
        ).normalized()

        def animate_particle(p=particle, d=direction):
            start_time = time.time()
            lifetime = 1.5

            def update_particle():
                current_time = time.time()
                age = current_time - start_time

                if p and p.enabled and age < lifetime:
                    p.position += d * 4 * time.dt
                    p.alpha = 1 - (age / lifetime)
                    p.scale = p.scale * (1 - age / lifetime * 0.5)
                    invoke(update_particle, delay=1 / 60)
                elif p:
                    destroy(p)

            update_particle()

        animate_particle()

    # Сообщение
    unlock_text = Text(
        parent=camera.ui,
        text=f"{weapon_name} РАЗБЛОКИРОВАН!",
        position=(0, 0.2, 0),
        scale=3,
        color=effect_color,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.8),
        font='custom2.ttf'
    )

    def fade_text():
        unlock_text.animate_scale(0.5, duration=2.0)
        unlock_text.animate_color(color.rgba(effect_color[0], effect_color[1], effect_color[2], 0), duration=2.0)
        invoke(lambda: destroy(unlock_text), delay=2.0)

    fade_text()


def hard_cleanup_all():
    """Полная очистка ВСЕХ систем (кроме снарядов врагов в полете)"""
    cleaned = 0
    object_manager.cleanup_dead_objects()

    # 1. ОЧИСТКА ВРАГОВ - УДАЛЯЕМ ВСЕХ МЕРТВЫХ
    global enemies
    for enemy_obj in enemies[:]:
        if not enemy_obj or not enemy_obj.entity or not enemy_obj.entity.enabled:
            # Уничтожаем все связанные объекты
            if enemy_obj.entity and enemy_obj.entity.enabled:
                destroy(enemy_obj.entity)
            enemies.remove(enemy_obj)
            cleaned += 1

    # 2. ОЧИСТКА ВСЕХ ЭФФЕКТОВ (без условий по времени)
    for blood_particles in blood_effects[:]:
        for particle_data in blood_particles[:]:
            if len(particle_data) == 5:
                particle, direction, speed, spawn_time, original_size = particle_data
                if particle and particle.enabled:
                    destroy(particle)
                    cleaned += 1
        blood_effects.remove(blood_particles)

    # 3. ОЧИСТКА ВСЕХ ТРАССЕРОВ
    for tracer_data in bullet_tracers[:]:
        if len(tracer_data) == 2:
            tracer, spawn_time = tracer_data
            if tracer and tracer.enabled:
                destroy(tracer)
                cleaned += 1
        bullet_tracers.remove(tracer_data)

    # 4. ОЧИСТКА ВСЕХ ВСПЫШЕК
    for flash_data in muzzle_flash_entities[:]:
        if len(flash_data) == 2:
            particles, spawn_time = flash_data
            for particle, direction, size in particles:
                if particle and particle.enabled:
                    destroy(particle)
                    cleaned += 1
        muzzle_flash_entities.remove(flash_data)

    # 5. ОЧИСТКА ТОЛЬКО ВЗРЫВНЫХ СНАРЯДОВ (игрока)
    # СНАРЯДЫ ВРАГОВ НЕ ОЧИЩАЕМ - они могут быть в полете!
    global enemy_projectiles, explosive_projectiles

    # Очищаем только взрывные снаряды (игрока)
    for projectile in explosive_projectiles[:]:
        if projectile and projectile.enabled:
            destroy(projectile)
            cleaned += 1
        explosive_projectiles.remove(projectile)

    # СНАРЯДЫ ВРАГОВ ПРОПУСКАЕМ - они обрабатываются в своей системе
    # enemy_projectiles НЕ очищаем!

    # 6. ПРИНУДИТЕЛЬНЫЙ СБОР МУСОРА
    import gc
    gc.collect()
    print(f"🧹 ПОЛНАЯ ОЧИСТКА: удалено {cleaned} объектов")
    print(f"📊 Врагов осталось: {len(enemies)}")
    print(f"🎯 Снарядов врагов в полете: {len(enemy_projectiles)}")
    return cleaned


def show_shader_activated_message():
    """Показывает сообщение о включении шейдера"""
    message = Text(
        parent=camera.ui,
        text="🔴 VHS EFFECTS ACTIVATED!",
        position=(0, 0.3, 0),
        scale=2.5,
        color=color.red,
        background=True,
        background_color=color.rgba(0, 0, 0, 0.8)
    )

    # Анимация появления и исчезновения
    message.animate_scale(1.5, duration=0.5, curve=curve.out_quad)
    message.animate_position((0, 0.4, 0), duration=0.5)

    def fade_out():
        message.animate_scale(0.5, duration=1.0)
        message.animate_color(color.rgba(1, 0, 0, 0), duration=1.0)
        invoke(lambda: destroy(message), delay=1.0)

    invoke(fade_out, delay=2.0)


def debug_memory():
    """Диагностика памяти"""
    print("=== ДИАГНОСТИКА ПАМЯТИ ===")
    print(f"Врагов: {len(enemies)}")
    print(f"Снарядов врагов: {len(enemy_projectiles)}")
    print(f"Эффектов крови: {len(blood_effects)}")
    print(f"Трассеров: {len(bullet_tracers)}")
    print(f"Вспышек: {len(muzzle_flash_entities)}")

    # Подсчет "мертвых" врагов
    dead_enemies = 0
    for enemy in enemies:
        if not enemy.entity or not enemy.entity.enabled:
            dead_enemies += 1
    print(f"Мертвых врагов в списке: {dead_enemies}")


def reset_performance():
    """Полный сброс производительности"""
    print("⚡ СБРОС ПРОИЗВОДИТЕЛЬНОСТИ")

    # 1. Очистка ВСЕХ систем
    hard_cleanup_all()

    # 2. Сброс истории игрока
    if hasattr(player, 'positions_history'):
        player.positions_history.clear()

    # 3. Сброс шейдерных эффектов
    global grenade_effect, shoot_strength, reload_strength, walk_strength
    grenade_effect = 0
    shoot_strength = 0
    reload_strength = 0
    walk_strength = 0

    # 4. Принудительный сбор мусора
    import gc
    gc.collect()

    print("✅ Производительность сброшена")


def safe_render_cleanup():
    """Безопасная очистка рендер-системы без удаления активных объектов"""
    print("🧹 Безопасная очистка рендер-системы...")

    cleaned = 0

    # Получаем список защищенных объектов
    protected_objects = protect_critical_objects()

    # 1. Очищаем ТОЛЬКО неактивные и неважные объекты
    for entity in scene.entities[:]:  # Используем копию списка
        if (hasattr(entity, 'enabled') and not entity.enabled and
                entity not in protected_objects):
            try:
                destroy(entity)
                cleaned += 1
            except:
                pass  # Игнорируем ошибки уничтожения

    # 2. Очистка только наших списков эффектов
    for blood_particles in blood_effects[:]:
        for particle_data in blood_particles[:]:
            if len(particle_data) == 5:
                particle, direction, speed, spawn_time, original_size = particle_data
                if particle and particle.enabled and particle not in protected_objects:
                    try:
                        destroy(particle)
                        cleaned += 1
                    except:
                        pass

    # 3. Очистка трассеров и вспышек
    for tracer_data in bullet_tracers[:]:
        if len(tracer_data) == 2:
            tracer, spawn_time = tracer_data
            if tracer and tracer.enabled and tracer not in protected_objects:
                try:
                    destroy(tracer)
                    cleaned += 1
                except:
                    pass

    for flash_data in muzzle_flash_entities[:]:
        if len(flash_data) == 2:
            particles, spawn_time = flash_data
            for particle, direction, size in particles:
                if particle and particle.enabled and particle not in protected_objects:
                    try:
                        destroy(particle)
                        cleaned += 1
                    except:
                        pass

    blood_effects.clear()
    bullet_tracers.clear()
    muzzle_flash_entities.clear()

    # 4. Очистка снарядов врагов
    global enemy_projectiles, explosive_projectiles
    for projectile in enemy_projectiles[:]:
        if projectile and projectile.enabled and projectile not in protected_objects:
            try:
                destroy(projectile)
                cleaned += 1
            except:
                pass
    enemy_projectiles.clear()

    for projectile in explosive_projectiles[:]:
        if projectile and projectile.enabled and projectile not in protected_objects:
            try:
                destroy(projectile)
                cleaned += 1
            except:
                pass
    explosive_projectiles.clear()

    # 5. Принудительный сбор мусора
    import gc
    gc.collect()

    print(f"✅ Безопасная очистка: удалено {cleaned} объектов")
    return cleaned


def protect_critical_objects():
    """Защита критически важных объектов от удаления"""
    critical_objects = [
        player, camera, weapon, ground,
        weapon_hud, health_bar, heart_icon, health_text,
        stage_text, enemies_text, press_e_text,
        dialogue_bg, npc_name, npc_line, button1, button2,
        human, head, body, human_collider,
        sky
    ]

    # Добавляем все оружия из словаря
    if weapons:
        critical_objects.extend(weapons.values())

    # Добавляем всех активных врагов
    for enemy in enemies:
        if enemy.entity and enemy.entity.enabled:
            critical_objects.append(enemy.entity)

    # Добавляем аптечки и патроны
    critical_objects.extend(heal_pickups)
    critical_objects.extend(ammo_pickups)
    critical_objects.extend(weapon_pickups)

    # Фильтруем None значения
    critical_objects = [obj for obj in critical_objects if obj is not None]

    return critical_objects


def update_shader_intensity():
    """Обновляет интенсивность шейдера в зависимости от текущего уровня"""
    global shader_intensity, current_stage, shader_enabled

    # Сохраняем предыдущую интенсивность для проверки включения
    previous_intensity = shader_intensity
    previous_enabled = shader_enabled

    if current_stage <= 9:
        shader_intensity = 0.0  # Шейдер полностью выключен
        shader_enabled = False  # ВЫКЛЮЧАЕМ шейдер
    elif current_stage == 10:
        shader_intensity = 0.3  # 30% - шейдер включается
        shader_enabled = True  # ВКЛЮЧАЕМ шейдер
    elif current_stage == 15:
        shader_intensity = 0.7  # 70%
        shader_enabled = True  # Шейдер включен
    elif current_stage >= 20:
        shader_intensity = 1.5  # 150% (превышение 100% для усиленного эффекта)
        shader_enabled = True  # Шейдер включен
    else:
        # Плавное увеличение между ключевыми уровнями
        if current_stage < 15:
            shader_intensity = 0.3 + (current_stage - 10) * 0.08  # 30% → 70%
        else:
            shader_intensity = 0.7 + (current_stage - 15) * 0.16  # 70% → 150%
        shader_enabled = True  # Шейдер включен для промежуточных уровней

    # Ограничиваем максимальную интенсивность (можно больше 100%)
    shader_intensity = max(0.0, shader_intensity)

    # Применяем интенсивность к шейдеру
    camera.set_shader_input("base_intensity", shader_intensity)

    # Сообщение о включении шейдера (только когда он включается впервые)
    if not previous_enabled and shader_enabled and current_stage == 10:
        print("🎚️ 🔴 ШЕЙДЕР АКТИВИРОВАН! VHS эффекты включены!")
        show_shader_activated_message()
    elif not shader_enabled:
        print("🎚️ ⚪ Шейдер выключен")
    else:
        print(f"🎚️ Интенсивность шейдера: {shader_intensity * 100:.0f}% (Stage {current_stage})")


def animate_explosion_particle(particle, direction, speed, lifetime):
    """Анимация частицы взрыва"""
    start_time = time.time()
    start_scale = particle.scale

    def update_particle():
        current_time = time.time()
        age = current_time - start_time

        if age < lifetime and particle and particle.enabled:
            # Движение
            particle.position += direction * speed * time.dt

            # Гравитация
            particle.position.y -= time.dt * 3

            # Исчезновение
            progress = age / lifetime
            particle.alpha = 1.0 - progress
            particle.scale = start_scale * (1 - progress * 0.7)

            invoke(update_particle, delay=1 / 60)
        elif particle:
            destroy(particle)

    update_particle()


def destroy_projectile(projectile):
    """Безопасное уничтожение снаряда и всех связанных объектов"""
    if not projectile:
        return

    # Уничтожаем связанные объекты
    related_objects = []

    if hasattr(projectile, 'glow'):
        related_objects.append(projectile.glow)
    if hasattr(projectile, 'particles'):
        related_objects.extend(projectile.particles)

    # Уничтожаем основной снаряд
    try:
        destroy(projectile)
    except:
        pass

    # Уничтожаем связанные объекты
    for obj in related_objects:
        if obj and hasattr(obj, 'enabled') and obj.enabled:
            try:
                destroy(obj)
            except:
                pass


def apply_stun_effect(duration=0.5):
    """Применяет эффект оглушения к игроку"""
    global is_stunned, stun_effect_time, stun_effect_duration

    is_stunned = True
    stun_effect_duration = duration
    stun_effect_time = 0

    # Визуальный эффект оглушения
    stun_overlay = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(1, 1, 1, 0.3),
        scale=(2, 2),
        position=(0, 0, -0.1),
        eternal=False
    )

    # Анимация исчезновения
    stun_overlay.animate_color(color.rgba(1, 1, 1, 0), duration=duration)
    invoke(lambda: destroy(stun_overlay) if stun_overlay else None, delay=duration)

    print(f"😵 Игрок оглушен на {duration} секунд!")


def convert_all_old_projectiles():
    """Конвертирует все старые снаряды в новый формат"""
    for projectile in enemy_projectiles:
        ensure_projectile_attributes(projectile)
def update_all_animations():
    """Обновляет все активные анимации в игре"""
    # Если есть глобальная система анимаций - обновляем ее
    if 'animation_system' in globals() and animation_system:
        animation_system.update()


def create_trigger_area():
    """Создает визуальную зону триггера без коллайдера"""
    global trigger_area

    # Создаем визуальную зону (без коллайдера, можно войти)
    trigger_area = Entity(
        model='cube',
        color=color.rgba(1, 0, 0, 0.15),  # Очень прозрачный красный куб
        scale=(10, 10, 10),  # Размер 10x10x10
        position=trigger_center,  # Центральные координаты
        eternal=True,
        collider=None  # НЕТ КОЛЛАЙДЕРА!
    )
    print(f"🎯 Большая триггерная зона создана (можно войти):")
    print(f"📍 Центр: {trigger_center}")
    print(f"📏 Размер: 10x10x10 единиц")
    print(f"📊 Область: X={trigger_center.x - 5:.2f} до {trigger_center.x + 5:.2f}")
    print(f"          Y={trigger_center.y - 5:.2f} до {trigger_center.y + 5:.2f}")
    print(f"          Z={trigger_center.z - 5:.2f} до {trigger_center.z + 5:.2f}")
    print("⚠️ Зона без коллайдера - можно свободно входить")


def check_trigger():
    """Проверяет приближение к триггерной зоне (простая проверка расстояния)"""
    global trigger_cooldown, trigger_activated

    if not trigger_area or not game_started or trigger_activated:
        return

    # Обновляем кулдаун
    if trigger_cooldown > 0:
        trigger_cooldown -= time.dt
        return

    # Проверяем находится ли игрок в кубе 10x10x10
    in_zone = (
            abs(player.position.x - trigger_center.x) <= 5 and
            abs(player.position.y - trigger_center.y) <= 5 and
            abs(player.position.z - trigger_center.z) <= 5
    )

    if in_zone:
        # Расстояние до центра для отладки
        distance = (player.position - trigger_center).length()

        # Проверяем, не был ли триггер уже активирован в этом заходе
        if not getattr(trigger_area, 'player_in_zone', False):
            print(f"🎯 Игрок вошел в триггерную зону! Расстояние до центра: {distance:.2f}")
            print(f"📍 Позиция игрока: X={player.position.x:.2f}, Y={player.position.y:.2f}, Z={player.position.z:.2f}")

            if current_stage < 25:
                # Волна < 25 - показываем подсказку
                show_trigger_hint()
                trigger_cooldown = 6.0  # Кулдаун 6 секунд
            else:
                # Волна >= 25 - показываем поздравление и выход
                trigger_activated = True
                show_congratulation()
                trigger_cooldown = 10.0  # Долгий кулдаун

            # Отмечаем что игрок активировал триггер
            trigger_area.player_in_zone = True

            # Меняем цвет зоны при активации
            trigger_area.animate_color(color.rgba(1, 0.5, 0, 0.3), duration=1.0)

    else:
        # Игрок вышел из зоны - сбрасываем флаг
        if getattr(trigger_area, 'player_in_zone', False):
            trigger_area.player_in_zone = False
            trigger_area.animate_color(color.rgba(1, 0, 0, 0.15), duration=1.0)


def show_trigger_hint():
    """Показывает подсказку 'Вы еще не готовы'"""
    global trigger_hint_text

    # Скрываем предыдущую подсказку если есть
    if trigger_hint_text:
        try:
            destroy(trigger_hint_text)
        except:
            pass

    # Создаем текст подсказки сверху экрана
    trigger_hint_text = Text(
        parent=camera.ui,
        text="ВЫ ЕЩЕ НЕ ГОТОВЫ",
        position=(0, 0.35, 0),
        scale=2.8,
        color=color.rgba(1, 0.2, 0.2, 1),
        background=True,
        background_color=color.rgba(0, 0, 0, 0.8),
        font='custom2.ttf',
        eternal=False
    )

    # Простая анимация появления
    trigger_hint_text.animate_scale(3.0, duration=0.3, curve=curve.out_quad)

    # Удаляем через 4 секунды
    invoke(lambda: hide_trigger_hint(), delay=4.0)


def hide_trigger_hint():
    """Правильно скрывает подсказку триггера"""
    global trigger_hint_text

    if trigger_hint_text:
        try:
            # Просто уничтожаем объект без анимации
            destroy(trigger_hint_text)
        except:
            pass
        trigger_hint_text = None


def show_congratulation():
    """Показывает поздравление и затемнение экрана"""
    global trigger_congratulation_text, trigger_fade_overlay

    # Отключаем управление игроком
    player.enabled = False

    # 1. Полное затемнение экрана
    trigger_fade_overlay = Entity(
        parent=camera.ui,
        model='quad',
        color=color.black,
        scale=(2, 2),
        z=-10,
        eternal=False
    )

    # Плавное затемнение (3 секунды)
    trigger_fade_overlay.color = color.rgba(0, 0, 0, 0)
    trigger_fade_overlay.animate_color(color.rgba(0, 0, 0, 1), duration=3.0)

    # 2. Текст "Congratulation" по центру
    trigger_congratulation_text = Text(
        parent=camera.ui,
        text="CONGRATULATION",
        position=(0, 0, 0),
        scale=0.1,  # Начинаем с маленького
        color=color.rgba(1, 0.84, 0, 0),  # Золотой, полностью прозрачный
        font='custom2.ttf',
        eternal=False
    )

    # Анимация появления текста
    invoke(lambda: trigger_congratulation_text.animate_color(color.rgba(1, 0.84, 0, 1), duration=2.0), delay=1.0)
    invoke(lambda: trigger_congratulation_text.animate_scale(4.5, duration=2.5, curve=curve.out_quad), delay=1.0)

    # Эффект мерцания
    def flash_effect():
        if trigger_congratulation_text:
            trigger_congratulation_text.animate_color(color.rgba(1, 1, 1, 1), duration=0.3)
            invoke(lambda: trigger_congratulation_text.animate_color(color.rgba(1, 0.84, 0, 1), duration=0.3)
            if trigger_congratulation_text else None, delay=0.3)

    # Запускаем мерцание каждую секунду
    invoke(flash_effect, delay=2.5)
    invoke(flash_effect, delay=3.5)
    invoke(flash_effect, delay=4.5)

    # 3. Сообщение об окончании
    end_text = Text(
        parent=camera.ui,
        text="Вы достигли 25+ волны!",
        position=(0, -0.2, 0),
        scale=1.8,
        color=color.rgba(1, 1, 1, 0),
        font='custom2.ttf',
        eternal=False
    )

    invoke(lambda: end_text.animate_color(color.rgba(1, 1, 1, 1), duration=1.5), delay=2.0)

    print("🎉 ПОЗДРАВЛЯЕМ! Вы достигли 25+ волны!")

    # 4. Выход через 7 секунд
    invoke(quit_game, delay=7.0)


def quit_game():
    """Выход из игры с анимацией"""
    print("🚪 Выход из игры...")

    # Анимация исчезновения текста
    if trigger_congratulation_text:
        trigger_congratulation_text.animate_color(color.rgba(1, 0.84, 0, 0), duration=1.0)

    # Выход через 1 секунду
    invoke(lambda: application.quit(), delay=1.0)



def update():
    global coordinates_debug_timer, player_health, is_sprinting
    global in_dialogue, is_moving, shake_timer, is_shooting, shoot_animation_time
    global is_firing_auto, last_fire_time, last_shoot_sound_time
    global target_weapon_rotation, current_weapon_rotation, target_weapon_position, current_weapon_position, mouse_movement
    global stun_effect_time, is_stunned, shoot_strength, reload_strength, walk_strength, shader_enabled, grenade_effect
    global lvl, shader_intensity
    if game_started and trigger_area:
        check_trigger()
    if random.random() < 0.5:  # 50% шанс обновления каждый кадр
        update_blood_effects_optimized()

    if not hasattr(update, 'last_blood_cleanup'):
        update.last_blood_cleanup = time.time()

    if time.time() - update.last_blood_cleanup > 5.0:  # Каждые 5 секунд
        cleanup_excess_blood_effects()
        update.last_blood_cleanup = time.time()
    update_all_animations()
    # =========== ЕСЛИ ИГРА НЕ НАЧАЛАСЬ ===========
    # =========== ЕСЛИ ИГРА НЕ НАЧАЛАСЬ ===========
    if not game_started:

        # МИНИМАЛЬНЫЕ ОБНОВЛЕНИЯ ДЛЯ ЛОББИ
        camera.set_shader_input("time", time.time())
        camera.set_shader_input("base_intensity", 0.0)
        camera.set_shader_input("shoot_strength", 0.0)
        camera.set_shader_input("reload_strength", 0.0)
        camera.set_shader_input("walk_strength", 0.0)
        camera.set_shader_input("grenade_effect", 0.0)
        if is_selecting_weapon and camera_mode == "table_view":
            highlight_hovered_weapon()


        # Простая проверка - игрок не должен упасть с платформы
        if player.position.y < 70:
            player.position = Vec3(0, 86, 0)
            if hasattr(player, 'velocity_y'):
                player.velocity_y = 0

        # ТОЛЬКО если идет выбор оружия - проверяем клики
        if is_selecting_weapon:
            # ОПТИМИЗИРОВАННАЯ проверка кликов - раз в 3 кадра
            if not hasattr(update, 'select_frame_counter'):
                update.select_frame_counter = 0

            update.select_frame_counter += 1
            if update.select_frame_counter % 3 == 0:  # Раз в 3 кадра
                if mouse.left:
                    check_mouse_click()


        # ВЫХОДИМ ИЗ UPDATE РАНО - не выполняем ВСЮ логику игры
        return

    # Конвертация снарядов
    if not hasattr(update, 'projectiles_converted'):
        convert_old_projectiles()
        update.projectiles_converted = True

    # Проверка падения
    if player.position.y < -5:
        print("⚠️ Игрок упал, телепортируем обратно!")
        player.position = Vec3(player.position.x, 5, player.position.z)
        if hasattr(player, 'velocity_y'):
            player.velocity_y = 0

    # Управление шейдером
    camera.set_shader_input("time", time.time())

    if shader_enabled:
        grenade_effect = max(0, grenade_effect - time.dt * 2)
        shoot_strength = max(0, shoot_strength - time.dt * 4)
        reload_strength = max(0, reload_strength - time.dt * 1.2)

        camera.set_shader_input("grenade_effect", grenade_effect)
        camera.set_shader_input("base_intensity", shader_intensity)
        camera.set_shader_input("shoot_strength", shoot_strength)
        camera.set_shader_input("reload_strength", reload_strength)
        camera.set_shader_input("walk_strength", walk_strength)
    else:
        camera.set_shader_input("base_intensity", 0.0)
        camera.set_shader_input("shoot_strength", 0.0)
        camera.set_shader_input("reload_strength", 0.0)
        camera.set_shader_input("walk_strength", 0.0)
        camera.set_shader_input("grenade_effect", 0.0)

    # Обновление анимаций стадий
    update_stage_animation()

    # Запуск стадий
    if not enemies_spawned_for_current_stage and not stage_animation["is_playing"]:
        update_stage()

    # Проверка завершения стадии
    check_stage_completion()

    # Полная очистка каждые 60 секунд
    if not hasattr(update, 'last_full_cleanup'):
        update.last_full_cleanup = time.time()

    if time.time() - update.last_full_cleanup > 60.0:
        hard_cleanup_all()
        update.last_full_cleanup = time.time()

    # Обновление HUD
    update_health_hud()
    update_explosion_shake()
    update_reload_animation()

    # Обновление игрока и врагов
    safe_update_enemies_optimized()
    show_coordinates_console()

    # Обновление оружия
    handle_shooting()

    # Проверка подбора предметов
    check_heal_pickup_collisions()
    update_weapon_hud()
    check_ammo_pickup_collisions()
    check_weapon_pickup_collisions()

    # Обновление анимации перезарядки
    if not is_reloading_anim:
        handle_shooting()

    # Отслеживание истории позиций для предсказания
    if not hasattr(player, 'last_position'):
        player.last_position = player.position
    if not hasattr(player, 'positions_history'):
        player.positions_history = []

    player.positions_history.append(Vec3(player.position))
    if len(player.positions_history) > 10:
        player.positions_history.pop(0)

    if is_sprinting:
        check_sprint_collisions()

    # Обновление эффектов
    update_shot_effects()

    # Изменение FOV для спринта
    if is_sprinting:
        camera.fov = 85
    else:
        camera.fov = 80

    # Обновление врагов и снарядов
    update_enemies()
    update_enemy_projectiles()
    check_bullet_hits()
    safe_update_effects()
    update_explosive_projectiles()

    # Проверка смерти игрока
    if player_health <= 0:
        player_health = 0

    player.last_position = player.position

    # Обновление эффекта оглушения
    if is_stunned:
        stun_effect_time += time.dt
        if stun_effect_time >= stun_effect_duration:
            is_stunned = False
            stun_effect_time = 0

    # Получаем базовые позиции оружия
    data = weapon_data[current_weapon]
    weapon_base_position = data["position"]
    weapon_base_rotation = data["rotation"]

    # Отставание оружия
    if not is_shooting and mouse.locked:
        current_mouse_movement = (mouse.velocity[0], mouse.velocity[1])

        if abs(current_mouse_movement[0]) > 0.001 or abs(current_mouse_movement[1]) > 0.001:
            mouse_movement = current_mouse_movement

            target_weapon_rotation = (
                weapon_base_rotation[0] - mouse_movement[1] * weapon_lag_intensity * 50,
                weapon_base_rotation[1] - mouse_movement[0] * weapon_lag_intensity * 50,
                weapon_base_rotation[2] - mouse_movement[0] * weapon_lag_intensity * 20
            )

            target_weapon_position = (
                weapon_base_position[0] - mouse_movement[0] * weapon_lag_position_intensity * 10,
                weapon_base_position[1] - mouse_movement[1] * weapon_lag_position_intensity * 5,
                weapon_base_position[2]
            )
        else:
            target_weapon_rotation = (
                lerp(target_weapon_rotation[0], weapon_base_rotation[0], time.dt * 2),
                lerp(target_weapon_rotation[1], weapon_base_rotation[1], time.dt * 2),
                lerp(target_weapon_rotation[2], weapon_base_rotation[2], time.dt * 3)
            )

            target_weapon_position = (
                lerp(target_weapon_position[0], weapon_base_position[0], time.dt * 3),
                lerp(target_weapon_position[1], weapon_base_position[1], time.dt * 3),
                lerp(target_weapon_position[2], weapon_base_position[2], time.dt * 3)
            )

        current_weapon_rotation = (
            lerp(current_weapon_rotation[0], target_weapon_rotation[0], time.dt * weapon_lag_speed),
            lerp(current_weapon_rotation[1], target_weapon_rotation[1], time.dt * weapon_lag_speed),
            lerp(current_weapon_rotation[2], target_weapon_rotation[2], time.dt * weapon_lag_speed * 1.5)
        )

        current_weapon_position = (
            lerp(current_weapon_position[0], target_weapon_position[0], time.dt * weapon_lag_speed),
            lerp(current_weapon_position[1], target_weapon_position[1], time.dt * weapon_lag_speed),
            lerp(current_weapon_position[2], target_weapon_position[2], time.dt * weapon_lag_speed)
        )

    # Анимация выстрела
    if is_shooting:
        shoot_animation_time += time.dt

        if shoot_animation_time < shoot_animation_duration:
            if shoot_animation_time < shoot_camera_kick_duration:
                kick_progress = shoot_animation_time / shoot_camera_kick_duration
                kick_power = shoot_camera_kick_intensity * (1 - kick_progress)
                camera.position = (0, 0, -kick_power)

            shake_progress = min(1.0, shoot_animation_time / shoot_camera_shake_duration)
            if shake_progress < 1.0:
                current_shake = shoot_camera_shake_intensity * (1 - shake_progress)

                high_freq_shake_x = math.sin(time.time() * 80) * current_shake * 0.3
                high_freq_shake_y = math.cos(time.time() * 75) * current_shake * 0.2
                low_freq_shake_x = math.sin(time.time() * 25) * current_shake * 0.7
                low_freq_shake_y = math.cos(time.time() * 20) * current_shake * 0.5

                total_shake_x = high_freq_shake_x + low_freq_shake_x
                total_shake_y = high_freq_shake_y + low_freq_shake_y

                if shoot_animation_time > shoot_camera_kick_duration:
                    return_progress = (shoot_animation_time - shoot_camera_kick_duration) / (
                            shoot_animation_duration - shoot_camera_kick_duration)
                    kick_return = shoot_camera_kick_intensity * (1 - return_progress)
                    camera.position = (
                        total_shake_x,
                        total_shake_y,
                        -kick_return
                    )

            if shoot_animation_time < shoot_camera_roll_duration:
                roll_progress = shoot_animation_time / shoot_camera_roll_duration
                roll_angle = shoot_camera_roll_intensity * (1 - roll_progress)
                camera.rotation_z = roll_angle
            else:
                roll_return_progress = (shoot_animation_time - shoot_camera_roll_duration) / (
                        shoot_animation_duration - shoot_camera_roll_duration)
                camera.rotation_z = shoot_camera_roll_intensity * (1 - roll_return_progress)

            weapon_bounce = math.sin(shoot_animation_time * 30) * 0.1 * (1 - shake_progress)

            weapon.position = (
                weapon_base_position[0],
                weapon_base_position[1] + weapon_bounce,
                weapon_base_position[2] - weapon_shoot_recoil * (1 - shake_progress)
            )

            current_weapon_rotation = weapon_base_rotation
            current_weapon_position = weapon_base_position
        else:
            is_shooting = False
            shoot_animation_time = 0

            if not is_firing_auto:
                camera.position = camera_base_position
                camera.rotation = (0, 0, 0)

    # Автоматическая стрельба
    if is_firing_auto and data["auto_fire"]:
        current_time = time.time()
        if current_time - last_fire_time >= data["fire_rate"]:
            ammo_type = weapon_data[current_weapon]["ammo_type"]
            ammo_info = ammo_data[ammo_type]
            if ammo_info['current_ammo'] > 0:
                perform_shot()
                last_fire_time = current_time
                shoot_strength = 1
            else:
                is_firing_auto = False

    # Движение и тряска
    if not is_reloading_anim:
        walking = held_keys['a'] or held_keys['d'] or held_keys['w'] or held_keys['s']
        running = held_keys['shift']

        if walking and player.grounded:
            if not is_moving:
                is_moving = True

            shake_timer += time.dt * 8
            speed_multiplier = 1.3 if running else 1.0

            body_sway_freq = 1.2
            step_freq = 3.5

            camera_body_sway_x = math.sin(shake_timer * body_sway_freq) * camera_body_sway_intensity * speed_multiplier
            camera_body_sway_y = math.cos(
                shake_timer * body_sway_freq * 0.9) * camera_body_sway_intensity * 0.5 * speed_multiplier
            camera_step_impact = abs(
                math.sin(shake_timer * step_freq)) * camera_step_impact_intensity * speed_multiplier

            weapon_shake_x = math.sin(
                shake_timer * body_sway_freq * 1.1) * weapon_body_sway_intensity * speed_multiplier
            weapon_shake_y = math.cos(
                shake_timer * body_sway_freq * 0.8) * weapon_body_sway_intensity * 0.4 * speed_multiplier
            weapon_step_impact = abs(
                math.sin(shake_timer * step_freq * 0.9)) * weapon_step_impact_intensity * speed_multiplier

            if not is_shooting:
                camera.position = (
                    camera_base_position[0] + camera_body_sway_x + current_explosion_shake[0],
                    camera_base_position[1] + camera_body_sway_y + camera_step_impact + current_explosion_shake[1],
                    camera_base_position[2] + current_explosion_shake[2]
                )

                camera.rotation = (
                    math.sin(shake_timer * 1.5) * 1.0 * speed_multiplier + current_explosion_tilt[0],
                    math.cos(shake_timer * 1.2) * 0.8 * speed_multiplier + current_explosion_tilt[1],
                    current_explosion_tilt[2]
                )

            if not is_shooting:
                weapon.position = (
                    current_weapon_position[0] + weapon_shake_x + current_explosion_shake[0] * 0.3,
                    current_weapon_position[1] + weapon_shake_y + (weapon_step_impact * 0.3) + current_explosion_shake[
                        1] * 0.3,
                    current_weapon_position[2] + current_explosion_shake[2] * 0.3
                )

                weapon.rotation = (
                    current_weapon_rotation[0] + math.sin(shake_timer * 1.2) * 0.5 * speed_multiplier +
                    current_explosion_tilt[0] * 0.5,
                    current_weapon_rotation[1] + math.cos(shake_timer * 0.9) * 0.3 * speed_multiplier +
                    current_explosion_tilt[1] * 0.5,
                    current_weapon_rotation[2] + current_explosion_tilt[2] * 0.5
                )
        else:
            if is_moving:
                is_moving = False
                if not is_shooting and not is_firing_auto:
                    camera.position = (
                        camera_base_position[0] + current_explosion_shake[0],
                        camera_base_position[1] + current_explosion_shake[1],
                        camera_base_position[2] + current_explosion_shake[2]
                    )

                    camera.rotation = (
                        current_explosion_tilt[0],
                        current_explosion_tilt[1],
                        current_explosion_tilt[2]
                    )

    # Звук шагов
    walking = held_keys['a'] or held_keys['d'] or held_keys['w'] or held_keys['s']
    if walking and player.grounded and not in_dialogue:
        if shader_enabled:
            walk_strength = 1
        if not walk.playing:
            walk.play()
    else:
        if walk.playing:
            walk.stop()

    # Диалоги
    if in_dialogue:
        press_e_text.enabled = False
        return

    if human_collider.hovered:
        press_e_text.enabled = True
    else:
        press_e_text.enabled = False


# ОБНОВЛЯЕМ ФУНКЦИЮ INPUT ДЛЯ ПРИОРИТЕТА ПЕРЕКЛЮЧЕНИЯ
def input(key):
    global in_dialogue, is_shooting, is_firing_auto, last_fire_time, is_sprinting, shoot_animation_time, shoot_strength, reload_strength, shader_enabled, is_selecting_weapon, weapon_selection_text

    if not game_started:
        # Обрабатываем только E для выбора оружия и ESC для выхода
        if key == 'e' and not is_selecting_weapon:
            if sword_on_table:
                distance_to_table = (player.position - start_table_position).length()
                if distance_to_table < pickup_radius:
                    switch_to_table_view()
                else:
                    print(f"❌ Подойдите ближе к столу! ({distance_to_table:.1f}/{pickup_radius})")
            return
        if key == 'c' and weapon_selection_ui:
            close_weapon_info()
            return
        if key == 'escape' and is_selecting_weapon:
            # Возвращаемся к обычной камере
            player.enabled = True
            mouse.locked = True
            is_selecting_weapon = False
            camera_mode = "player"

            if weapon_selection_text:
                destroy(weapon_selection_text)
                weapon_selection_text = None

            camera.animate_position(player_camera_position, duration=1.0, curve=curve.in_out_cubic)
            camera.animate_rotation(player_camera_rotation, duration=1.0, curve=curve.in_out_cubic)

            weapons_list = [sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table]
            for weapon_obj in weapons_list:
                if weapon_obj and hasattr(weapon_obj, 'original_color'):
                    weapon_obj.color = weapon_obj.original_color
            return

        # Другие клавиши не обрабатываем до начала игры
        return
    # ПЕРЕКЛЮЧЕНИЕ ОРУЖИЯ
    if key == '1':
        is_firing_auto = False  # ⬅️ ВАЖНО: сбрасываем автоматическую стрельбу
        is_shooting = False
        switch_weapon("assault_rifle")
        update_weapon_parameters()
        return

    if key == '2':
        is_firing_auto = False  # ⬅️ ВАЖНО: сбрасываем автоматическую стрельбу
        is_shooting = False
        switch_weapon("pistol")
        update_weapon_parameters()
        return
    if key == '3':
        is_firing_auto = False  # ⬅️ ВАЖНО: сбрасываем автоматическую стрельбу
        is_shooting = False
        switch_weapon("dual_uzi")
        update_weapon_parameters()
        return
    if key == '4':  # СЕКРЕТНОЕ ОРУЖИЕ - ГРАНАТОМЕТ
        is_firing_auto = False  # ⬅️ ВАЖНО: сбрасываем автоматическую стрельбу
        is_shooting = False
        switch_weapon("grenade_launcher")
        update_weapon_parameters()
        print("🚀 Активирован гранатомет!")
        return

    # ПЕРЕЗАРЯДКА ПО КЛАВИШЕ R
    if key == 'r' and not is_reloading_anim:
        is_firing_auto = False  # ⬅️ ВАЖНО: сбрасываем автоматическую стрельбу при перезарядке
        reload_weapon()
        return

    # ОСТАЛЬНАЯ ЛОГИКА ТОЛЬКО ЕСЛИ НЕ БЫЛО ПЕРЕКЛЮЧЕНИЯ ОРУЖИЯ
    # НАЧАЛО СТРЕЛЬБЫ - РАЗНЫЕ РЕЖИМЫ ДЛЯ РАЗНОГО ОРУЖИЯ
    data = weapon_data[current_weapon]

    # НАЧАЛО СТРЕЛЬБЫ
    if key == 'left mouse down':
        if data["auto_fire"]:
            # Автоматическая стрельба для автомата - начинаем стрельбу
            is_firing_auto = True
            last_fire_time = time.time() - auto_fire_delay  # ⬅️ ИСПРАВЛЕНИЕ: сразу можем стрелять
            print(f"🔫 Начата автоматическая стрельба из {current_weapon}!")
        else:
            # Полуавтоматическая стрельба для пистолета - один выстрел
            perform_shot()  # ⬅️ ИСПРАВЛЕНИЕ: сразу делаем выстрел
            print(f"🔫 Выстрел из {current_weapon}!")

    # ОКОНЧАНИЕ СТРЕЛЬБЫ (только для автоматического оружия)
    if key == 'left mouse up':
        if data["auto_fire"]:
            is_firing_auto = False
            print(f"🔫 Автоматическая стрельба из {current_weapon} остановлена")

    # ОБРАБОТКА БЕГА
    if key == 'shift':
        is_sprinting = True
        player.speed = sprint_speed
        print("Спринт активирован!")

    if key == 'shift up':
        is_sprinting = False
        player.speed = normal_speed
        print("Спринт деактивирован!")

    # if key == 'e' and human_collider.hovered and not in_dialogue:
    #     in_dialogue = True
    #     dialogue_bg.enabled = True
    #     npc_name.text = "Человек"
    #     npc_line.text = "Привет! Рад тебя видеть. Что скажешь?"
    #     button1.enabled = True
    #     button2.enabled = True
    #     press_e_text.enabled = False
    #     player.enabled = False

    # if key == '1' and in_dialogue:
    #     close_dialogue()
    # if key == '2' and in_dialogue:
    #     close_dialogue()
    if key == 'q':
        quit()

    if key == 'space':
        if not jump.playing:
            jump.play()

    if key == 'shift':
        is_sprinting = True
        # Увеличиваем скорость игрока
        player.speed = sprint_speed
        print("Спринт активирован!")
    if key == 'p':
        print("💊 Принудительный респавн аптечек!")

    if key == 'shift up':
        is_sprinting = False
        # Возвращаем обычную скорость
        player.speed = normal_speed
        print("Спринт деактивирован!")
    if key == 'o':
        print("🔫 Принудительный респавн патронов!")

    if key == 'n':  # клавиша ]
        shader_enabled = True

        print("🔴 Шейдер ВКЛЮЧЕН")

    if key == 'm':  # клавиша [
        shader_enabled = False

        print("⚪ Шейдер ВЫКЛЮЧЕН")

    if key == 'f6':
        debug_memory()
    if key == 'h':
        hard_cleanup_all()
    if key == 'f5':  # Ручная очистка
        cleaned = safe_render_cleanup()
        print(f"🧹 Ручная очистка: {cleaned} объектов")
    # if key == 'e' and not game_started and not is_selecting_weapon:
    #     if sword_on_table:  # Проверяем что стол создан
    #         distance_to_table = (player.position - start_table_position).length()
    #         if distance_to_table < pickup_radius:
    #             switch_to_table_view()
    #         else:
    #             print(f"❌ Подойдите ближе к столу! ({distance_to_table:.1f}/{pickup_radius})")
    #     return
    #
    #     # ВЫХОД ИЗ РЕЖИМА ВЫБОРА (ESC)
    # if key == 'escape' and is_selecting_weapon and not game_started:
    #     # Возвращаемся к обычной камере
    #     player.enabled = True
    #     mouse.locked = True
    #     is_selecting_weapon = False
    #     camera_mode = "player"
    #
    #     # Убираем текст выбора
    #     if weapon_selection_text:
    #         destroy(weapon_selection_text)
    #         weapon_selection_text = None
    #
    #     # Возвращаем камеру к игроку
    #     camera.animate_position(player_camera_position, duration=1.0, curve=curve.in_out_cubic)
    #     camera.animate_rotation(player_camera_rotation, duration=1.0, curve=curve.in_out_cubic)
    #
    #     # Возвращаем оригинальные цвета оружиям
    #     weapons = [sword_on_table, axe_on_table, copie_on_table, main_weapon_on_table]
    #     for weapon in weapons:
    #         if weapon and hasattr(weapon, 'original_color'):
    #             weapon.color = weapon.original_color
    #
    #     return


def close_dialogue():
    global in_dialogue
    dialogue_bg.enabled = False
    button1.enabled = False
    button2.enabled = False
    in_dialogue = False
    press_e_text.enabled = False
    player.enabled = True


button1.on_click = close_dialogue
button2.on_click = close_dialogue

# ==================== ИНИЦИАЛИЗАЦИЯ ИГРЫ ====================

print("🎮 Инициализация игры...")

# Создаем стартовую сцену с оружием
create_start_scene()

# Инициализируем оружия (но они будут скрыты до начала игры)
init_weapons()

# Скрываем все оружия - они появятся только после начала игры
for weapon_type in weapons:
    weapons[weapon_type].enabled = False

# Инициализируем оптимизированные системы
init_optimized_systems()

print("✅ Игра готова! Спускайтесь к оружию и нажмите E")
print(f"📍 Ваша позиция: {player.position}")
print(f"📍 Оружие внизу на позиции: (0, 0, 0)")

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    app.run()