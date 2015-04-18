import sys
import pygame


class Game(object):

    def __init__(self):
        pygame.init()

        size = width, height = 320, 240
        self.screen = pygame.display.set_mode(size)
        self.ball = pygame.image.load("ball.gif")

    def draw_ball(self, x, y):
        rect = pygame.Rect(x, y, self.ball.get_rect().width, self.ball.get_rect().height)
        self.screen.blit(self.ball, rect)

    def background(self, r, g, b):
        print(r, g, b)
        self.screen.fill((r, g, b))

    def render(self):
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()

    def _keypressed(key):
        def pressed(self):
            keyState = pygame.key.get_pressed()
            return keyState[key]
        return pressed

    upkeyq = _keypressed(pygame.K_UP)
    downkeyq = _keypressed(pygame.K_DOWN)
    leftkeyq = _keypressed(pygame.K_LEFT)
    rightkeyq = _keypressed(pygame.K_RIGHT)


def test():

    pygame.init()

    size = width, height = 320, 240
    speed = [2, 2]
    black = 0, 0, 0

    screen = pygame.display.set_mode(size)

    ball = pygame.image.load("ball.gif")
    ballrect = ball.get_rect()

    while 1:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()

        ballrect = ballrect.move(speed)
        if ballrect.left < 0 or ballrect.right > width:
            speed[0] = -speed[0]
        if ballrect.top < 0 or ballrect.bottom > height:
            speed[1] = -speed[1]

        screen.fill(black)
        screen.blit(ball, ballrect)
        pygame.display.flip()

if __name__ == '__main__':
    test()



# every statement is named, it's a function call
# keep a list of named
# write a parser, access the current ast


# Repeatedly:
#  parse a text file into an AST
#  evaluate the AST with a generator
#  at each step 
#  store each s-expr evalutation (and everything is a function invocation)
#  store state at that point
#  keep track of what part of the AST a function invocation runs
#  on AST change, find all the function invocations that this AST corresponds to. Rewind to the most recent one of these.
#  
