import pygame, random, math, os
from collections import deque

pygame.init()

WIDTH, HEIGHT, FPS = 800, 600, 60
HUD_H, CELL, WALL = 50, 50, 6       # marcador, celda del laberinto, grosor de pared
COLS, ROWS = WIDTH // CELL, (HEIGHT - HUD_H) // CELL
MAX_LEVEL, BANNER_TIME = 10, 90

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GALAXITE")
clock = pygame.time.Clock()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BLACK, WHITE, YELLOW = (0, 0, 0), (255, 255, 255), (255, 255, 0)
RED, GRAY = (220, 40, 40), (110, 110, 110)
font = pygame.font.Font(None, 28)
big_font = pygame.font.Font(None, 72)


def load_image(filename, size, fallback):
    path = os.path.join(BASE_DIR, filename)
    if os.path.isfile(path):
        return pygame.transform.scale(pygame.image.load(path).convert_alpha(), size)
    print("Aviso: imagen no encontrada:", path)   # cuadro de color en vez de cerrar el juego
    surface = pygame.Surface(size)
    surface.fill(fallback)
    return surface


player_idle = load_image("player.png", (30, 38), (80, 160, 255))
player_walk = load_image("player2.png", (30, 38), (60, 120, 220))
enemy_image = load_image("enemy.png", (28, 32), (200, 60, 60))


def draw_text(text, font_used, color, x, y):
    image = font_used.render(text, True, color)
    screen.blit(image, image.get_rect(center=(x, y)))


def cell_center(c, r):
    return c * CELL + CELL // 2, HUD_H + r * CELL + CELL // 2


