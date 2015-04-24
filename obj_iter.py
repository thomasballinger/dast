"""
Copy-able objects for evaluation tree, still implementing iterator interface



>>> d = Eval(parse('"a"'), [{}], {}); d
Eval('"a"', env=[{}], funs={})
>>> e = next(d); e
Literal("a")
>>> run("(if (+ 1 2) 3 4)")
3
>>> run('''((fun countto x y
...             (do 1
...             (if (< x y)
...                 (countto (+ x 1) y)
...                 x)))
...         1 2000)''')
2000
"""
import copy
import time

from gamelib import builtins
from lisp_parser import parse, Function, Lambda, parsed_funs

from gen_iter import literal, lookup, setbang


class Incomplete():
    """Keep chewing on the generator - this isn't the final result!"""
    def __repr__(self):
        return 'Incomplete'
Incomplete = Incomplete()


class GlobalFunctions(dict):
    # TODO put this logic in Runner instead
    def __init__(self):
        dict.__init__(self)
        self.snapshots = {}

    def set_eval_tree(self, tree):
        self.top_level = tree

    def about_to_call(self, func):
        if not isinstance(func, (Function, Lambda)):
            raise ValueError('?')
        t = time.time()
        self.snapshots[func.name] = [copy.deepcopy(self.top_level), t]

    def __getitem__(self, key):
        fun = dict.__getitem__(self, key)
        return fun

    def __deepcopy__(self, memo):
        return self


def run(s, env=None, funs=None):
    """
    >>> run('(+ 1 1)')
    2
    """
    runner = Runner(s, env, funs)
    for value in runner:
        pass
    return value


class Runner(object):
    def __init__(self, s, env=None, funs=None):
        self.ast = parse(s)
        self.function_asts = parsed_funs(self.ast)
        self.done = False
        self.i = 0

        if env is None:
            env = [builtins, {}]
        if funs is None:
            funs = GlobalFunctions()

        self.funs = funs
        self.state = Eval(self.ast, env, funs)
        funs.set_eval_tree(self.state)
        self.orig_eval = copy.deepcopy(self.state)

    def reset(self):
        self.state = copy.deepcopy(self.orig_eval)

    def diff_funs(self, old_funs, new_funs):
        """Returns new, removed, and modified function names"""
        return (set(new_funs) - set(old_funs),
                set(old_funs) - set(new_funs),
                set(name for name in new_funs
                    if new_funs[name] != old_funs[name]))

    def update(self, s):
        ast = parse(s)
        if ast == self.ast:
            return
        print('ast changed!')

        new_fun_asts = parsed_funs(ast)
        new, removed, modified = self.diff_funs(self.function_asts, new_fun_asts)
        self.function_asts = new_fun_asts
        self.ast = ast
        if modified:
            print('ast modified! changed function %s' % (modified, ))
        if new or removed or len(modified) > 1:
            raise ValueError("can't cope with that change yet: new:%r removed:%r modified:%r" % (new, removed, modified))

        if modified:
            (name, ) = modified

            old = self.funs[name]
            function = Function(name=old.name,
                                params=new_fun_asts[name][2:-1],
                                ast=new_fun_asts[name][-1],
                                env=old.env,
                                funs=old.funs)
            self.funs[name] = function

            if name not in self.funs.snapshots:
                return
            snapshot, t = self.funs.snapshots[name]
            print('restoring snapshot from %s' % (t, ))
            self.state = snapshot
            self.funs.set_eval_tree(self.state)
        else:  # must have been in top level expression
            self.state = self.orig_eval
            self.funs.set_eval_tree(self.state)

    def step(self):
        self.i += 1
        value = next(self.state)
        if value is Incomplete:
            pass
        elif isinstance(value, BaseEval):
            self.state = value
            self.funs.set_eval_tree(self.state)
        else:
            self.done = True
            return value

    def __iter__(self):
        return self

    def __next__(self):
        if self.done:
            raise StopIteration
        return self.step()


