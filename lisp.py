"""Gradual evaluation techniques

ideas:
    * greenlets (skip this, it's boring)
    * nested generators
    * return thunks


TODO:
  - [ ] parse language that does pygamey stuff
    - [ ] lisp without first class functions
    - [x] pygamey bindings

    should be able to swap out portions of AST at any time
    store last time each function was run

  - [ ] stateful OO evaluator
    - [ ] partial evaluator
    - [ ] snapshotting
    - [ ] log every dereference
    - [ ] log every lambda function call


ASTs are associated directly with functions, and no macros allowed
If we enforce no inner functions, no closures,

Closures are fine - the annoying thing is f = cond ? func1 : func2
no this is ok - if the cond code changes, we'll rerun this.
              - if the func1 we chose changes, change func1!





If we use the "rollback to last use of that code" technique, it seems
ok to use lambdas maybe? But if we didn't dynamically choose the ast
for a function then we wouldn't need to roll back.

Seems like we can do the same thing with values in the environment
For every value, record the last time it was accessed. Rewind
execution to that point when it's changed.

If the value is live editing
a lambda value, no problem - roll back to the last time we accessed the function.

If editing the ast, diff the trees and find out which 


Two different kinds of live reload: changing values (including functions)
and changing initial code, which (based on tree diffs?) triggers rollback?



Another idea: turn everything into environmental updates - do the diffs at this level,
rerun the code to find out how the environment differs, then change values that need to be changed!




Going to give up on tree diffing or something to find a function's source in the new AST given that we knew it in the old one.

INSTEAD: Reevaluate everything, 

It's great 


Named functions (and a single global function namespace) solves associating ast with code
Log every function invocation, save state snapshots at each function invocation


Do functions have closures still? If they do, you changed the code around it! So rerun, including the defun!

"""
from __future__ import division
import operator
import random
import re
import sys
from functools import reduce
from collections import namedtuple


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


class Lambda(namedtuple('baselambda', ['params', 'ast', 'env'])):
    """Anonymous function (annoying for live reloading)"""


def eval(ast, env=None):
    """

    >>> eval(('-', 1, 2))
    -1
    >>> eval(('+', ('-', 1, 2), ('+', 3, 4)))
    6
    >>> eval(('do', ('display', 1), ('display', 2), ('display', 3)))
    1
    2
    3
    >>> eval((('lambda', 'x', 'y', 'z', ('+', 'x', 'y', 'z')), 1, 2, 3))
    6
    """
    if env is None:
        env = [builtins, {}]

    if isinstance(ast, (int, float)):
        return ast
    if isinstance(ast, str):
        return lookup(ast, env)
    if not isinstance(ast, (list, tuple)):
        raise ValueError(ast)

    if ast[0] == 'do':
        for form in ast[1:]:
            result = eval(form, env)
        return result
    elif ast[0] == 'loop':
        while True:
            result = eval(ast[1], env)
    elif ast[0] == 'if':
        assert len(ast) in (3, 4)
        if eval(ast[1]):
            return eval(ast[2], env)
        elif len(ast) == 4:
            return eval(ast[3], env)
        else:
            return None
    elif ast[0] == 'lambda':
        assert all(isinstance(x, str) for x in ast[1:-1])
        return Lambda(params=ast[1:-1], ast=ast[-1], env=[{}])
    else:  # not a special form
        func = eval(ast[0], env)
        args = [eval(f, env) for f in ast[1:]]
        if isinstance(func, Lambda):
            return eval(func.ast, env + [{p: a for p, a in zip(func.params, args)}])
        elif callable(func):
            return builtins[ast[0]](*[eval(f, env) for f in ast[1:]])
        raise ValueError(ast)


def lookup(symbol, env):
    for scope in env:
        if symbol in scope:
            return scope[symbol]
    raise NameError(repr(symbol) + repr(env))


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
    [Incomplete, Incomplete, Incomplete, Incomplete, Incomplete, Incomplete, None]
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
        args = []
        for form in ast[1:]:
            g = eval_generator(form)
            for value in g:
                yield Incomplete
            args.append(value)
        yield builtins[ast[0]](*args)
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

    def update_code(self, ast):
        """With a new ast, find which functions changed

        Find all the function definitions, """

#TODO: treediff two syntax trees


def dict_of_public_methods(obj):
    return {key: getattr(obj, key)
            for key in dir(obj)
            if callable(getattr(obj, key)) and not key.startswith('_')}


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


if __name__ == '__main__':
    eval((('lambda', 'x', 'y', 'z', ('+', 'x', 'y', 'z')), 1, 2, 3))

    import doctest
    doctest.testmod()
    eval(parse(game))
