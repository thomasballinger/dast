"""
Beautiful generator versions of the code for testing against

>>> run('(+ 1 1)')
2
>>> run('(if 1 2 3)')
2
>>> run('(if 0 2)')
>>> run('((lambda x y (+ 1 y)) 2 3)')
4

"""

from gamelib import builtins, Game
from lisp_parser import parse, Function, Lambda


def run(s):
    ast = parse(s)
    e = eval(ast)
    while True:
        try:
            next(e)
        except StopIteration as e:
            if len(e.args) == 0:
                return None
            else:
                return e.args[0]


def lookup(symbol, env, funs=None):
    assert isinstance(symbol, str), repr(symbol)
    for scope in reversed(env):
        if symbol in scope:
            return scope[symbol]
    if funs is not None and symbol in funs:
        return funs[symbol]
    raise NameError(repr(symbol) + '\n' + repr(env) + '\n' + repr(funs))


def setbang(symbol, value, env):
    assert isinstance(symbol, str), repr(str)
    for scope in reversed(env):
        if symbol in scope:
            scope[symbol] = value
            return
    else:
        env[-1][symbol] = value


def eval(ast, env=None, funs=None):
    if env is None:
        env = [builtins, {}]
    if funs is None:
        funs = {}

    if isinstance(ast, (int, float)):
        return literal(ast)
    if isinstance(ast, str):
        start, end = ast[0], ast[-1]
        if start == end and start in ["'", '"']:
            return literal(ast)
        return lookup(ast, env, funs)
    if not isinstance(ast, (list, tuple)):
        raise ValueError(ast)

    if ast[0] == 'do':
        return (yield from do(*ast[1:]))
    if ast[0] == 'fun':
        return fun(ast[1], ast[2:-1], ast[-1], env, funs)
    if ast[0] == 'lambda':
        return Lambda(ast[1:-1], ast[-1], env, funs)
    if ast[0] == 'set':
        return (yield from Set(ast[1], ast[2]))
    if ast[0] == 'if':
        if len(ast) == 4:
            return (yield from If(*(ast[1:4] + (env, funs))))
        else:
            assert len(ast) == 3
            return (yield from If(*(ast[1:3] + (None, env, funs))))

    return (yield from invocation(ast[0], ast[1:], env, funs))


def invocation(func_ast, expr_asts, env, funs):
    func = (yield from eval(func_ast))
    args = []
    for f in expr_asts:
        args.append((yield from eval(f, env=env, funs=funs)))

    if isinstance(func, (Function, Lambda)):
        if len(func.params) != len(args):
            raise TypeError('func %s takes %d args, %d given' %
                            (func.name, len(func.params), len(args)))
        return (yield from eval(func.ast, env + [{p: a for p, a in zip(func.params, args)}], funs))
    elif callable(func):
        return func(*args)
    raise ValueError("%r doesn't look like a function in %r" % (ast[0], ast))


def literal(ast):
    assert isinstance(ast, (float, int, str))
    if isinstance(ast, str):
        start, end = ast[0], ast[-1]
        if start in ['"', "'"] and start == end:
            return ast[1:-1]
        else:
            assert False, ast+" is't a string literal"
    else:
        return ast


def If(cond, case1, case2, env, funs):
    result = yield from eval(cond)
    if result:
        return (yield from eval(case1))
    elif case2 is None:
        return None
    else:
        return (yield from eval(case2))


def do(forms, env, funs):
    exprs = []
    for f in forms:
        exprs.append((yield from eval(f)))
    return exprs[-1]


def fun(name, params, ast, env, funs):
    assert all(isinstance(x, str) for x in ast[1:-1])
    fun = Function(name=ast[1], params=ast[2:-1], ast=ast[-1], env=env, funs=funs)
    if fun.name in funs:
        raise ValueError("Two definitions for function %s" % (fun.name, ))
    funs[fun.name] = fun
    return fun


def Set(name, value):
    assert isinstance(name, str)
    value = (yield from eval(ast[2], env, funs))
    setbang(name, value)
    return value


if __name__ == '__main__':
    import doctest
    doctest.testmod()