class BaseEval(object):
    """Something iterable, that isn't a real result"""

    def __iter__(self):
        return self

    def __deepcopy__(self, memo):
        # Not doing anything with memo because I think these are trees
        cls = self.__class__
        new = cls.__new__(cls)
        for k, v in self.__dict__.items():
            setattr(new, k, copy.deepcopy(v, memo))
        return new

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__



class Eval(BaseEval):
    def __init__(self, ast, env, funs):
        self.ast = ast
        self.env = env
        self.funs = funs

    def __repr__(self):
        return "Eval(%r, env=%r, funs=%r)" % (self.ast, self.env, self.funs)

    def __next__(self):
        return eval(self.ast, self.env, self.funs)


def eval(ast, env, funs):
    if isinstance(ast, (int, float)):
        return Literal(ast)
    if isinstance(ast, str):
        start, end = ast[0], ast[-1]
        if start == end and start in ["'", '"']:
            return Literal(ast)
        return Lookup(ast, env, funs)
    if not isinstance(ast, (list, tuple)):
        raise ValueError(ast, env, funs)

    if ast[0] == 'do':
        return Do(ast[1:], env, funs)
    if ast[0] == 'fun':
        return Fun(ast[1], ast[2:-1], ast[-1], env, funs)
    if ast[0] == 'set':
        return Set(ast[1], ast[2], env, funs)
    if ast[0] == 'if':
        return If(ast[1], ast[2], ast[3] if len(ast) == 4 else None, env, funs)
    return Invocation(ast[0], ast[1:], env, funs)
    raise ValueError("whoops! don't know how to eval %r", (ast, ))


class Literal(BaseEval):
    def __init__(self, ast):
        self.ast = ast

    def __next__(self):
        return literal(self.ast)

    def __repr__(self):
        return "Literal(%s)" % (self.ast, )


class Fun(BaseEval):
    """

    >>> a = Eval(parse('(fun geta x y a)'), [{'a': 1}], {}); a
    Eval(('fun', 'geta', 'x', 'y', 'a'), env=[{'a': 1}], funs={})
    >>> b = next(a); b
    Fun(geta(x, y) -> 'a', env=[{'a': 1}], funs={})

    """
    def __init__(self, name, params, ast, env, funs):
        self.name = name
        self.params = params
        self.ast = ast
        self.env = env
        self.funs = funs

    def __next__(self):
        function = Function(name=self.name, params=self.params, ast=self.ast, env=self.env, funs=self.funs)
        self.funs[function.name] = function
        return function

    def __repr__(self):
        return "Fun(%s(%s) -> %r, env=%r, funs=%r)" % (
                self.name,
                ', '.join(self.params),
                self.ast,
                self.env,
                self.funs)


class Lookup(BaseEval):
    """
    >>> a = Eval(parse('a'), [{'a': 1}], {}); a
    Eval('a', env=[{'a': 1}], funs={})
    >>> b = next(a)
    >>> a
    Eval('a', env=[{'a': 1}], funs={})
    >>> b
    Lookup(a, env=[{'a': 1}], funs={})
    >>> c = next(b)
    >>> b
    Lookup(a, env=[{'a': 1}], funs={})
    >>> c
    1
    """
    def __init__(self, symbol, env, funs):
        self.symbol = symbol
        self.env = env
        self.funs = funs

    def __next__(self):
        return lookup(self.symbol, self.env, self.funs)

    def __repr__(self):
        return "Lookup(%s, env=%r, funs=%r)" % (self.symbol, self.env, self.funs)


