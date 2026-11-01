
import pygame

pygame.init()

# CONFIGURACIÓN
WIDTH, HEIGHT = 800, 600
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GALAXITE")
clock = pygame.time.Clock()

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)

title_font = pygame.font.Font(None, 100)
font = pygame.font.Font(None, 50)

languages = {
    "es": ["INICIAR", "IDIOMA", "VOLVER"],
    "en": ["START", "LANGUAGE", "BACK"],
    "pt": ["INICIAR", "IDIOMA", "VOLTAR"]
}

language_names = ["ESPAÑOL", "ENGLISH", "PORTUGUÊS"]
language_codes = ["es", "en", "pt"]

language = "en"
screen = "menu"
selected = 0
game = True


def draw(text, font, color, y):
    surface = font.render(text, True, color)
    window.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))


def change_screen(new_screen):
    global screen, selected
    screen = new_screen
    selected = 0


while game:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            game = False

        elif e.type == pygame.KEYDOWN:

            if e.key == pygame.K_ESCAPE:
                if screen != "menu":
                    change_screen("menu")
                else:
                    game = False

            elif screen == "menu":
                if e.key in (pygame.K_UP, pygame.K_DOWN):
                    selected = 1 - selected

                elif e.key == pygame.K_SPACE:
                    change_screen("started" if selected == 0 else "language")

            elif screen == "language":
                if e.key == pygame.K_UP:
                    selected = (selected - 1) % 4

                elif e.key == pygame.K_DOWN:
                    selected = (selected + 1) % 4

                elif e.key == pygame.K_LEFT:
                    selected = 3

                elif e.key == pygame.K_SPACE:
                    if selected == 3:
                        change_screen("menu")
                    else:
                        language = language_codes[selected]
                        change_screen("menu")

    window.fill(BLACK)
    draw("GALAXITE", title_font, WHITE, 110)

    if screen == "menu":
        for i, option in enumerate(languages[language][:2]):
            draw(option, font, YELLOW if selected == i else WHITE, 290 + i * 75)

    elif screen == "language":
        for i, option in enumerate(language_names):
            draw(option, font, YELLOW if selected == i else WHITE, 230 + i * 65)

        draw(
            languages[language][2],
            font,
            YELLOW if selected == 3 else WHITE,
            510
        )

    elif screen == "started":
        draw("GAME IN DEVELOPMENT", font, WHITE, 320)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
