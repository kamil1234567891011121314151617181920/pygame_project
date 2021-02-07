import os
from random import choice
import pygame
import pyganim

TILE_SIDE = 50
SIZE = WIDTH, HEIGHT = 750, 750
FPS = 30
GRAVITY = 10 / FPS

pygame.init()
screen = pygame.display.set_mode(SIZE)


def cut_sheet(filename, rows, cols, anim_delay):
    sheet: pygame.Surface = load_image(filename)
    picture_w, picture_h = sheet.get_width() // cols, sheet.get_height() // rows
    frames = []
    for y in range(rows):
        for x in range(cols):
            frame_location = (picture_w * x, picture_h * y)
            frames.append((sheet.subsurface(frame_location,
                                            (picture_w, picture_h)),
                           anim_delay))

    return frames


def load_image(name, color_key=None):
    """Загрузка изображения"""
    fullname = os.path.join('data', name)
    # если файл не существует, то выходим
    if not os.path.isfile(fullname):
        raise SystemExit(f"Файл с изображением '{fullname}' не найден")
    image = pygame.image.load(fullname)
    if color_key is not None:
        image = image.convert()
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    else:
        image = image.convert_alpha()
    return image


def load_level(filename):
    """Загрузка уровня"""
    filename = os.path.join('data', filename)
    # если файл не существует, то выходим
    if not os.path.isfile(filename):
        raise SystemExit(f"Файл с картой '{filename}' не найден")

    with open(filename, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]
    new_player, x, y = None, None, None
    for y, row in enumerate(level_map):
        for x, elem in enumerate(row):
            if elem == '-':
                Platform(x * TILE_SIDE, y * TILE_SIDE)
            elif elem == '.':
                Spikes(x * TILE_SIDE, y * TILE_SIDE)
            elif elem == '*':
                Fruit(x * TILE_SIDE, y * TILE_SIDE)
            elif elem == '@':
                new_player = NinjaFrog(x * TILE_SIDE - 18,
                                       y * TILE_SIDE + 18, 5)

    return new_player, (x + 1) * TILE_SIDE, (y + 1) * TILE_SIDE


