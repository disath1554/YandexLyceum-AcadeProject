import arcade
import random
from enum import Enum
from dataclasses import dataclass, field
import math
import os

SCREEN_WIDTH = 1300
SCREEN_HEIGHT = 768
TITLE = "Kolobok Knight"

TILE_SIZE = 64
MAP_WIDTH = 50
MAP_HEIGHT = 40

ROOM_MIN_SIZE = 5
ROOM_MAX_SIZE = 12
MAX_ROOMS = 15

STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
IMAGES_PATH = os.path.join(STATIC_PATH, "images")
SOUNDS_PATH = os.path.join(STATIC_PATH, "sounds")


def get_image_path(filename):
    return os.path.join(IMAGES_PATH, filename)


def get_sound_path(filename):
    return os.path.join(SOUNDS_PATH, filename)


def ensure_directories():
    os.makedirs(IMAGES_PATH, exist_ok=True)
    os.makedirs(SOUNDS_PATH, exist_ok=True)


def draw_texture_at(texture, center_x, center_y, width, height):
    try:
        arcade.draw_texture_rect(
            texture,
            arcade.LBWH(center_x - width/2, center_y - height/2, width, height)
        )
    except (AttributeError, TypeError):
        try:
            arcade.draw_texture_rect(
                texture,
                arcade.rect.LBWH(center_x - width/2, center_y - height/2, width, height)
            )
        except (AttributeError, TypeError):
            try:
                arcade.draw_texture_rectangle(center_x, center_y, width, height, texture)
            except:
                pass


class TileType(Enum):
    WALL = 0
    FLOOR = 1
    STAIRS = 2
    DOOR = 3


class ItemType(Enum):
    HEALTH_POTION = "health_potion"
    MANA_POTION = "mana_potion"
    SWORD = "sword"
    SHIELD = "shield"
    SCROLL_FIREBALL = "scroll_fireball"
    SCROLL_TELEPORT = "scroll_teleport"
    GOLD = "gold"


class HeroClass(Enum):
    WARRIOR = ("Колобок", 100, 50, 15, 0, 5)
    MAGE = ("Бабка ведьма", 70, 100, 8, 15, 10)
    ROGUE = ("Дед Разбойник", 90, 50, 12, 0, 5)
    
    def __init__(self, title, hp, mana, attack, magic, defense):
        self.title = title
        self.base_hp = hp
        self.base_mana = mana
        self.base_attack = attack
        self.base_magic = magic
        self.base_defense = defense


@dataclass
class Room:
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self):
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def inner(self):
        return (self.x + 1, self.y + 1, self.x + self.width - 1, self.y + self.height - 1)
    
    def intersects(self, other):
        return (self.x <= other.x + other.width + 1 and
                self.x + self.width + 1 >= other.x and
                self.y <= other.y + other.height + 1 and
                self.y + self.height + 1 >= other.y)


@dataclass
class Item:
    x: int
    y: int
    item_type: ItemType
    name: str
    value: int
    rarity: int = 1
    sprite: arcade.Sprite = None
    
    def get_color(self):
        rarity_colors = {
            1: arcade.color.WHITE,
            2: arcade.color.GREEN,
            3: arcade.color.BLUE,
            4: arcade.color.PURPLE,
            5: arcade.color.ORANGE,
        }
        return rarity_colors.get(self.rarity, arcade.color.WHITE)
    
    def get_symbol(self):
        symbols = {
            ItemType.HEALTH_POTION: "+",
            ItemType.MANA_POTION: "*",
            ItemType.SWORD: "/",
            ItemType.SHIELD: "O",
            ItemType.SCROLL_FIREBALL: "~",
            ItemType.SCROLL_TELEPORT: "?",
            ItemType.GOLD: "$",
        }
        return symbols.get(self.item_type, "?")


@dataclass
class Enemy:
    x: int
    y: int
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    exp_value: int
    symbol: str
    color: tuple
    is_boss: bool = False
    sprite: arcade.Sprite = None
    
    def is_alive(self):
        return self.hp > 0


@dataclass
class Player:
    x: int
    y: int
    hero_class: HeroClass
    hp: int = 0
    max_hp: int = 0
    mana: int = 0
    max_mana: int = 0
    attack: int = 0
    defense: int = 0
    magic: int = 0
    level: int = 1
    exp: int = 0
    exp_to_next: int = 100
    gold: int = 0
    inventory: list = field(default_factory=list)
    equipped: dict = field(default_factory=dict)
    sprite: arcade.Sprite = None
    
    def __post_init__(self):
        self.max_hp = self.hero_class.base_hp
        self.hp = self.max_hp
        self.max_mana = self.hero_class.base_mana * 2
        self.mana = self.hero_class.base_mana
        self.attack = self.hero_class.base_attack
        self.defense = self.hero_class.base_defense
        self.magic = self.hero_class.base_magic
        self.equipped = {'weapon': None,  'shield': None}
    
    def gain_exp(self, amount):
        self.exp += amount
        leveled_up = False
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level_up()
            leveled_up = True
        return leveled_up
    
    def level_up(self):
        self.level += 1
        self.exp_to_next = int(self.exp_to_next * 1.5)
        hp_gain = random.randint(5, 15)
        mana_gain = random.randint(3, 10)
        self.max_hp += hp_gain
        self.hp = min(self.hp + hp_gain, self.max_hp)
        self.max_mana += mana_gain
        self.mana = min(self.mana + mana_gain, self.max_mana)
        self.attack += random.randint(1, 3)
        self.defense += random.randint(1, 2)
        self.magic += random.randint(1, 3)
    
    def get_total_attack(self):
        bonus = 0
        if self.equipped['weapon']:
            bonus += self.equipped['weapon'].value
        return self.attack + bonus
    
    def get_total_defense(self):
        bonus = 0
        if self.equipped['shield']:
            bonus += self.equipped['shield'].value
        return self.defense + bonus
    
    def is_alive(self):
        return self.hp > 0


