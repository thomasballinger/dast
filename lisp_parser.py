import re
from collections import namedtuple


class Function(namedtuple('Fun', ['name', 'params', 'ast', 'env', 'funs'])):
    """Named function, duplicate names aren't allowed"""


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

if __name__ == '__main__':
    import doctest
    doctest.testmod()