def cell_of(rect):
    return (min(max(rect.centerx // CELL, 0), COLS - 1),
            min(max((rect.centery - HUD_H) // CELL, 0), ROWS - 1))


def inside(cell):
    return 0 <= cell[0] < COLS and 0 <= cell[1] < ROWS


def neighbors(cell, blocked):
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (cell[0] + dc, cell[1] + dr)
        if inside(n) and (min(cell, n), max(cell, n)) not in blocked:
            yield n


def bfs(start, blocked):
    dist, queue = {start: 0}, deque([start])
    while queue:
        current = queue.popleft()
        for n in neighbors(current, blocked):
            if n not in dist:
                dist[n] = dist[current] + 1
                queue.append(n)
    return dist


def generate_maze(level):
    # Una pared solo se acepta si todo el mapa sigue alcanzable (sin zonas cerradas).
    target, blocked = min(25 + level * 8, 100), set()
    for _ in range(400):
        if len(blocked) >= target:
            break
        c, r = random.randrange(COLS), random.randrange(ROWS)
        vertical = random.choice((True, False))
        for i in range(random.randint(2, 4)):
            a, b = ((c, r + i), (c + 1, r + i)) if vertical else ((c + i, r), (c + i, r + 1))
            if not (inside(a) and inside(b)) or (a, b) in blocked:
                break
            blocked.add((a, b))
            if len(bfs((0, 0), blocked)) < COLS * ROWS:
                blocked.discard((a, b))
                break
    return blocked


def build_walls(blocked):
    h = WALL // 2
    walls = [pygame.Rect(0, HUD_H, WIDTH, WALL), pygame.Rect(0, HEIGHT - WALL, WIDTH, WALL),
             pygame.Rect(0, HUD_H, WALL, HEIGHT - HUD_H),
             pygame.Rect(WIDTH - WALL, HUD_H, WALL, HEIGHT - HUD_H)]
    for (c1, r1), (c2, r2) in blocked:
        if r1 == r2:    # pared vertical entre dos celdas contiguas
            walls.append(pygame.Rect(c2 * CELL - h, HUD_H + r1 * CELL - h, WALL, CELL + WALL))
        else:           # pared horizontal
            walls.append(pygame.Rect(c1 * CELL - h, HUD_H + r2 * CELL - h, CELL + WALL, WALL))
    return walls


class Entity:
    def __init__(self, center, w, h):
        self.rect = pygame.Rect(0, 0, w, h)
        self.place(center)

    def place(self, center):
        self.rect.center = center
        self.fx, self.fy = float(self.rect.x), float(self.rect.y)

    def move_with_walls(self, dx, dy, walls):
        self.fx += dx
        self.rect.x = round(self.fx)
        for wall in walls:
            if self.rect.colliderect(wall):
                if dx > 0:
                    self.rect.right = wall.left
                elif dx < 0:
                    self.rect.left = wall.right
                self.fx = self.rect.x
        self.fy += dy
        self.rect.y = round(self.fy)
        for wall in walls:
            if self.rect.colliderect(wall):
                if dy > 0:
                    self.rect.bottom = wall.top
                elif dy < 0:
                    self.rect.top = wall.bottom
                self.fy = self.rect.y


class Bullet:
    def __init__(self, pos, vel, size, color):
        self.x, self.y = pos
        self.vx, self.vy = vel
        self.color = color
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = pos

    def update(self, walls):    # devuelve False si la bala debe desaparecer
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (round(self.x), round(self.y))
        return screen.get_rect().contains(self.rect) and self.rect.collidelist(walls) == -1

    def draw(self):
        pygame.draw.circle(screen, self.color, self.rect.center, self.rect.width // 2)


class Player(Entity):
    def __init__(self):
        super().__init__(cell_center(0, 0), 30, 38)
        self.speed, self.lives, self.score = 4, 3, 0
        self.bullets = []
        self.aim = (1.0, 0.0)       # disparo en 8 direcciones (antes solo horizontal)
        self.facing, self.moving = 1, False
        self.invulnerable = self.shoot_cooldown = 0

    def update(self, keys, walls):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.moving = bool(dx or dy)
        if self.moving:
            length = math.hypot(dx, dy)     # normalizado: la diagonal ya no es mas rapida
            self.aim = (dx / length, dy / length)
            self.move_with_walls(self.aim[0] * self.speed, self.aim[1] * self.speed, walls)
            if dx:
                self.facing = int(dx)
        if keys[pygame.K_SPACE]:            # mantener espacio dispara en rafaga
            self.shoot()
        self.shoot_cooldown = max(0, self.shoot_cooldown - 1)
        self.invulnerable = max(0, self.invulnerable - 1)
        self.bullets = [b for b in self.bullets if b.update(walls)]

    def shoot(self):
        if self.shoot_cooldown > 0:
            return
        self.shoot_cooldown = 15
        vel = (self.aim[0] * 9, self.aim[1] * 9)
        self.bullets.append(Bullet(self.rect.center, vel, 6, YELLOW))

    def take_damage(self):
        if self.invulnerable <= 0:
            self.lives -= 1
            self.invulnerable = 90

    def draw(self):
        for bullet in self.bullets:
            bullet.draw()
        if self.invulnerable > 0 and self.invulnerable // 6 % 2 == 0:
            return      # parpadeo al ser golpeado
        image = player_walk if self.moving else player_idle
        screen.blit(pygame.transform.flip(image, True, False) if self.facing < 0 else image, self.rect)
        cx, cy = self.rect.center       # punto que marca hacia donde se dispara
        pygame.draw.circle(screen, YELLOW,
                           (round(cx + self.aim[0] * 24), round(cy + self.aim[1] * 24)), 2)


class Enemy(Entity):
    def __init__(self, center, level):
        super().__init__(center, 28, 32)
        self.speed = min(0.9 + level * 0.1, 1.9)
        self.bullet_speed = min(3 + level * 0.25, 5)
        self.fire_delay = max(150 - level * 10, 70)
        self.timer = random.randint(60, self.fire_delay)

    def update(self, game):
        ex, ey = self.rect.center
        px, py = game.player.rect.center
        cell = cell_of(self.rect)
        if cell == game.player_cell or cell not in game.dist:
            tx, ty = px, py
        else:       # rodea paredes: va al centro de la celda vecina mas cercana al jugador
            best = min(neighbors(cell, game.blocked), key=lambda n: game.dist.get(n, 999))
            tx, ty = cell_center(*best)
        dx, dy = tx - ex, ty - ey
        dist = math.hypot(dx, dy)
        too_close = cell == game.player_cell and math.hypot(px - ex, py - ey) < 60
        if dist > 2 and not too_close:
            vx, vy = dx / dist * self.speed, dy / dist * self.speed
            for other in game.enemies:      # separacion: no se apilan en el mismo punto
                ox, oy = ex - other.rect.centerx, ey - other.rect.centery
                od = math.hypot(ox, oy)
                if other is not self and 0 < od < 34:
                    vx, vy = vx + ox / od * 0.6, vy + oy / od * 0.6
            self.move_with_walls(vx, vy, game.walls)
        self.timer -= 1
        if self.timer <= 0:     # solo dispara con linea de vision (antes atravesaba paredes)
            if not any(w.clipline((ex, ey), (px, py)) for w in game.walls):
                d = math.hypot(px - ex, py - ey) or 1
                vel = ((px - ex) / d * self.bullet_speed, (py - ey) / d * self.bullet_speed)
                game.enemy_bullets.append(Bullet((ex, ey), vel, 8, RED))
                self.timer = random.randint(self.fire_delay, self.fire_delay * 3 // 2)
            else:
                self.timer = 15

    def draw(self):
        screen.blit(enemy_image, self.rect)


class Game:
    def __init__(self, high_score=0, state="title"):
        self.state, self.level = state, 1
        self.high_score = high_score    # se conserva al reiniciar (antes se perdia)
        self.player = Player()
        self.load_level()

    def load_level(self):
        self.blocked = generate_maze(self.level)
        self.walls = build_walls(self.blocked)
        self.player.place(cell_center(0, 0))
        self.player.bullets.clear()
        self.player.invulnerable = 60
        self.player_cell = (0, 0)
        self.dist = bfs(self.player_cell, self.blocked)
        self.enemy_bullets = []
        self.banner = BANNER_TIME
        far = [cell for cell, d in self.dist.items() if d >= 7]
        amount = min(2 + self.level, 12)
        self.enemies = [Enemy(cell_center(*c), self.level)
                        for c in random.sample(far, min(amount, len(far)))]

    def update(self, keys):
        if self.banner > 0:
            self.banner -= 1
            return
        player = self.player
        player.update(keys, self.walls)
        cell = cell_of(player.rect)
        if cell != self.player_cell:    # el mapa de distancias solo se recalcula al cambiar de celda
            self.player_cell = cell
            self.dist = bfs(cell, self.blocked)
        for enemy in self.enemies:
            enemy.update(self)
        self.enemy_bullets = [b for b in self.enemy_bullets if b.update(self.walls)]

        for bullet in player.bullets[:]:        # balas del jugador contra enemigos
            hit = bullet.rect.collidelist([e.rect for e in self.enemies])
            if hit != -1:
                player.bullets.remove(bullet)
                del self.enemies[hit]
                player.score += 100
        for bullet in self.enemy_bullets[:]:    # siguen en el aire aunque el enemigo muera
            if bullet.rect.colliderect(player.rect):
                self.enemy_bullets.remove(bullet)
                player.take_damage()
        if any(e.rect.colliderect(player.rect) for e in self.enemies):
            player.take_damage()

        self.high_score = max(self.high_score, player.score)
        if player.lives <= 0:
            self.state = "gameover"
        elif not self.enemies:
            player.score += 50 * self.level             # bonus por nivel
            self.level += 1
            if self.level > MAX_LEVEL:
                self.state = "win"
            else:
                self.load_level()

    def draw_game(self):
        for wall in self.walls:
            pygame.draw.rect(screen, GRAY, wall)
        for item in self.enemies + self.enemy_bullets:
            item.draw()
        self.player.draw()
        hud = f"SCORE: {self.player.score}   HIGH SCORE: {self.high_score}   LIVES: {self.player.lives}   LEVEL: {self.level}"
        draw_text(hud, font, WHITE, WIDTH // 2, HUD_H // 2)
        if self.banner > 0:
            draw_text(f"LEVEL {self.level}", big_font, YELLOW, WIDTH // 2, HEIGHT // 2)

    def draw(self):
        screen.fill(BLACK)
        if self.state == "title":
            draw_text("GALAXITE", big_font, WHITE, WIDTH // 2, 230)
            draw_text("PRESS SPACE TO START", font, YELLOW, WIDTH // 2, 330)
        elif self.state == "playing":
            self.draw_game()
        else:
            won = self.state == "win"
            draw_text("YOU WIN!" if won else "GAME OVER", big_font, YELLOW if won else RED, WIDTH // 2, 230)
            draw_text(f"SCORE: {self.player.score}   HIGH SCORE: {self.high_score}", font, WHITE, WIDTH // 2, 300)
            draw_text("PRESS SPACE TO " + ("PLAY AGAIN" if won else "RESTART"), font, WHITE, WIDTH // 2, 350)


def main():
    game = Game()
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if game.state == "title" and event.key == pygame.K_SPACE:
                    game.state = "playing"
                elif game.state in ("gameover", "win") and event.key == pygame.K_SPACE:
                    game = Game(game.high_score, "playing")
        if game.state == "playing":
            game.update(pygame.key.get_pressed())
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()