class DungeonGenerator:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[TileType.WALL for _ in range(height)] for _ in range(width)]
        self.rooms = []
        self.explored = [[False for _ in range(height)] for _ in range(width)]
        self.visible = [[False for _ in range(height)] for _ in range(width)]
    
    def generate(self, dungeon_level):
        self.tiles = [[TileType.WALL for _ in range(self.height)] for _ in range(self.width)]
        self.rooms = []
        
        for _ in range(MAX_ROOMS):
            w = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            h = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            x = random.randint(1, self.width - w - 2)
            y = random.randint(1, self.height - h - 2)
            
            new_room = Room(x, y, w, h)
            
            if not any(new_room.intersects(other) for other in self.rooms):
                self._create_room(new_room)
                
                if self.rooms:
                    prev_center = self.rooms[-1].center
                    new_center = new_room.center
                    
                    if random.random() < 0.5:
                        self._create_h_tunnel(prev_center[0], new_center[0], prev_center[1])
                        self._create_v_tunnel(prev_center[1], new_center[1], new_center[0])
                    else:
                        self._create_v_tunnel(prev_center[1], new_center[1], prev_center[0])
                        self._create_h_tunnel(prev_center[0], new_center[0], new_center[1])
                
                self.rooms.append(new_room)
        
        if self.rooms:
            last_room = self.rooms[-1]
            cx, cy = last_room.center
            self.tiles[cx][cy] = TileType.STAIRS
        
        return self.rooms[0].center if self.rooms else (self.width // 2, self.height // 2)
    
    def _create_room(self, room):
        x1, y1, x2, y2 = room.inner
        for x in range(x1, x2):
            for y in range(y1, y2):
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.tiles[x][y] = TileType.FLOOR
    
    def _create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.tiles[x][y] = TileType.FLOOR
    
    def _create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.tiles[x][y] = TileType.FLOOR
    
    def is_walkable(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[x][y] in [TileType.FLOOR, TileType.STAIRS, TileType.DOOR]
        return False
    
    def compute_fov(self, player_x, player_y, radius=8):
        self.visible = [[False for _ in range(self.height)] for _ in range(self.width)]
        
        for angle in range(360):
            rad = math.radians(angle)
            dx = math.cos(rad)
            dy = math.sin(rad)
            x, y = float(player_x), float(player_y)
            
            for _ in range(radius):
                ix, iy = int(x), int(y)
                
                if 0 <= ix < self.width and 0 <= iy < self.height:
                    self.visible[ix][iy] = True
                    self.explored[ix][iy] = True
                    
                    if self.tiles[ix][iy] == TileType.WALL:
                        break
                else:
                    break
                
                x += dx
                y += dy


class GameState(Enum):
    MENU = "menu"
    CLASS_SELECT = "class_select"
    TUTORIAL = "tutorial"
    PLAYING = "playing"
    INVENTORY = "inventory"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    PAUSED = "paused"


class TutorialPage(Enum):
    CONTROLS = 1
    ENEMIES = 2
    ITEMS = 3
    LORE = 0


class MessageLog:
    def __init__(self, max_messages=6):
        self.messages = []
        self.max_messages = max_messages
    
    def add(self, text, color=arcade.color.WHITE):
        self.messages.append((text, color))
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
    
    def clear(self):
        self.messages = []


class TextureManager:
    def __init__(self):
        self.textures = {}
        self.use_sprites = False
        self._load_textures()
    
    def _load_textures(self):
        texture_files = {
            'player': ['player.png', 'player.jpg'],
            'wall': ['wall.png', 'wall.jpg'],
            'floor': ['floor.png', 'floor.jpg'],
            'box': ['box.png', 'box.jpg'],
            'stairs': ['stairs.png', 'stairs.jpg'],
            'hare': ['hare.png', 'hare.jpg'],
            'fox': ['fox.png', 'fox.jpg'],
            'skeleton': ['skeleton.png', 'skeleton.jpg'],
            'wolf': ['wolf.png', 'wolf.jpg'],
            'punk': ['punk.png', 'punk.jpg'],
            'fish': ['fish.png', 'fish.jpg'],
            'bear': ['bear.png', 'bear.jpg'],
            'mage': ['mage.png', 'mage.jpg'],
            'health_potion': ['health_potion.png', 'health_potion.jpg'],
            'mana_potion': ['mana_potion.png', 'mana_potion.jpg'],
            'star_gray': ['star_gray.png', 'star_gray.jpg'],
            'star_gold': ['star_gold.png', 'star_gold.jpg'],
            'sword': ['sword.png', 'sword.jpg'],
            'shield': ['shield.png', 'shield.jpg'],
            'gold': ['gold.png', 'gold.jpg'],
            'scroll_fireball': ['scroll_fireball.png', 'scroll_fireball.jpg'],
            'scroll_teleport': ['scroll_teleport.png', 'scroll_teleport.jpg'],
            'menu_bg': ['menu_bg.jpg', 'menu_bg.png', 'background.jpg', 'background.png', 'bg.jpg', 'bg.png'],
        }
        
        for name, filenames in texture_files.items():
            for filename in filenames:
                path = get_image_path(filename)
                if os.path.exists(path):
                    try:
                        self.textures[name] = arcade.load_texture(path)
                        self.use_sprites = True
                        break
                    except:
                        pass
    
    def get(self, name):
        return self.textures.get(name)
    
    def has(self, name):
        return name in self.textures


class MusicManager:
    def __init__(self):
        self.current_music = None
        self.music_player = None
        self.volume = 0.5
        self.current_file = None
        
    def play(self, filename):
        if self.current_file == filename and self.music_player:
            return
            
        self.stop()
        
        possible_names = [filename]
        if filename == "колобок.mp3":
            possible_names.extend(["меню.mp3", "menu.ogg", "menu.wav"])
        elif filename == "game.mp3":
            possible_names.extend(["игра.mp3", "game.ogg", "game.wav", "battle.mp3"])
        
        path = None
        for name in possible_names:
            test_path = get_sound_path(name)
            if os.path.exists(test_path):
                path = test_path
                break
        
        if not path:
            return
        
        try:
            self.current_music = arcade.load_sound(path)
            
            if self.current_music:
                try:
                    self.music_player = self.current_music.play(volume=self.volume, loop=True)
                except (TypeError, AttributeError):
                    try:
                        self.music_player = arcade.play_sound(self.current_music, volume=self.volume)
                    except:
                        return
                
                self.current_file = filename
        except:
            pass
    
    def stop(self):
        if self.music_player:
            try:
                self.music_player.pause()
            except AttributeError:
                try:
                    arcade.stop_sound(self.music_player)
                except:
                    pass
            self.music_player = None
        self.current_file = None
    
    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.music_player:
            try:
                self.music_player.volume = self.volume
            except:
                pass


class DungeonRogue(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, TITLE)
        self.background_color = arcade.color.BLACK
        
        ensure_directories()
        
        self.state = GameState.MENU
        self.dungeon = None
        self.player = None
        self.enemies = []
        self.items = []
        self.dungeon_level = 1
        self.max_dungeon_level = 8
        self.message_log = MessageLog()
        self.camera_x = 0
        self.camera_y = 0
        self.selected_class_index = 0
        self.selected_inventory_index = 0
        self.particle_effects = []
        self.turn_count = 0
        
        self.tutorial_page = TutorialPage.CONTROLS
        self.selected_hero_class = None
        
        self.textures = TextureManager()
        self.music = MusicManager()
        self.current_music_state = None
        
    def setup(self):
        self.dungeon_level = 1
        self.message_log.clear()
        self.enemies = []
        self.items = []
        self.particle_effects = []
        self.turn_count = 0
        self._update_music()
    
    def _update_music(self):
        if self.state in [GameState.MENU, GameState.CLASS_SELECT, GameState.TUTORIAL]:
            if self.current_music_state != "menu":
                self.music.play("kolobok.mp3")
                self.current_music_state = "menu"
        elif self.state in [GameState.PLAYING, GameState.INVENTORY, GameState.PAUSED]:
            if self.current_music_state != "game":
                self.music.play("game.mp3")
                self.current_music_state = "game"
    
    def _get_enemy_texture_name(self, enemy_name):
        name_map = {
            'Заяц': 'hare',
            'Волк': 'wolf',
            'Медведь': 'bear',
            'Лиса': 'fox',
            'Скелет': 'skeleton',
            'Тыква': 'punk',
        }
        return name_map.get(enemy_name, 'goblin')
    
    def _get_item_texture_name(self, item_type):
        type_map = {
            ItemType.HEALTH_POTION: 'health_potion',
            ItemType.MANA_POTION: 'mana_potion',
            ItemType.SWORD: 'sword',
            ItemType.SHIELD: 'shield',
            ItemType.GOLD: 'gold',
            ItemType.SCROLL_FIREBALL: 'scroll_fireball',
            ItemType.SCROLL_TELEPORT: 'scroll_teleport',
        }
        return type_map.get(item_type, 'gold')
    
    def start_new_game(self, hero_class):
        self.setup()
        self.dungeon = DungeonGenerator(MAP_WIDTH, MAP_HEIGHT)
        start_pos = self.dungeon.generate(self.dungeon_level)
        
        self.player = Player(x=start_pos[0], y=start_pos[1], hero_class=hero_class)
        
        if self.textures.has('player'):
            self.player.sprite = arcade.Sprite()
            self.player.sprite.texture = self.textures.get('player')
            self.player.sprite.width = TILE_SIZE
            self.player.sprite.height = TILE_SIZE
        
        self._spawn_enemies()
        self._spawn_items()
        
        self.dungeon.compute_fov(self.player.x, self.player.y)
        self.state = GameState.PLAYING
        self._update_music()
        
        self.message_log.add(f"{self.player.hero_class.title} входит в подземелье!", arcade.color.GOLD)
        self.message_log.add("Найдите лестницу, чтобы спуститься глубже...", arcade.color.GRAY)
    
    def _spawn_enemies(self):
        self.enemies = []
        enemy_types = [
            ("Заяц", 15, 4, 1, 10, "h", arcade.color.LIGHT_GRAY),
            ("Волк", 25, 6, 2, 20, "w", arcade.color.LIGHT_GREEN),
            ("Медведь", 40, 10, 4, 40, "b", arcade.color.LIGHT_BLUE),
            ("Лиса", 30, 8, 3, 30, "f", arcade.color.LIGHT_CORAL),
            ("Скелет", 50, 7, 2, 35, "s", arcade.color.LIGHT_GRAY),
            ("Тыква", 45, 18, 3, 55, "p", arcade.color.ORANGE),
            ("Шука", 80, 20, 8, 80, "F", arcade.color.LIGHT_CORAL),
        ]
        
        available_enemies = enemy_types[:min(len(enemy_types), 2 + self.dungeon_level)]
        num_enemies = 5 + self.dungeon_level * 2
        
        for room in self.dungeon.rooms[1:]:
            if num_enemies <= 0:
                break
            enemies_in_room = random.randint(1, min(3, num_enemies))
            
            for _ in range(enemies_in_room):
                if num_enemies <= 0:
                    break
                
                x = random.randint(room.x + 1, room.x + room.width - 2)
                y = random.randint(room.y + 1, room.y + room.height - 2)
                
                if self.dungeon.is_walkable(x, y) and not self._is_occupied(x, y):
                    template = random.choice(available_enemies)
                    level_mult = 1 + (self.dungeon_level - 1) * 0.15
                    
                    enemy = Enemy(
                        x=x, y=y,
                        name=template[0],
                        hp=int(template[1] * level_mult),
                        max_hp=int(template[1] * level_mult),
                        attack=int(template[2] * level_mult),
                        defense=int(template[3] * level_mult),
                        exp_value=int(template[4] * level_mult),
                        symbol=template[5],
                        color=template[6]
                    )
                    
                    tex_name = self._get_enemy_texture_name(template[0])
                    if self.textures.has(tex_name):
                        enemy.sprite = arcade.Sprite()
                        enemy.sprite.texture = self.textures.get(tex_name)
                        enemy.sprite.width = TILE_SIZE
                        enemy.sprite.height = TILE_SIZE
                    
                    self.enemies.append(enemy)
                    num_enemies -= 1
        
        if self.dungeon_level % 5 == 0 and self.dungeon.rooms:
            boss_room = self.dungeon.rooms[-2] if len(self.dungeon.rooms) > 1 else self.dungeon.rooms[-1]
            cx, cy = boss_room.center
            
            boss = Enemy(
                x=cx, y=cy,
                name=f"Босс {self.dungeon_level} уровня",
                hp=150 + self.dungeon_level * 30,
                max_hp=150 + self.dungeon_level * 30,
                attack=20 + self.dungeon_level * 3,
                defense=10 + self.dungeon_level * 2,
                exp_value=200 + self.dungeon_level * 50,
                symbol="B",
                color=arcade.color.CRIMSON,
                is_boss=True
            )
            
            if self.textures.has('punk'):
                boss.sprite = arcade.Sprite()
                boss.sprite.texture = self.textures.get('punk')
                boss.sprite.width = TILE_SIZE * 1.5
                boss.sprite.height = TILE_SIZE * 1.5
            
            self.enemies.append(boss)
    
    def _spawn_items(self):
        self.items = []
        
        item_templates = [
            (ItemType.HEALTH_POTION, "Здоровье", 25, 1, 30),
            (ItemType.MANA_POTION, "Мана", 20, 1, 25),
            (ItemType.GOLD, "Золото", 0, 1, 40),
            (ItemType.SWORD, "Меч", 5, 2, 15),
            (ItemType.SHIELD, "Щит", 3, 2, 12),
            (ItemType.SCROLL_FIREBALL, "Свиток огня", 30, 3, 5),
            (ItemType.SCROLL_TELEPORT, "Свиток телепорта", 0, 2, 5),
        ]
        
        num_items = 8 + self.dungeon_level
        
        for room in self.dungeon.rooms:
            items_in_room = random.randint(0, 2)
            
            for _ in range(items_in_room):
                if num_items <= 0:
                    break
                
                x = random.randint(room.x + 1, room.x + room.width - 2)
                y = random.randint(room.y + 1, room.y + room.height - 2)
                
                if self.dungeon.is_walkable(x, y) and not self._is_occupied(x, y):
                    weights = [t[4] for t in item_templates]
                    template = random.choices(item_templates, weights=weights)[0]
                    
                    value = template[2]
                    rarity = template[3]
                    
                    if random.random() < 0.1 * self.dungeon_level:
                        rarity = min(5, rarity + 1)
                        value = int(value * 1.5)
                    
                    if template[0] == ItemType.GOLD:
                        value = random.randint(10, 30) * self.dungeon_level
                    
                    item = Item(
                        x=x, y=y,
                        item_type=template[0],
                        name=template[1],
                        value=value,
                        rarity=rarity
                    )
                    
                    tex_name = self._get_item_texture_name(template[0])
                    if self.textures.has(tex_name):
                        item.sprite = arcade.Sprite()
                        item.sprite.texture = self.textures.get(tex_name)
                        item.sprite.width = TILE_SIZE * 0.7
                        item.sprite.height = TILE_SIZE * 0.7
                    
                    self.items.append(item)
                    num_items -= 1
    
    def _is_occupied(self, x, y):
        if self.player and self.player.x == x and self.player.y == y:
            return True
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y and enemy.is_alive():
                return True
        return False
    
    def next_level(self):
        self.dungeon_level += 1
        
        if self.dungeon_level > self.max_dungeon_level:
            self.state = GameState.VICTORY
            return
        
        self.dungeon = DungeonGenerator(MAP_WIDTH, MAP_HEIGHT)
        start_pos = self.dungeon.generate(self.dungeon_level)
        
        self.player.x = start_pos[0]
        self.player.y = start_pos[1]
        
        heal_amount = self.player.max_hp // 4
        self.player.hp = min(self.player.hp + heal_amount, self.player.max_hp)
        self.player.mana = min(self.player.mana + self.player.max_mana // 4, self.player.max_mana)
        
        self._spawn_enemies()
        self._spawn_items()
        
        self.dungeon.compute_fov(self.player.x, self.player.y)
        
        self.message_log.add(f"Этаж {self.dungeon_level}!", arcade.color.GOLD)
        self.message_log.add(f"Восстановлено {heal_amount} ед. здоровья", arcade.color.GREEN)
    
    def move_player(self, dx, dy):
        if self.state != GameState.PLAYING:
            return
        
        new_x = self.player.x + dx
        new_y = self.player.y + dy
        
        for enemy in self.enemies:
            if enemy.x == new_x and enemy.y == new_y and enemy.is_alive():
                self.attack_enemy(enemy)
                self._enemy_turn()
                return
        
        if self.dungeon.is_walkable(new_x, new_y):
            self.player.x = new_x
            self.player.y = new_y
            
            if self.dungeon.tiles[new_x][new_y] == TileType.STAIRS:
                self.message_log.add("Нажмите ENTER чтобы спуститься", arcade.color.LIME_GREEN)
            
            self._pickup_items()
            self.dungeon.compute_fov(self.player.x, self.player.y)
            self._enemy_turn()
            self.turn_count += 1
    
    def attack_enemy(self, enemy):
        damage = max(1, self.player.get_total_attack() - enemy.defense + random.randint(-2, 2))
        
        crit = random.random() < 0.15
        if crit:
            damage *= 2
            self.message_log.add(f"УРА! {enemy.name} получает {damage} ед. урона!", arcade.color.ORANGE)
        else:
            self.message_log.add(f"{enemy.name} получает {damage} ед. урона", arcade.color.WHITE)
        
        enemy.hp -= damage
        
        self.particle_effects.append({
            'x': enemy.x * TILE_SIZE,
            'y': enemy.y * TILE_SIZE,
            'text': f"-{damage}",
            'color': arcade.color.ORANGE if crit else arcade.color.RED,
            'life': 30
        })
        
        if not enemy.is_alive():
            self.message_log.add(f"{enemy.name} повержен! +{enemy.exp_value} опыта", arcade.color.YELLOW)
            
            if self.player.gain_exp(enemy.exp_value):
                self.message_log.add(f"Вы получили новую звезду! Теперь звёзд {self.player.level}!", arcade.color.GOLD)
            
            if random.random() < 0.4:
                gold = random.randint(5, 20) * self.dungeon_level
                self.player.gold += gold
                self.message_log.add(f"+{gold} золота", arcade.color.GOLD)
    
    def _enemy_turn(self):
        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            
            if not self.dungeon.visible[enemy.x][enemy.y]:
                continue
            
            dx = 0
            dy = 0
            
            if enemy.x < self.player.x:
                dx = 1
            elif enemy.x > self.player.x:
                dx = -1
            
            if enemy.y < self.player.y:
                dy = 1
            elif enemy.y > self.player.y:
                dy = -1
            
            if random.random() < 0.3:
                dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            
            new_x = enemy.x + dx
            new_y = enemy.y + dy
            
            if new_x == self.player.x and new_y == self.player.y:
                damage = max(1, enemy.attack - self.player.get_total_defense() + random.randint(-2, 2))
                self.player.hp -= damage
                
                color = arcade.color.RED if enemy.is_boss else arcade.color.LIGHT_CORAL
                self.message_log.add(f"{enemy.name} наносит {damage} ед. урона!", color)
                
                self.particle_effects.append({
                    'x': self.player.x * TILE_SIZE,
                    'y': self.player.y * TILE_SIZE,
                    'text': f"-{damage}",
                    'color': arcade.color.RED,
                    'life': 30
                })
                
                if not self.player.is_alive():
                    self.state = GameState.GAME_OVER
                    self.message_log.add("Вы погибли!", arcade.color.RED)
            
            elif self.dungeon.is_walkable(new_x, new_y) and not self._is_occupied(new_x, new_y):
                enemy.x = new_x
                enemy.y = new_y
    
    def _pickup_items(self):
        items_to_remove = []
        
        for item in self.items:
            if item.x == self.player.x and item.y == self.player.y:
                if item.item_type == ItemType.GOLD:
                    self.player.gold += item.value
                    self.message_log.add(f"+{item.value} золота", arcade.color.GOLD)
                else:
                    if len(self.player.inventory) < 20:
                        self.player.inventory.append(item)
                        self.message_log.add(f"Подобрано: {item.name}", item.get_color())
                    else:
                        self.message_log.add("Сундук полон!", arcade.color.RED)
                        continue
                
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.items.remove(item)
    
    def use_item(self, index):
        if index >= len(self.player.inventory):
            return
        
        item = self.player.inventory[index]
        
        if item.item_type == ItemType.HEALTH_POTION:
            heal = item.value + self.player.level * 5
            self.player.hp = min(self.player.hp + heal, self.player.max_hp)
            self.player.inventory.pop(index)
            self.message_log.add(f"Восстановлено {heal} здоровья", arcade.color.GREEN)
        
        elif item.item_type == ItemType.MANA_POTION:
            restore = item.value + self.player.level * 3
            self.player.mana = min(self.player.mana + restore, self.player.max_mana)
            self.player.inventory.pop(index)
            self.message_log.add(f"Восстановлено {restore} маны", arcade.color.BLUE)
        
        elif item.item_type == ItemType.SCROLL_FIREBALL:
            damage = item.value + self.player.magic
            count = 0
            for enemy in self.enemies:
                if enemy.is_alive() and self.dungeon.visible[enemy.x][enemy.y]:
                    enemy.hp -= damage
                    count += 1
                    if not enemy.is_alive():
                        self.player.gain_exp(enemy.exp_value)
            self.player.inventory.pop(index)
            self.message_log.add(f"Огненный шар поражает {count} врагов!", arcade.color.ORANGE)
        
        elif item.item_type == ItemType.SCROLL_TELEPORT:
            if self.dungeon.rooms:
                room = random.choice(self.dungeon.rooms)
                self.player.x, self.player.y = room.center
                self.dungeon.compute_fov(self.player.x, self.player.y)
                self.player.inventory.pop(index)
                self.message_log.add("Телепортация!", arcade.color.CYAN)
        
        elif item.item_type == ItemType.SWORD:
            old = self.player.equipped['weapon']
            self.player.equipped['weapon'] = item
            self.player.inventory.pop(index)
            if old:
                self.player.inventory.append(old)
            self.message_log.add(f"Экипировано: {item.name}", arcade.color.WHITE)
        
        elif item.item_type == ItemType.SHIELD:
            old = self.player.equipped['shield']
            self.player.equipped['shield'] = item
            self.player.inventory.pop(index)
            if old:
                self.player.inventory.append(old)
            self.message_log.add(f"Экипировано: {item.name}", arcade.color.WHITE)

    
    def cast_spell(self, spell_type):
        if spell_type == "heal":
            cost = 20
            if self.player.mana >= cost:
                heal = 15 + self.player.magic * 2
                self.player.hp = min(self.player.hp + heal, self.player.max_hp)
                self.player.mana -= cost
                self.message_log.add(f"Исцеление: +{heal} здоровья", arcade.color.GREEN)
            else:
                self.message_log.add("Недостаточно маны!", arcade.color.RED)
        
        elif spell_type == "fireball":
            cost = 30
            if self.player.mana >= cost:
                damage = 20 + self.player.magic * 2
                closest = None
                min_dist = float('inf')
                
                for enemy in self.enemies:
                    if enemy.is_alive() and self.dungeon.visible[enemy.x][enemy.y]:
                        dist = abs(enemy.x - self.player.x) + abs(enemy.y - self.player.y)
                        if dist < min_dist:
                            min_dist = dist
                            closest = enemy
                
                if closest:
                    closest.hp -= damage
                    self.player.mana -= cost
                    self.message_log.add(f"Огненный шар: {damage} ед. урона по {closest.name}!", arcade.color.ORANGE)
                    
                    if not closest.is_alive():
                        self.player.gain_exp(closest.exp_value)
                        self.message_log.add(f"{closest.name} повержен!", arcade.color.YELLOW)
                else:
                    self.message_log.add("Нет целей!", arcade.color.GRAY)
            else:
                self.message_log.add("Недостаточно маны!", arcade.color.RED)
    
    def on_key_press(self, key, modifiers):
        if self.state == GameState.MENU:
            if key == arcade.key.ENTER:
                self.state = GameState.CLASS_SELECT
                ##################### заглушка
                classes = list(HeroClass)
                self.selected_hero_class = classes[0]
                self.tutorial_page = TutorialPage.LORE
                self.state = GameState.TUTORIAL
                #####################WW
                self._update_music()
            elif key == arcade.key.ESCAPE:
                self.music.stop()
                arcade.close_window()
        
        elif self.state == GameState.CLASS_SELECT:
            classes = list(HeroClass)
            if key in (arcade.key.UP, arcade.key.W):
                self.selected_class_index = (self.selected_class_index - 1) % len(classes)
            elif key in (arcade.key.DOWN, arcade.key.S):
                self.selected_class_index = (self.selected_class_index + 1) % len(classes)
            elif key == arcade.key.ENTER:
                self.selected_hero_class = classes[self.selected_class_index]
                self.tutorial_page = TutorialPage.LORE
                self.state = GameState.TUTORIAL
            elif key == arcade.key.ESCAPE:
                self.state = GameState.MENU
                self._update_music()
        
        elif self.state == GameState.TUTORIAL:
            if key in (arcade.key.RIGHT, arcade.key.D, arcade.key.ENTER):
                current = self.tutorial_page.value
                if current < len(TutorialPage) - 1:
                    self.tutorial_page = TutorialPage(current + 1)
                else:
                    if self.selected_hero_class:
                        self.start_new_game(self.selected_hero_class)
            elif key in (arcade.key.LEFT, arcade.key.A):
                current = self.tutorial_page.value
                if current > 0:
                    self.tutorial_page = TutorialPage(current - 1)

            elif key == arcade.key.SPACE:
                if self.selected_hero_class:
                    self.start_new_game(self.selected_hero_class)
        
        elif self.state == GameState.PLAYING:
            if key in (arcade.key.UP, arcade.key.W):
                self.move_player(0, 1)
            elif key in (arcade.key.DOWN, arcade.key.S):
                self.move_player(0, -1)
            elif key in (arcade.key.LEFT, arcade.key.A):
                self.move_player(-1, 0)
            elif key in (arcade.key.RIGHT, arcade.key.D):
                self.move_player(1, 0)
            elif key == arcade.key.ENTER:
                if self.dungeon.tiles[self.player.x][self.player.y] == TileType.STAIRS:
                    self.next_level()
            elif key == arcade.key.I:
                self.state = GameState.INVENTORY
                self.selected_inventory_index = 0
            elif key == arcade.key.SPACE:
                self._enemy_turn()
                self.turn_count += 1
            elif key == arcade.key.KEY_1:
                self.cast_spell("heal")
            elif key == arcade.key.KEY_2:
                self.cast_spell("fireball")
            elif key == arcade.key.ESCAPE:
                self.state = GameState.PAUSED
        
        elif self.state == GameState.INVENTORY:
            if key in (arcade.key.UP, arcade.key.W):
                self.selected_inventory_index = max(0, self.selected_inventory_index - 1)
            elif key in (arcade.key.DOWN, arcade.key.S):
                self.selected_inventory_index = min(len(self.player.inventory) - 1, self.selected_inventory_index + 1)
            elif key == arcade.key.ENTER:
                self.use_item(self.selected_inventory_index)
                self.selected_inventory_index = min(self.selected_inventory_index, len(self.player.inventory) - 1)
            elif key in (arcade.key.ESCAPE, arcade.key.I):
                self.state = GameState.PLAYING
        
        elif self.state == GameState.PAUSED:
            if key == arcade.key.ESCAPE:
                self.state = GameState.PLAYING
            elif key == arcade.key.Q:
                self.state = GameState.MENU
                self._update_music()
        
        elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
            if key == arcade.key.ENTER:
                self.state = GameState.MENU
                self._update_music()
    
    def on_update(self, delta_time):
        for effect in self.particle_effects[:]:
            effect['life'] -= 1
            effect['y'] += 1
            if effect['life'] <= 0:
                self.particle_effects.remove(effect)
        
        if self.player:
            target_x = self.player.x * TILE_SIZE - SCREEN_WIDTH // 2
            target_y = self.player.y * TILE_SIZE - SCREEN_HEIGHT // 2
            self.camera_x += (target_x - self.camera_x) * 0.1
            self.camera_y += (target_y - self.camera_y) * 0.1
    
    def on_draw(self):
        self.clear()
        
        if self.state == GameState.MENU:
            self._draw_menu()
        elif self.state == GameState.CLASS_SELECT:
            self._draw_class_select()
        elif self.state == GameState.TUTORIAL:
            self._draw_tutorial()
        elif self.state == GameState.PLAYING:
            self._draw_game()
            self._draw_ui()
        elif self.state == GameState.INVENTORY:
            self._draw_game()
            self._draw_ui()
            self._draw_inventory()
        elif self.state == GameState.PAUSED:
            self._draw_game()
            self._draw_pause()
        elif self.state == GameState.GAME_OVER:
            self._draw_game_over()
        elif self.state == GameState.VICTORY:
            self._draw_victory()
    
    def _draw_menu(self):
        if self.textures.has('menu_bg'):
            draw_texture_at(self.textures.get('menu_bg'), SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT)
            arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 150))
        else:
            arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, arcade.color.DARK_SLATE_GRAY)
        
        arcade.draw_text("KOLOBOK", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100, arcade.color.GOLD, 56, anchor_x="center", bold=True)
        arcade.draw_text("Magical adventure", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40, arcade.color.LIGHT_GRAY, 24, anchor_x="center")
        arcade.draw_text("Нажмите ENTER чтобы начать", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, arcade.color.WHITE, 28, anchor_x="center")
        arcade.draw_text("Нажмите ESC для выхода", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, arcade.color.GRAY, 20, anchor_x="center")
    
    def _draw_class_select(self):
        if self.textures.has('menu_bg'):
            draw_texture_at(self.textures.get('menu_bg'), SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT)
            arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 180))
        else:
            arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, arcade.color.DARK_SLATE_GRAY)
        
        arcade.draw_text("Выберите класс героя", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80, arcade.color.GOLD, 36, anchor_x="center")
        
        classes = list(HeroClass)
        start_y = SCREEN_HEIGHT - 180
        item_height = 100
        item_spacing = 20
        
        for i, hero_class in enumerate(classes):
            center_y = start_y - i * (item_height + item_spacing)
            
            if i == self.selected_class_index:
                arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH // 2 - 250, center_y - item_height // 2, 500, item_height, (60, 60, 80, 200))
                arcade.draw_lbwh_rectangle_outline(SCREEN_WIDTH // 2 - 250, center_y - item_height // 2, 500, item_height, arcade.color.GOLD, 3)
            else:
                arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH // 2 - 250, center_y - item_height // 2, 500, item_height, (40, 40, 60, 150))
            
            color = arcade.color.GOLD if i == self.selected_class_index else arcade.color.WHITE
            arcade.draw_text(hero_class.title, SCREEN_WIDTH // 2, center_y + 15, color, 28, anchor_x="center", anchor_y="center")
            
            stats = f"ОЗ: {hero_class.base_hp}  Мана: {hero_class.base_mana}  АТК: {hero_class.base_attack}  ЗАЩ: {hero_class.base_defense}  МАГ: {hero_class.base_magic}"
            arcade.draw_text(stats, SCREEN_WIDTH // 2, center_y - 20, arcade.color.LIGHT_GRAY, 14, anchor_x="center", anchor_y="center")
        
        arcade.draw_text("Вверх/Вниз - выбор   ENTER - подтвердить   ESC - назад", SCREEN_WIDTH // 2, 50, arcade.color.GRAY, 16, anchor_x="center")
    
    def _draw_tutorial(self):
        if self.textures.has('menu_bg'):
            draw_texture_at(self.textures.get('menu_bg'), SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT)
            arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 200))
        else:
            arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (20, 20, 35))
        
        panel_width = 800
        panel_height = 600
        left = SCREEN_WIDTH // 2 - panel_width // 2
        bottom = SCREEN_HEIGHT // 2 - panel_height // 2
        
        arcade.draw_lbwh_rectangle_filled(left, bottom, panel_width, panel_height, (30, 30, 50, 240))
        arcade.draw_lbwh_rectangle_outline(left, bottom, panel_width, panel_height, arcade.color.GOLD, 3)
        
        page_titles = {TutorialPage.LORE: "ЛЕГЕНДА", TutorialPage.CONTROLS: "УПРАВЛЕНИЕ",
                       TutorialPage.ENEMIES: "ВРАГИ", TutorialPage.ITEMS: "ПРЕДМЕТЫ"}
        
        arcade.draw_text(page_titles[self.tutorial_page], SCREEN_WIDTH // 2, bottom + panel_height - 50, arcade.color.GOLD, 32, anchor_x="center", bold=True)
        #arcade.draw_text(f"Страница {self.tutorial_page.value + 1}/{len(TutorialPage)}", SCREEN_WIDTH // 2, bottom + panel_height - 85, arcade.color.LIGHT_GRAY, 16, anchor_x="center")
        
        content_y = bottom + panel_height - 130
        
        if self.tutorial_page == TutorialPage.CONTROLS:
            controls = [(" ↑ ", "Движение вверх < W >"),
                        (" ↓ ", "Движение вниз < S >"),
                        (" ← ", "Движение влево < A >"),
                        (" → ", "Движение вправо < D >"),
                        (" ", " "),

                        ("ENTER", "Спуститься по лестнице"),
                        (" < I >", "Открыть сундук"),
                        (" < 1 >", "Заклинание исцеления (20 маны)"),
                        (" < 2 >", "Огненный шар (30 маны)"), ("ESC", "Пауза")]

            for i, (key, action) in enumerate(controls):
                y = content_y - i * 40
                arcade.draw_text(key, left + 120, y, arcade.color.YELLOW, 16, anchor_x="center")
                arcade.draw_text("-", left + 220, y, arcade.color.WHITE, 16)
                arcade.draw_text(action, left + 240, y, arcade.color.WHITE, 16)
        
        elif self.tutorial_page == TutorialPage.ENEMIES:
            enemies_info = [("Заяц", arcade.color.LIGHT_GRAY, "Слабый, но быстрый.", 'hare'),
                            ("Волколак", arcade.color.LIGHT_GREEN, "Сильный воин.", 'wolf'),
                            ("Медведь", arcade.color.LIGHT_SKY_BLUE, "Огромный зверь. Очень опасен!.", 'bear'),
                            ("Лиса", arcade.color.ORANGE, "Магический зверь. Ментальные атаки.", 'fox'),
                            ("Скелет", arcade.color.GRAY, "Обычная нежить со средними характеристиками.", 'skeleton'),
                            ("Тыква", arcade.color.LIGHT_BROWN, "Очень медленный враг, но живучий.", 'punk'),
                            ("Щука", arcade.color.DARK_RED, "Элитный враг.", 'fish')]
            for i, (name, color, desc, tex_name) in enumerate(enemies_info):
                y = content_y - i * 55
                if self.textures.has(tex_name):
                    draw_texture_at(self.textures.get(tex_name), left + 60, y, 40, 40)
                arcade.draw_text(name, left + 120, y + 8, color, 18, bold=True)
                arcade.draw_text(desc, left + 120, y - 12, arcade.color.LIGHT_GRAY, 13)
        
        elif self.tutorial_page == TutorialPage.ITEMS:
            items_info = [("Зелье здоровья", arcade.color.LIGHT_CORAL, "Восстанавливает ОЗ.", 'health_potion'),
                          ("Зелье маны", arcade.color.LIGHT_SKY_BLUE, "Восстанавливает ману.", 'mana_potion'),
                          ("Золото", arcade.color.GOLD, "Валюта.", 'gold'),
                          ("Меч", arcade.color.SILVER, "Увеличивает урон.", 'sword'),
                          ("Щит", arcade.color.LIGHT_GRAY, "Увеличивает защиту.", 'shield'),
                          ("Свиток огня", arcade.color.ORANGE, "Урон всем видимым врагам!", 'scroll_fireball'),
                          ("Свиток телепорта", arcade.color.CYAN, "Перемещает в случайную комнату.", 'scroll_teleport')]
            for i, (name, color, desc, tex_name) in enumerate(items_info):
                y = content_y - i * 52
                if self.textures.has(tex_name):
                    draw_texture_at(self.textures.get(tex_name), left + 60, y, 36, 36)
                arcade.draw_text(name, left + 120, y + 8, color, 16, bold=True)
                arcade.draw_text(desc, left + 120, y - 12, arcade.color.LIGHT_GRAY, 12)
        
        elif self.tutorial_page == TutorialPage.LORE:
            lore_text = ["Давным-давно на Руси жили-были Дед-колдун да Бабка-ведьма.",
                         "Как-то раз для кроваго ритуала испекли они Колобка", "и положили его остудить в холодное подземелье.", "",
                         "Но не стал Колобок безропотной жертвой", "Вооружённый лишь своими навыками и отвагой,",
                         "смело отправился он исследовать зловещий подземный лабиринт...",
                         "Колобка ждут несметные богатства и могущественные артефакты", "забытой эпохи. Но также и невыразимые ужасы -",
                         "существа тьмы, питающиеся душами храбрецов...", "",
                        "Да пребудет с вами удача. Ваше путешествие начинается..."]
            for i, line in enumerate(lore_text):
                y = content_y - i * 26
                color = arcade.color.GOLD if i == 0 or i == len(lore_text) - 1 else arcade.color.LIGHT_GRAY
                arcade.draw_text(line, SCREEN_WIDTH // 2, y, color, 15, anchor_x="center")
        
        nav_y = bottom + 30
        if self.tutorial_page.value > 0:
            arcade.draw_text("<< Назад", left + 100, nav_y, arcade.color.GRAY, 14, anchor_x="center")
        if self.tutorial_page.value < len(TutorialPage) - 1:
            arcade.draw_text("Далее >>", left + panel_width - 120, nav_y, arcade.color.GRAY, 14, anchor_x="center")
            arcade.draw_text("ПРОБЕЛ: Пропустить заставку", SCREEN_WIDTH // 2, nav_y, arcade.color.DARK_GRAY, 12,
                             anchor_x="center")
        else:
            arcade.draw_text("ENTER: Начать приключение!", SCREEN_WIDTH // 2, nav_y, arcade.color.GOLD, 16, anchor_x="center", bold=True)

    
    def _draw_game(self):
        if not self.dungeon:
            return
        
        offset_x = -self.camera_x
        offset_y = -self.camera_y
        
        WALL_COLOR = (50, 50, 60)
        WALL_DARK_COLOR = (25, 25, 35)
        FLOOR_COLOR = (35, 35, 45)
        FLOOR_DARK_COLOR = (20, 20, 28)
        STAIRS_COLOR = (25, 60, 25)
        
        for x in range(self.dungeon.width):
            for y in range(self.dungeon.height):
                screen_x = x * TILE_SIZE + offset_x + TILE_SIZE // 2
                screen_y = y * TILE_SIZE + offset_y + TILE_SIZE // 2
                
                if screen_x < -TILE_SIZE or screen_x > SCREEN_WIDTH + TILE_SIZE:
                    continue
                if screen_y < -TILE_SIZE or screen_y > SCREEN_HEIGHT + TILE_SIZE:
                    continue
                
                tile = self.dungeon.tiles[x][y]
                
                if self.dungeon.visible[x][y]:
                    if tile == TileType.WALL:
                        if self.textures.has('wall'):
                            draw_texture_at(self.textures.get('wall'), screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                        else:
                            arcade.draw_lbwh_rectangle_filled(screen_x - TILE_SIZE//2, screen_y - TILE_SIZE//2, TILE_SIZE, TILE_SIZE, WALL_COLOR)
                    elif tile == TileType.FLOOR:
                        if self.textures.has('floor'):
                            draw_texture_at(self.textures.get('floor'), screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                        else:
                            arcade.draw_lbwh_rectangle_filled(screen_x - TILE_SIZE//2, screen_y - TILE_SIZE//2, TILE_SIZE, TILE_SIZE, FLOOR_COLOR)
                    elif tile == TileType.STAIRS:
                        if self.textures.has('stairs'):
                            draw_texture_at(self.textures.get('stairs'), screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                        else:
                            arcade.draw_lbwh_rectangle_filled(screen_x - TILE_SIZE//2, screen_y - TILE_SIZE//2, TILE_SIZE, TILE_SIZE, STAIRS_COLOR)
                elif self.dungeon.explored[x][y]:
                    if tile == TileType.WALL:
                        arcade.draw_lbwh_rectangle_filled(screen_x - TILE_SIZE//2, screen_y - TILE_SIZE//2, TILE_SIZE, TILE_SIZE, WALL_DARK_COLOR)
                    elif tile in [TileType.FLOOR, TileType.STAIRS]:
                        arcade.draw_lbwh_rectangle_filled(screen_x - TILE_SIZE//2, screen_y - TILE_SIZE//2, TILE_SIZE, TILE_SIZE, FLOOR_DARK_COLOR)
        
        for item in self.items:
            if self.dungeon.visible[item.x][item.y]:
                screen_x = item.x * TILE_SIZE + offset_x + TILE_SIZE // 2
                screen_y = item.y * TILE_SIZE + offset_y + TILE_SIZE // 2
                if item.sprite and item.sprite.texture:
                    draw_texture_at(item.sprite.texture, screen_x, screen_y, TILE_SIZE * 0.7, TILE_SIZE * 0.7)
        
        for enemy in self.enemies:
            if enemy.is_alive() and self.dungeon.visible[enemy.x][enemy.y]:
                screen_x = enemy.x * TILE_SIZE + offset_x + TILE_SIZE // 2
                screen_y = enemy.y * TILE_SIZE + offset_y + TILE_SIZE // 2
                size = TILE_SIZE * 1.2 if enemy.is_boss else TILE_SIZE
                if enemy.sprite and enemy.sprite.texture:
                    draw_texture_at(enemy.sprite.texture, screen_x, screen_y, size, size)
                hp_width = TILE_SIZE - 4
                hp_height = 4
                hp_ratio = enemy.hp / enemy.max_hp
                bar_y = screen_y + size / 2 + 4
                arcade.draw_lbwh_rectangle_filled(screen_x - hp_width//2, bar_y - hp_height//2, hp_width, hp_height, arcade.color.DARK_RED)
                if hp_ratio > 0:
                    arcade.draw_lbwh_rectangle_filled(screen_x - hp_width//2, bar_y - hp_height//2, int(hp_width * hp_ratio), hp_height, arcade.color.RED)
        
        if self.player:
            screen_x = self.player.x * TILE_SIZE + offset_x + TILE_SIZE // 2
            screen_y = self.player.y * TILE_SIZE + offset_y + TILE_SIZE // 2
            if self.player.sprite and self.player.sprite.texture:
                draw_texture_at(self.player.sprite.texture, screen_x, screen_y, TILE_SIZE, TILE_SIZE)
        
        for effect in self.particle_effects:
            screen_x = effect['x'] + offset_x + TILE_SIZE // 2
            screen_y = effect['y'] + offset_y + TILE_SIZE // 2
            alpha = int(255 * (effect['life'] / 30))
            color = (*effect['color'][:3], alpha)
            arcade.draw_text(effect['text'], screen_x, screen_y, color, 16, anchor_x="center", anchor_y="center", bold=True)
    
    def _draw_ui(self):
        if not self.player:
            return
        # поле игры вывод инф. панели
        panel_height = 100
        arcade.draw_lbwh_rectangle_filled(0, SCREEN_HEIGHT - panel_height, SCREEN_WIDTH, panel_height, (20, 20, 30, 230))
        self._draw_bar(20, SCREEN_HEIGHT - 30, 200, 30, self.player.hp,
                       self.player.max_hp, arcade.color.RED, arcade.color.DARK_RED,
                       f"Здоровье: {self.player.hp}")
        self._draw_bar(20, SCREEN_HEIGHT - 65, 200, 30, self.player.mana, self.player.max_mana,
                       arcade.color.ORANGE, arcade.color.DARK_BROWN, f"Мана: {self.player.mana}")
        self._draw_bar(250, SCREEN_HEIGHT - 30, 200, 30, self.player.exp, self.player.exp_to_next,
                       arcade.color.GREEN, arcade.color.DARK_GREEN, f"Опыт:   {self.player.exp}")
        # вывод наград
        '''self._draw_bar(250, SCREEN_HEIGHT - 65, 200, 30, 180, 0,
                       (30, 30, 50, 240), (30, 30, 50, 240), f"Золото: {self.player.gold}")
            #arcade.draw_text(f"{self.player.hero_class.title} Уровень {self.player.level}", 20, 
            SCREEN_HEIGHT - 30, arcade.color.GOLD, 18, bold=True)'''

        arcade.draw_text(f"Этаж: {self.dungeon_level}/{self.max_dungeon_level}", SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 50,
                         arcade.color.YELLOW, 32)
        arcade.draw_text(f"Ход: {self.turn_count}", SCREEN_WIDTH // 2 - 20, SCREEN_HEIGHT - 80, arcade.color.GRAY, 16)
        self._draw_bar(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 30, 180, 30, 180, 0,
                       (30, 30, 50, 240), (30, 30, 50, 240),
                       f"Посмотреть СУНДУК < I >")
        # напомнить клавиши
        '''self._draw_bar(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 65, 180, 30, 180, 0,
                       (30, 30, 50, 240), (30, 30, 50, 240),
                       f"Напомнить КЛАВИШИ (K)")'''
        #arcade.draw_text("Посмотреть СУНДУК (I)", SCREEN_WIDTH - 250, SCREEN_HEIGHT - 30, arcade.color.LIGHT_GRAY, 12)
        #arcade.draw_text("Напомнить КЛАВИШИ (K)", SCREEN_WIDTH - 250, SCREEN_HEIGHT - 65, arcade.color.LIGHT_GRAY, 12)
        
        log_height = 120
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, log_height, (20, 20, 30, 200))
        for i, (text, color) in enumerate(self.message_log.messages):
            arcade.draw_text(text, 20, log_height - 25 - i * 18, color, 13)
    
    def _draw_bar(self, x, y, width, height, current, maximum, color, bg_color, text):
        arcade.draw_lbwh_rectangle_filled(x, y - height // 2, width, height, bg_color)
        if maximum > 0:
            ratio = current / maximum
            fill_width = int(width * ratio)
            if fill_width > 0:
                arcade.draw_lbwh_rectangle_filled(x, y - height // 2, fill_width, height, color)
        arcade.draw_text(text, x + width // 2, y, arcade.color.WHITE, 10, anchor_x="center", anchor_y="center")
    
    def _draw_inventory(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 180))
        
        panel_width = 500
        panel_height = 520
        left = SCREEN_WIDTH // 2 - panel_width // 2
        bottom = SCREEN_HEIGHT // 2 - panel_height // 2
        
        arcade.draw_lbwh_rectangle_filled(left, bottom, panel_width, panel_height, (30, 30, 45))
        arcade.draw_lbwh_rectangle_outline(left, bottom, panel_width, panel_height, arcade.color.GOLD, 3)
        arcade.draw_text("СУНДУК", SCREEN_WIDTH // 2, bottom + panel_height - 40, arcade.color.GOLD, 24, anchor_x="center")
        
        equip_y = SCREEN_HEIGHT // 2 + 160
        arcade.draw_text("Оружие", left + 30, equip_y, arcade.color.GOLD, 14)
        arcade.draw_text("Навыки", left + 30 + panel_width // 2, equip_y, arcade.color.GOLD, 14)
        slot_names = {'weapon': 'Оружие', 'shield': 'Щит'}
        slot_player = [("Атака ", self.player.get_total_attack()),
                       ("Защита", self.player.get_total_defense())]

        for i, (slot, name) in enumerate(slot_names.items()):
            item = self.player.equipped.get(slot)
            item_text = item.name if item else "Пусто"
            color = item.get_color() if item else arcade.color.GRAY
            arcade.draw_text(f"{name}: {item_text}", left + 30, equip_y - 25 - i * 20, color, 12)
            arcade.draw_text(f"{slot_player[i][0]}: {slot_player[i][1]}", left + 30 + panel_width // 2,
                             equip_y - 25 - i * 20, color, 12)

        items_start_y = SCREEN_HEIGHT // 2 + 75
        arcade.draw_text("Награды", left + 30, items_start_y, arcade.color.GOLD, 14)
        items_start_y = SCREEN_HEIGHT // 2 + 50
        arcade.draw_text(f"Золото:   {self.player.gold}", left + 30, items_start_y, arcade.color.WHITE, 12)
        items_start_y = SCREEN_HEIGHT // 2 + 30
        arcade.draw_text(f"Уровень:   {self.player.level}", left + 30, items_start_y, arcade.color.WHITE, 12)
        items_start_y = SCREEN_HEIGHT // 2 - 20
        arcade.draw_text("Артефакты и зелья:", left + 30, items_start_y, arcade.color.GOLD, 14)

        if self.player.inventory:
            for i, item in enumerate(self.player.inventory[:12]):
                y = items_start_y - 25 - i * 22
                if i == self.selected_inventory_index:
                    arcade.draw_lbwh_rectangle_filled(left + 20, y - 10, panel_width - 40, 20, arcade.color.DARK_SLATE_GRAY)
                
                tex_name = self._get_item_texture_name(item.item_type)
                if self.textures.has(tex_name):
                    draw_texture_at(self.textures.get(tex_name), left + 35, y, 24, 24)
                
                text = item.name
                if item.item_type in [ItemType.HEALTH_POTION, ItemType.MANA_POTION, ItemType.SWORD, ItemType.SHIELD]:
                    text += f" (+{item.value})"
                arcade.draw_text(text, left + 55, y, item.get_color(), 12, anchor_y="center")
        else:
            arcade.draw_text("Пусто", SCREEN_WIDTH // 2, items_start_y - 50, arcade.color.GRAY, 16, anchor_x="center")
        
        arcade.draw_text("Вверх/Вниз - выбор   ENTER - использовать   ESC - закрыть", SCREEN_WIDTH // 2, bottom + 20, arcade.color.GRAY, 12, anchor_x="center")
    
    def _draw_pause(self):
        arcade.draw_lbwh_rectangle_filled(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 100, 400, 200, (30, 30, 50, 240))
        arcade.draw_text("ПАУЗА", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, arcade.color.WHITE, 36, anchor_x="center")
        arcade.draw_text("ESC - продолжить", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, arcade.color.GRAY, 18, anchor_x="center")
        arcade.draw_text("Q - выйти в меню", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30, arcade.color.GRAY, 18, anchor_x="center")
    
    def _draw_game_over(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 200))
        arcade.draw_text("ВЫ ПОГИБЛИ", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100, arcade.color.RED, 48, anchor_x="center")
        
        if self.player:
            stats = [f"Класс: {self.player.hero_class.title}", f"Уровень: {self.player.level}", f"Этаж подземелья: {self.dungeon_level}", f"Собрано золота: {self.player.gold}", f"Сделано ходов: {self.turn_count}"]
            for i, stat in enumerate(stats):
                arcade.draw_text(stat, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - i * 30, arcade.color.WHITE, 20, anchor_x="center")
        
        arcade.draw_text("Нажмите ENTER для перезапуска", SCREEN_WIDTH // 2, 150, arcade.color.GOLD, 20, anchor_x="center")
    
    def _draw_victory(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 200))
        arcade.draw_text("ПОБЕДА!", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100, arcade.color.GOLD, 48, anchor_x="center")
        arcade.draw_text("Вы покорили подземелье!", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40, arcade.color.WHITE, 24, anchor_x="center")
        
        if self.player:
            stats = [f"Класс: {self.player.hero_class.title}", f"Финальный уровень: {self.player.level}", f"Золото: {self.player.gold}", f"Ходов: {self.turn_count}"]
            for i, stat in enumerate(stats):
                arcade.draw_text(stat, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30 - i * 30, arcade.color.WHITE, 18, anchor_x="center")
        
        arcade.draw_text("Нажмите ENTER для возврата в меню", SCREEN_WIDTH // 2, 150, arcade.color.GOLD, 20, anchor_x="center")


def main():
    game = DungeonRogue()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()