class Set(BaseEval):
    """
    >>> f = Eval(parse('(set a 2)'), [{}], {}); f
    Eval(('set', 'a', 2), env=[{}], funs={})
    >>> g = next(f); g
    Set(a, Eval(2, env=[{}], funs={}), env=[{}])
    >>> next(g); g
    Incomplete
    Set(a, Literal(2), env=[{}])
    >>> next(g)
    2
    """

    def __init__(self, symbol, ast, env, funs):
        self.symbol = symbol
        self.ast = ast
        self.funs = funs
        self.env = env
        self.delegate = Eval(ast, env, funs)

    def __next__(self):
        if self.delegate is None:
            self.delegate = Eval(self.ast, self.env, self.funs)
            return Incomplete
        else:
            value = next(self.delegate)
            if value is Incomplete:
                return value
            if isinstance(value, BaseEval):
                self.delegate = value
                return Incomplete
            setbang(self.symbol, value, self.env)
            return value

    def __repr__(self):
        return "Set(%s, %r, env=%r)" % (
            self.symbol,
            self.delegate if self.delegate else self.ast,
            self.env)


class Do(BaseEval):
    """

    >>> a = Eval(parse('(do 1 2)'), [{}], {}); a
    Eval(('do', 1, 2), env=[{}], funs={})
    >>> b = next(a); b
    Do(1, 2, env=[{}], funs={})
    >>> next(b); b
    Incomplete
    Do(Eval(1, env=[{}], funs={}), 2, env=[{}], funs={})
    >>> next(b); b
    Incomplete
    Do(Literal(1), 2, env=[{}], funs={})
    >>> c = next(b); c
    Eval(2, env=[{}], funs={})
    >>> d = next(c); d
    Literal(2)
    >>> next(d)
    2
    """
    def __init__(self, forms, env, funs):
        self.forms = forms
        self.env = env
        self.funs = funs
        self.values = []
        self.delegate = None

    def __next__(self):
        if self.delegate is None:
            self.delegate = Eval(self.forms[len(self.values)], self.env, self.funs)
            return Incomplete
        else:
            value = next(self.delegate)
            if value is Incomplete:
                return value
            if isinstance(value, BaseEval):
                self.delegate = value
                return Incomplete
            self.values.append(value)
            if len(self.values) < len(self.forms) - 1:
                self.delegate = Eval(self.forms[len(self.values)], self.env, self.funs)
                return Incomplete
            return Eval(self.forms[len(self.values)], self.env, self.funs)

    def __repr__(self):
        if self.delegate is None:
            to_print = self.forms
        else:
            to_print = (tuple(self.values) +
                        (self.delegate,) +
                        self.forms[len(self.values)+1:])
        return "Do(%s, env=%r, funs=%r)" % (
            ', '.join(repr(x) for x in to_print),
            self.env,
            self.funs)


class If(BaseEval):
    """

    >>> a = Eval(parse('(if 1 2 3)'), [{}], {}); a
    Eval(('if', 1, 2, 3), env=[{}], funs={})
    >>> b = next(a); b
    If(1 ? 2 : 3, env=[{}], funs={})
    >>> next(b); b
    Incomplete
    If(Eval(1, env=[{}], funs={}) ? 2 : 3, env=[{}], funs={})
    >>> next(b); b
    Incomplete
    If(Literal(1) ? 2 : 3, env=[{}], funs={})
    >>> next(b); b
    Incomplete
    If(True, 2, env=[{}], funs={})
    >>> next(b)
    Eval(2, env=[{}], funs={})
    """
    def __init__(self, cond, case1, case2, env, funs):
        self.cond = cond
        self.case1 = case1
        self.case2 = case2
        self.env = env
        self.funs = funs
        self.delegate = None
        self.value = None

    def __repr__(self):
        if self.value is None:
            return 'If(%r ? %r : %r, env=%r, funs=%r)' % (
                self.cond if self.delegate is None else self.delegate,
                self.case1,
                self.case2,
                self.env,
                self.funs)
        else:
            return 'If(%r, %r, env=%r, funs=%r)' % (
                self.value,
                self.case1 if self.value else self.case2,
                self.env,
                self.funs)

    def __next__(self):
        if self.value is not None:
            if self.case2 is None and not self.value:
                return None
            else:
                return Eval(self.case1 if self.value else self.case2,
                            env=self.env, funs=self.funs)
        if self.delegate is None:
            self.delegate = Eval(self.cond, self.env, self.funs)
            return Incomplete
        value = next(self.delegate)
        if value is Incomplete:
            return value
        if isinstance(value, BaseEval):
            self.delegate = value
            return Incomplete
        self.value = bool(value)
        return Incomplete


