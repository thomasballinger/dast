import sys
import time
import copy

from game import game
from gamelib import game_methods
from lisp_parser import parse, parsed_funs
from obj_iter import GlobalFunctions, Runner
from gamelib import builtins


def run_and_check(script, every=1):
    builtins.update(game_methods())
    env = [builtins, {}]
    funs = GlobalFunctions()

    ast = open(script).read()
    runner = Runner(ast, env, funs)

    last_check = time.time()
    for value in runner:
        if time.time() > last_check + every:

            s = open(script).read()
            runner.update(s)
            last_check = time.time()

    return value


test = """
(do
    (fun each i (do
        (display i)
        (sleep 1)
        (each (+ i 1))))
    (display "starting")
    (each 1))
"""

if __name__ == '__main__':
    if len(sys.argv) == 1:
        script = 'tmp.scm'
        open(script, 'w').write(game)
    elif len(sys.argv) == 2:
        script = sys.argv[1]
    print(script)

    print('watching %s for changes...' % (script, ))
    run_and_check(script)
