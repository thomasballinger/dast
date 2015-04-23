"""


>>> parse('+')
'+'

>>> import game
>>> ast = parse(game.game)
>>> sorted(parsed_funs(ast).keys())
['draw-ball-at-mouse', 'draw-ob', 'draw-obs', 'gravity', 'ground', 'jump', 'mainloop', 'step-x', 'step-y']

"""

import re
from collections import namedtuple


class Function(namedtuple('Fun', ['name', 'params', 'ast', 'env', 'funs'])):
    """Named function, duplicate names aren't allowed"""
    def __repr__(self):
        return 'Function(name=%s, params=(%s,), ast=%r)' % (self.name, ', '.join(self.params), self.ast)


class Lambda(namedtuple('Lambda', ['params', 'ast', 'env', 'funs'])):
    """Lambda"""


def tokenize(s):
    """

    >>> tokenize('(+ (thing 1 2) (other 3 4))')
    ['(', '+', '(', 'thing', '1', '2', ')', '(', 'other', '3', '4', ')', ')']

    """
    return re.findall(r"""[()]|[\w\-+/*=<>?!]+|["].*?["]|['].*?[']""", s)


def parse(s, i=0):
    """Lispy syntax -> AST

    >>> parse('(+ (thing 1 2) (other 3 "4"))')
    ('+', ('thing', 1, 2), ('other', 3, '"4"'))

    """
    if isinstance(s, str):
        s = iter(tokenize(s))
    cur = next(s)

    if cur == '(':
        form = []
        while True:
            try:
                f = parse(s)
            except StopIteration:
                raise ValueError("forgot to close something? %r" % (form, ))
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


def parsed_funs(ast, map=None):
    """Returns a map of fun names to fun asts"""
    if map is None:
        map = {}
    if not isinstance(ast, (tuple, list)):
        return
    if ast[0] == 'fun':
        if ast[1] in map:
            raise ValueError('Fun %s declared in two locations' % (ast[1], ))
        map[ast[1]] = ast

    for form in ast:
        parsed_funs(form, map)

    return map


if __name__ == '__main__':
    import doctest
    doctest.testmod()
