from __future__ import division
import sys
import operator
import random
import pygame
from functools import reduce


class Game(object):

    def __init__(self):
        pygame.init()

        self.size = width, height = 320, 240
        self.screen = pygame.display.set_mode(self.size)
        self.ball = pygame.image.load("ball.gif")

        pygame.event.set_grab(True)

    def width(self):
        return self.size[0]

    def height(self):
        return self.size[1]

    def draw_ball(self, x, y):
        old_rect = self.ball.get_rect()
        x = x - (old_rect.width / 2)
        y = y - old_rect.height
        rect = pygame.Rect(x, y, old_rect.width, old_rect.height)
        self.screen.blit(self.ball, rect)

    def draw(self, x, y, r, g, b):
        w, h = 10, 10
        rect = pygame.Rect(x-w/2, y-h/2, w, h)
        pygame.draw.rect(self.screen, (r, g, b), rect)

    def background(self, r, g, b):
        self.screen.fill((r, g, b))

    def render(self):
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            print(event)

    def _keypressed(key):
        def pressed(self):
            keyState = pygame.key.get_pressed()
            return keyState[key]
        return pressed

    def mousepressedq(self):
        return pygame.mouse.get_pressed()[0]

    def mousex(self):
        return pygame.mouse.get_pos()[0]

    def mousey(self):
        return pygame.mouse.get_pos()[1]

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


class PyFuncs(dict):
    def __getitem__(self, key):
        if dict.__contains__(self, key):
            return dict.__getitem__(self, key)
        elif dict.__contains__(self, lisp_to_py(key)):
            return dict.__getitem__(self, lisp_to_py(key))
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __repr__(self):
        return '{BuiltinFunctions}'


def lisp_to_py(s):
    s = s.replace('-', '_')
    if s.endswith('?'):
        s = s[:-1] + 'q'
    return s


builtins = PyFuncs({
    '+': lambda *args: sum(args),
    '-': lambda *args: (reduce(operator.sub, args, 0)
                        if len(args) == 1
                        else reduce(operator.sub, args)),
    '*': lambda *args: reduce(operator.mul, args, 1),
    '/': lambda x, y: x / y,
    'display': lambda *args: [sys.stdout.write(
        ', '.join(repr(x) for x in args) + '\n'), None][-1],
    'coinflip': lambda: random.choice([True, False]),
    '=': lambda *args: all(x == args[0] for x in args),
    '<': lambda x, y: x < y,
    '>': lambda x, y: x > y,
    'list': lambda *args: tuple(args),
    'foreach': lambda func, arr: [func(x) for x in arr][-1],
    'len': len,
    })


def dict_of_public_methods(obj):
    return {key: getattr(obj, key)
            for key in dir(obj)
            if callable(getattr(obj, key)) and not key.startswith('_')}


def game_methods():
    g = Game()
    return dict_of_public_methods(g)


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