class Invocation(BaseEval):
    """


    >>> a = Eval(parse('((fun inc x (+ x 1)) 2)'), env=[builtins], funs={}); a
    Eval((('fun', 'inc', 'x', ('+', 'x', 1)), 2), env=[{BuiltinFunctions}], funs={})
    >>> b = next(a); b
    Invocation(('fun', 'inc', 'x', ('+', 'x', 1))(2), env=[{BuiltinFunctions}], funs={})
    >>> next(b); b
    Incomplete
    Invocation(Eval(('fun', 'inc', 'x', ('+', 'x', 1)), env=[{BuiltinFunctions}], funs={})(2), env=[{BuiltinFunctions}], funs={})
    >>> next(b); b
    Incomplete
    Invocation(Fun(inc(x) -> ('+', 'x', 1), env=[{BuiltinFunctions}], funs={})(2), env=[{BuiltinFunctions}], funs={})
    >>> next(b); b
    Incomplete
    Invocation(inc(Eval(2, env=[{BuiltinFunctions}], funs={'inc': Function(name=inc, params=(x,), ast=('+', 'x', 1))})), env=[{BuiltinFunctions}], funs={'inc': Function(name=inc, params=(x,), ast=('+', 'x', 1))})
    """
    def __init__(self, func_ast, arg_asts, env, funs):
        self.func_ast = func_ast
        self.arg_asts = arg_asts
        self.asts = (func_ast,) + arg_asts
        self.env = env
        self.funs = funs
        self.values = []
        self.delegate = None

    def __next__(self):
        if self.delegate is None:
            self.delegate = Eval(self.asts[len(self.values)], self.env, self.funs)
            return Incomplete
        elif len(self.values) == len(self.asts):
            func = self.values[0]
            args = self.values[1:]
            if isinstance(func, (Function, Lambda)):
                if len(func.params) != len(args):
                    raise TypeError('func %s takes %d param, %d args given: %r called on %r (-> %r)' %
                                    (func.name, len(func.params), len(args), self.func_ast, self.arg_asts, args))
                self.funs.about_to_call(func)
                new_env = self.env[:-1] + [{p: a for p, a in zip(func.params, args)}]
                #TODO save state here
                return Eval(self.funs[self.values[0].name].ast, new_env, self.funs)
            elif callable(func):
                return func(*args)
            raise ValueError("%r doesn't look like a function in %r" % (self.func_ast, self.arg_asts))
        else:
            value = next(self.delegate)
            if value is Incomplete:
                return value
            if isinstance(value, BaseEval):
                self.delegate = value
                return Incomplete
            self.values.append(value)
            if len(self.values) < len(self.asts):
                self.delegate = Eval(self.asts[len(self.values)], self.env, self.funs)
            return Incomplete


    def __repr__(self):
        if self.delegate is None:
            return "Invocation(%r(%s), env=%r, funs=%r)" % (
                self.func_ast, ' '.join(repr(x) for x in self.arg_asts), self.env, self.funs)
        if len(self.values) == 0:
            return "Invocation(%r(%s), env=%r, funs=%r)" % (
                self.delegate, ' '.join(repr(x) for x in self.arg_asts), self.env, self.funs)
        to_print = (tuple(self.values[1:]) +
                    (self.delegate,) +
                    self.asts[len(self.values)+2:])
        return "Invocation(%s(%s), env=%r, funs=%r)" % (
            self.values[0].name
            if isinstance(self.values[0], (Function, Lambda))
            else self.values[0].__name__,
            ', '.join(repr(x) for x in to_print),
            self.env,
            self.funs)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
