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


class Function(namedtuple('fun', ['name', 'params', 'ast', 'env'])):
    """Named function, duplicate names aren't allowed"""


def eval(ast, env=None, funs=None):
    """

    >>> eval(('-', 1, 2))
    -1
    >>> eval(('+', ('-', 1, 2), ('+', 3, 4)))
    6
    >>> eval(('do', ('display', 1), ('display', 2), ('display', 3)))
    1
    2
    3
    >>> eval(('do', ('fun', 'three', 'x', 'y', 'z', ('+', 'x', 'y', 'z')),
    ...             ('three', 1, 2, 3)))
    6
    >>> eval(('if', 1, 2, 3))
    2
    >>> funs = {}
    >>> eval(parse('''
    ... (fun maybe cond
    ...     (if (= cond 0)
    ...         1))'''), funs=funs)
    >>> eval(parse('(maybe 0)'), funs=funs)
    1
    """
    if env is None:
        env = [builtins, {}]
    if funs is None:
        funs = {}

    if isinstance(ast, (int, float)):
        return ast
    if isinstance(ast, str):
        start, end = ast[0], ast[-1]
        if start == end and start in ["'", '"']:
            return ast[1:-1]
        return lookup(ast, env, funs)
    if not isinstance(ast, (list, tuple)):
        raise ValueError(ast)

    if ast[0] == 'do':
        for form in ast[1:]:
            result = eval(form, env, funs)
        return result
    elif ast[0] == 'loop':
        while True:
            result = eval(ast[1], env, funs)
    elif ast[0] == 'if':
        assert len(ast) in (3, 4)
        result = eval(ast[1], env, funs)
        if result:
            return eval(ast[2], env, funs)
        elif len(ast) == 4:
            return eval(ast[3], env, funs)
        else:
            return None
    elif ast[0] == 'fun':
        assert all(isinstance(x, str) for x in ast[1:-1])
        fun = Function(name=ast[1], params=ast[2:-1], ast=ast[-1], env=env)
        if fun.name in funs:
            raise ValueError("Two definitions for function %s" % (fun.name, ))
        funs[fun.name] = fun
        return None
    elif ast[0] == 'lambda':
        assert all(isinstance(x, str) for x in ast[1:-1])
        fun = Function(name=ast[0], params=ast[1:-1], ast=ast[-1], env=env)
        return fun
    elif ast[0] == 'set':
        assert len(ast) == 3, ast
        assert isinstance(ast[1], str)
        set(ast[1], eval(ast[2], env, funs), env)

    else:  # not a special form
        func = eval(ast[0], env, funs)
        args = [eval(f, env, funs) for f in ast[1:]]
        if isinstance(func, Function):
            if len(func.params) != len(args):
                raise TypeError('func %s takes %d args, %d given' %
                                (func.name, len(func.params), len(args)))
            return eval(func.ast, env + [{p: a for p, a in zip(func.params, args)}], funs)
        elif callable(func):
            return func(*[eval(f, env, funs) for f in ast[1:]])
        raise ValueError("%r doesn't look like a function in %r" % (ast[0], ast))


def lookup(symbol, env, funs=None):
    assert isinstance(symbol, str), repr(symbol)
    for scope in reversed(env):
        if symbol in scope:
            return scope[symbol]
    if funs is not None and symbol in funs:
        return funs[symbol]
    raise NameError(repr(symbol) + '\n' + repr(env) + '\n' + repr(funs))


def set(symbol, value, env):
    assert isinstance(symbol, str), repr(str)
    for scope in reversed(env):
        if symbol in scope:
            scope[symbol] = value
            print('setting %s to %r' % (symbol, value))
            print(env)
            return
    else:
        env[-1][symbol] = value


class Incomplete:
    """Signal that evaluation is incomplete"""
    def __repr__(self):
        return 'Incomplete'
Incomplete = Incomplete()


def Eval(ast, env, funs):
    """Returns an instance of an iterator which will yield the result"""
    if isinstance(ast, (int, float)):
        return Literal(ast)
    if isinstance(ast, str):
        start, end = ast[0], ast[-1]
        if start == end and start in ["'", '"']:
            return ast[1:-1]
        return Literal(lookup(ast, env, funs))
    if not isinstance(ast, (list, tuple)):
        raise ValueError(ast)


def gen_return(g):
    try:
        while True:
            next(g)
    except StopIteration as e:
        return e.args[0]


def gen_return_with_intermediates(g):
    results = []
    try:
        while True:
            results.append(next(g))
    except StopIteration as e:
        results.append(e.args[0])
        return results


class Literal(object):
    """
    >>> gen_return_with_intermediates(Literal(1))
    [1]
    >>> gen_return_with_intermediates(Literal('"asdf"'))
    ['asdf']

    """
    def __init__(self, ast):
        assert isinstance(ast, (float, int, str))
        if isinstance(ast, str):
            start, end = ast[0], ast[-1]
            if start in ['"', "'"] and start == end:
                self.value = ast[1:-1]
            else:
                assert False, ast+" is't a string literal"
        else:
            self.value = ast
        self.done = False

    def __next__(self):
        if self.done:
            raise StopIteration()
        self.done = True
        raise StopIteration(self.value)


class If(object):
    """
    >>> i = If(1, 2, 3, {})
    >>> i._reference()
    next(i)
    i.cond_result
    [Incomplete, 2]

    """
    def __init__(self, cond, case1, case2, env):
        self.cond = cond
        self.case1 = case1
        self.case2 = case2
        self.env = env

    def _reference(self):
        """Beautiful generator version of this function"""
        result = yield from Eval(self.cond)
        if result:
            return (yield from Eval(self.case1))
        elif self.case1 is None:
            return None
        else:
            return (yield from Eval(self.case2))

    def copy(self):

class Evaluation(object):
    """Annotate AST with last time run, eval_tree at that time,
    and in current eval what value is there

    #>>> e = Evaluation(parse('(if 1 1)'), {});
    #>>> e.ast
    #('if', 1, 1)
    #>>> e.eval_tree
    #[None, {}]
    #>>> e.step()
    #>>> e.eval_tree
    #[('if', (Incomplete, ), {}]
    """
    def __init__(self, ast, env=None):
        self.ast = ast
        if env == None:
            env = [builtins, {}]
        self.eval_tree = [None, env]
        self.funs = {}

    def update_code(self, ast):
        """With a new ast, find which functions changed

        Find all the function definitions, """
        raise NotImplemented('yet')  # TODO

    def step(self):
        """Take one incremental evaluation step, record it, and return.

        Progressively transforms self.eval_tree into an evaluated tree.
        Wrap it in a list so the pattern of modififying the parent works
        at the top level.
        OR let's traverse the AST and add stuff as we go! (better idea)
        Build the eval tree as we go. Make one change each time, store
        partial evaluation information in it!
        """
        # We don't need no stinking recursion!



#TODO: treediff two syntax trees


def dict_of_public_methods(obj):
    return {key: getattr(obj, key)
            for key in dir(obj)
            if callable(getattr(obj, key)) and not key.startswith('_')}


import gamelib
g = gamelib.Game()
builtins.update(dict_of_public_methods(g))





if __name__ == '__main__':
    eval((('lambda', 'x', 'y', 'z', ('+', 'x', 'y', 'z')), 1, 2, 3))

    import doctest
    doctest.testmod()
    from game import game
    #eval(parse(game))
