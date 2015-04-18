"""Gradual evaluation techniques

ideas:
    * greenlets
    * nested generators
    * return thunks


TODO:
    parse language that does pygamey stuff

"""
import re

def tokenize(s):
    """

    >>> tokenize('(+ (thing 1 2) (other 3 4))')
    ['(', '+', '(', 'thing', '1', '2', ')', '(', 'other', '3', '4', ')', ')']

    """
    return re.findall(r'[()]|[\w\-+/*]+', s)

def parse(s):
    """Lispy syntax -> AST

    #>>> '(+ (thing 1 2) (other 3 4))'
    
    #('+', ('thing', 1, 2)

    """



if __name__ == '__main__':
    import doctest
    doctest.testmod()
