"""Gradual evaluation techniques

ideas:
    * greenlets (skip this, it's boring)
    * nested generators
    * return thunks


TODO:
    parse language that does pygamey stuff

    should be able to swap out portions of AST at any time
    store last time each function was run

"""
from __future__ import division
import operator
import random
import re
import sys
from functools import reduce


def tokenize(s):
    """

    >>> tokenize('(+ (thing 1 2) (other 3 4))')
    ['(', '+', '(', 'thing', '1', '2', ')', '(', 'other', '3', '4', ')', ')']

    """
    return re.findall(r'[()]|[\w\-+/*?!]+', s)


def parse(s, i=0):
    """Lispy syntax -> AST

    >>> parse('(+ (thing 1 2) (other 3 4))')
    ('+', ('thing', 1, 2), ('other', 3, 4))

    """
    if isinstance(s, str):
        s = iter(tokenize(s))
    cur = next(s)

    if cur == '(':
        form = []
        while True:
            f = parse(s)
            if f == ')':
                return tuple(form)
            form.append(f)
    elif cur == ')':
        return ')'
    elif re.match(r'[+-]?\d+', cur):
        return int(cur)
    elif re.match('[+-]?\d+\.?\d*', cur):
        return float(cur)
    else:
        return cur


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

def lisp_to_py(s):
    s = s.replace('-', '_')
    if s.endswith('?'):
        s = s[:-1] + 'q'
    return s


def eval(ast):
    """

    >>> eval(('-', 1, 2))
    -1
    >>> eval(('+', ('-', 1, 2), ('+', 3, 4)))
    6
    >>> eval(('do', ('display', 1), ('display', 2), ('display', 3)))
    1
    2
    3
    """
    if isinstance(ast, (int, float)):
        return ast
    if ast[0] == 'do':
        for form in ast[1:]:
            result = eval(form)
        return result
    elif ast[0] == 'loop':
        while True:
            result = eval(ast[1])
    elif ast[0] in builtins:
        return builtins[ast[0]](*[eval(f) for f in ast[1:]])
    elif ast[0] == 'if':
        assert len(ast) in (3, 4)
        if eval(ast[1]):
            return eval(ast[2])
        elif len(ast) == 4:
            return eval(ast[3])
        else:
            return None
    raise ValueError(ast)


class Incomplete:
    """Signal that evaluation is incomplete"""
    def __repr__(self):
        return 'Incomplete'
Incomplete = Incomplete()


def eval_with_generator(ast):
    """
    >>> eval_with_generator(('+', ('-', 1, 2), ('+', 3, 4)))
    6
    """
    (result, ) = [x for x in eval_generator(ast) if x is not Incomplete]
    return result


def eval_generator(ast):
    """

    >>> [x for x in eval_generator(['+', 1, 2]) if x is not Incomplete]
    [3]
    >>> g = eval_generator(('do', ('display', 1), ('display', 2), ('display', 3)))
    >>> list(g)
    1
    2
    3
    [Incomplete, Incomplete, Incomplete, None]
    """
    if isinstance(ast, (int, float)):
        yield ast
    elif ast[0] == 'do':
        for form in ast[1:]:
            g = eval_generator(form)
            for value in g:
                yield Incomplete
        yield value
    elif ast[0] in builtins:
        yield builtins[ast[0]](*[eval(f) for f in ast[1:]])
    elif ast[0] == 'if':
        assert len(ast) in (3, 4)
        g = eval_generator(ast[1])
        for value in g:
            yield Incomplete
        if value:
            yield from eval_generator(ast[2])
        elif len(ast) == 4:
            yield from eval_generator(ast[3])


def mutable_version(tree):
    if isinstance(tree, (tuple, list)):
        return [mutable_version(x) for x in tree]
    return tree


class Evaluation(object):
    """Annotate AST with last time run, eval_tree at that time,
    and in current eval what value is there"""
    def __init__(self, ast):
        self.ast = ast
        self.eval_tree = mutable_version(ast)
        self.path = [self.eval_tree]


def dict_of_public_methods(obj):
    return {key: getattr(obj, key)
            for key in dir(obj)
            if callable(getattr(obj, key)) and not key.startswith('_')}


builtins = PyFuncs({
    '+': lambda *args: sum(args),
    '-': lambda *args: (reduce(operator.sub, args, 0)
                        if len(args) == 1
                        else reduce(operator.sub, args)),
    '*': lambda *args: reduce(operator.mul, args, 1),
    '/': lambda x, y: x / y,
    'display': lambda *args: [sys.stdout.write(
        ', '.join(repr(x) for x in args) + '\n'), None][-1],
    'coinflip': lambda: random.choice([True, False])
    })
import gamelib
g = gamelib.Game()
builtins.update(dict_of_public_methods(g))

assert 'upkey?' in builtins


game = """
(loop
    (do
        (background 100 100 100)
        (if (mousepressed?)
            (draw_ball (mousex) (mousey)))
        (render)))
"""
eval(parse(game))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