class BaseHero(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__(all_sprites)

        self.width, self.height = width, height

        self.start_x, self.start_y = x, y
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.image = pygame.Surface((self.width, self.height))
        self.x_vel, self.y_vel = None, None
        self.on_ground = False

    def update(self):
        self.image.fill('black')
        self.image.set_colorkey('black')

    def get_position(self):
        return self.rect.x, self.rect.y


class NinjaFrog(BaseHero):
    width, height = 32, 32

    animations = {'hit': pyganim.PygAnimation(cut_sheet(
        'Ninja Frog/Hit (32x32).png', 1, 7, anim_delay=100)),

        'jump': pyganim.PygAnimation(cut_sheet(
            'Ninja Frog/Jump (32x32).png', 1, 1, anim_delay=100)),

        'double_jump': pyganim.PygAnimation(cut_sheet(
            'Ninja Frog/Double Jump (32x32).png', 1, 6, anim_delay=100)),

        'fall': pyganim.PygAnimation(cut_sheet(
            'Ninja Frog/Fall (32x32).png', 1, 1, anim_delay=100)),

        'run': pyganim.PygAnimation(cut_sheet(
            'Ninja Frog/Run (32x32).png', 1, 12, anim_delay=100)),

        'stay': pyganim.PygAnimation(cut_sheet(
            'Ninja Frog/Idle (32x32).png', 1, 11, anim_delay=100))
    }

    for anim in animations.values():
        anim.play()

    def __init__(self, x, y, speed):
        super().__init__(x, y, NinjaFrog.width, NinjaFrog.height)
        self.direction = "right"
        self.speed = speed
        self.jump, self.x_vel, self.y_vel = 0, 0, 0
        self.height_jump = 10  # показатель высоты прыжка
        self.attack = False  # происходит ли сейчас атака
        self.double_jump = False  # происходит ли сейчас двойной прыжок
        self.got_hit = False
        self.health = 100

        # время последнего столкновения с шипами (мс)
        self.last_collide_with_spikes = pygame.time.get_ticks()

        self.mask = pygame.mask.from_surface(self.image)

    def flip(self):
        """Разворот всех анимаций спрайтов"""
        for anim in NinjaFrog.animations.values():
            anim.flip(True, False)

    def collide(self, x_vel, y_vel):
        """Обработка столкновений с платформами, фруктами"""

        # Обработка столкновений с платформами
        for platform in pygame.sprite.spritecollide(self, platforms, False):
            if x_vel < 0:
                self.rect.left = platform.rect.right
                self.x_vel = 0
            elif x_vel > 0:
                self.rect.right = platform.rect.left
                self.x_vel = 0
            elif y_vel > 0:
                self.on_ground = True
                self.jump = False
                self.rect.bottom = platform.rect.top
                self.y_vel = 0
            elif y_vel < 0:
                self.rect.top = platform.rect.bottom
                self.y_vel = 0

        # Обработка столкновений с фруктами (взятие фрукта)
        for fruit in fruits_group:
            fruit: Fruit
            if pygame.sprite.collide_mask(self, fruit):
                self.health += fruit.get_health()
                print(self.health)  # для отладки
                fruit.collect()  # Собрать фрукт

    def collide_with_spikes(self):
        # Обработка столкновений с шипами
        for spike in spikes_group:
            spike: Spikes
            if pygame.sprite.collide_mask(self, spike):
                self.health -= spike.get_damage()
                print(self.health)  # для отладки
                if self.health <= 0:
                    self.defeat()
                    break

                self.got_hit = pygame.time.get_ticks()  # Время последнего удара

                # Изменение векторов скоростей в соответствии со старыми
                self.x_vel = 0 if self.x_vel == 0 else (-5 if self.x_vel > 0 else 5)
                self.y_vel = 0 if self.y_vel == 0 else (-8 if self.y_vel > 0 else 8)

    def update(self):
        super().update()

        if not self.health:  # герой повержен
            self.rect.y += 5
            NinjaFrog.animations['stay'].blit(self.image, (0, 0))
            return

        # флаг, нужна ли ещё анимация в текущем обновлении
        flag_anim = True  # нужно, чтобы не было двойной анимации

        if not self.on_ground:
            self.y_vel += GRAVITY
        else:
            self.y_vel = 1
            self.on_ground = False

        self.collide_with_spikes()  # Проверка на столкновение с шипами

        # Вынес по отдельности проверку на столкновение для каждой координаты, потому что
        # метод collide не должен изменять координаты, он лишь меняет вектор скорости
        self.rect.x += self.x_vel
        self.collide(self.x_vel, 0)  # По-отдельности определяем вектор скорости по x

        self.rect.y += self.y_vel
        self.collide(0, self.y_vel)  # По-отдельности определяем вектор скорости по y

        # Если игрок попал на шипы, то на протяжении 700 мс проигрывается анимация
        if self.got_hit and pygame.time.get_ticks() - self.got_hit < 700:
            NinjaFrog.animations['hit'].play()
            NinjaFrog.animations['hit'].blit(self.image, (0, 0))
            return
        else:
            self.got_hit = False  # Анимация прошла
            NinjaFrog.animations['hit'].stop()

        if self.double_jump:
            NinjaFrog.animations['double_jump'].blit(self.image, (0, 0))
            flag_anim = False
            if NinjaFrog.animations['double_jump'].currentFrameNum == \
                    NinjaFrog.animations['double_jump'].numFrames - 1:
                self.double_jump = False

        if pygame.key.get_pressed()[pygame.K_RIGHT]:
            self.x_vel = self.speed
            if self.direction == "left":
                self.direction = "right"
                self.flip()
            if flag_anim:
                NinjaFrog.animations['run'].blit(self.image, (0, 0))
                flag_anim = False

        elif pygame.key.get_pressed()[pygame.K_LEFT]:
            self.x_vel = -self.speed

            if self.direction == "right":
                self.direction = "left"
                self.flip()
            if flag_anim:
                NinjaFrog.animations['run'].blit(self.image, (0, 0))
                flag_anim = False

        if flag_anim:  # нет передвижения по оси x
            self.x_vel = 0

        if pygame.key.get_pressed()[pygame.K_UP]:
            if self.on_ground:
                self.on_ground = False
                self.y_vel = -self.height_jump
            if flag_anim:
                NinjaFrog.animations['jump'].blit(self.image, (0, 0))
                flag_anim = False

        if pygame.key.get_pressed()[pygame.K_DOWN]:
            # Не было проверки на то, что гг стоит на земле при нажатии "вниз"
            if not self.on_ground:
                self.y_vel = 2 * self.height_jump
                if flag_anim:
                    NinjaFrog.animations['fall'].blit(self.image, (0, 0))
                    flag_anim = False

        if pygame.key.get_pressed()[pygame.K_RETURN] and not self.double_jump:
            self.attack = True
            NinjaFrog.animations['hit'].play()
            if flag_anim:
                NinjaFrog.animations['hit'].blit(self.image, (0, 0))
                flag_anim = False

        if pygame.key.get_pressed()[pygame.K_SPACE] \
                and not pygame.key.get_pressed()[pygame.K_DOWN]:
            if self.on_ground:
                self.on_ground = False
                self.y_vel = -1.4 * self.height_jump
                self.double_jump = True
                NinjaFrog.animations['double_jump'].play()
                if flag_anim:
                    NinjaFrog.animations['double_jump'].blit(self.image,
                                                             (0, 0))
                    flag_anim = False

        if pygame.key.get_pressed()[pygame.K_f]:
            self.defeat()

        if flag_anim:  # все клавиши не нажаты
            # Когда клавиши не нажаты и герой на земле, то анимация stay
            if self.on_ground:
                NinjaFrog.animations['stay'].blit(self.image, (0, 0))
            # когда в воздухе и падает анимация падения
            elif self.y_vel >= 0:
                NinjaFrog.animations['fall'].blit(self.image, (0, 0))
            # когда поднимается - анимация прыжка
            else:
                NinjaFrog.animations['jump'].blit(self.image, (0, 0))

    def defeat(self):
        """Поражение героя"""
        self.health = 0  # чтобы здоровье не было отрицательным
        NinjaFrog.animations['stay'].flip(False, True)


class Platform(pygame.sprite.Sprite):
    """Платформы"""

    def __init__(self, x, y):
        super().__init__(platforms, all_sprites)

        self.image = pygame.transform.scale(load_image('grass.png'),
                                            (TILE_SIDE, TILE_SIDE))

        self.width, self.height = self.image.get_size()

        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y


class Spikes(pygame.sprite.Sprite):
    """Шипы"""

    def __init__(self, x, y):
        super().__init__(spikes_group, all_sprites)

        self.image = pygame.transform.scale(load_image('spikes.png'),
                                            (TILE_SIDE, TILE_SIDE))

        self.width, self.height = self.image.get_size()

        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = x, y
        self.mask = pygame.mask.from_surface(self.image)
        # урон, который получит персонаж, если ударится о шипы
        self.damage = 30

    def get_damage(self):
        return self.damage


class Fruit(pygame.sprite.Sprite):
    """Фрукты (прибавляют игроку жизни)"""

    width, height = 32, 32

    fruits = ['Apple', 'Bananas', 'Cherries', 'Melon',
              'Kiwi', 'Pineapple', 'Strawberry', 'Orange']

    def __init__(self, x, y):
        super().__init__(fruits_group, all_sprites)

        self.rect = pygame.Rect(x, y, Fruit.width, Fruit.height)
        self.image = pygame.Surface((Fruit.width, Fruit.height))
        self.collected = False

        # каждый раз случайный фрукт
        self.anim_normal = pyganim.PygAnimation(cut_sheet(
            f'Fruits/{choice(Fruit.fruits)}.png', 1, 17, anim_delay=100))
        self.anim_normal.play()

        self.anim_collected = pyganim.PygAnimation(cut_sheet(
            f'Fruits/Collected.png', 1, 6, anim_delay=100))

        # кол-во жизней, которое получит герой, если возьмёт фрукт
        self.health = 10

    def update(self):
        self.image.fill('black')
        self.image.set_colorkey('black')

        if not self.collected:  # Если не собран, обычная анимация
            self.anim_normal.blit(self.image, (0, 0))
        elif self.anim_collected.currentFrameNum == \
                self.anim_collected.numFrames - 1:
            # Если собран и анимация подходит к концу, спрайт удаляется
            self.anim_collected.stop()
            self.kill()
        else:
            self.anim_collected.blit(self.image, (0, 0))

    def collect(self):
        """Фрукт собран"""

        self.collected = True
        self.anim_collected.play()

    def get_health(self):
        return self.health


class Camera:
    def __init__(self, width, height):
        self.view = pygame.Rect(0, 0, width, height)

    def apply(self, obj):
        """Сдвинуть объект obj на смещение камеры"""
        return obj.rect.move(self.view.topleft)

    def update(self, target):
        """Позиционировать камеру на объекте target"""
        self.view = self.set_camera(target)

    def set_camera(self, target):
        left, top, _, _ = target.rect
        _, _, width, height = self.view

        left, top = WIDTH / 2 - left, HEIGHT / 2 - top

        left = max(WIDTH - width, min(0, left))
        top = min(0, max(HEIGHT - height, top))

        return pygame.Rect(left, top, width, height)


if __name__ == "__main__":
    running = True
    clock = pygame.time.Clock()

    # группы спрайтов
    all_sprites = pygame.sprite.Group()
    fruits_group = pygame.sprite.Group()
    spikes_group = pygame.sprite.Group()
    platforms = pygame.sprite.Group()

    player, level_x, level_y = load_level('map.txt')

    camera = Camera(level_x, level_y)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(pygame.Color("light blue"))
        all_sprites.update()

        if player.health:
            # изменяем ракурс камеры
            camera.update(player)
        # обновляем положение всех спрайтов
        for sprite in all_sprites:
            screen.blit(sprite.image, camera.apply(sprite))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()