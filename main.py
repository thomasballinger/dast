import sys
import time
import copy

from game import game
from gamelib import game_methods
from lisp_parser import parse, parsed_funs
from obj_iter import Eval, GlobalFunctions, BaseEval, Incomplete, Function
from gamelib import builtins


# TODO detect changes in the top level expression

def check(filename, last_ast, last_funs):
    s = open(filename).read()
    try:
        ast = parse(s)
    except:
        return last_ast, last_funs, None, 'invalid!'
    if ast == last_ast:
        return last_ast, last_funs, None, 'no change'
    new_funs = parsed_funs(ast)
    if set(new_funs) - set(last_funs):
        return ast, new_funs, None, 'new funs'
    if set(last_funs) - set(new_funs):
        return ast, new_funs, None, 'funs removed'
    diff = {}
    for name in new_funs:
        if new_funs[name] != last_funs[name]:
            diff[name] = new_funs[name]
    if diff:
        return ast, new_funs, diff, 'funs modified: '+', '.join(diff.keys())
    return ast, new_funs, None, '?'


#TODO need a wrapper object around Eval objects
# that can keep a counter, do the finicky evaling

def run_and_check(script, every=1):
    builtins.update(game_methods())
    env = [builtins, {}]
    funs = GlobalFunctions()

    ast = parse(game)
    fun_asts = parsed_funs(ast)

    e = Eval(ast, env, funs)
    orig = copy.deepcopy(e)

    funs.set_eval_tree(e)
    ast = parse(game)

    last_check = time.time()
    while True:
        if time.time() > last_check + every:
            ast, fun_asts, changed_funs, status = check(script, ast, fun_asts)
            print(status)
            if status in ['new funs', '?', 'funs removed']:
                e = copy.deepcopy(orig)
            elif status.startswith('funs modified'):
                snapshots = [funs.snapshots[name] for name in changed_funs
                             if name in funs.snapshots]
                #TODO find earliest snapshot
                if snapshots:
                    (e, ) = snapshots
                for fun in changed_funs:
                    old = funs[fun]
                    function = Function(name=old.name,
                                        params=old.params,
                                        ast=changed_funs[fun][-1],
                                        env=old.env,
                                        funs=old.funs)
                    funs[fun] = function
            elif status in ['invalid!', 'no change']:
                pass
            else:
                raise ValueError('what is status %r?' % (status, ))
            last_check = time.time()

        value = next(e)
        if value is Incomplete:
            pass
        elif isinstance(value, BaseEval):
            e = value
        else:
            return value

if __name__ == '__main__':
    if len(sys.argv) == 1:
        script = 'tmp.scm'
        open(script, 'w').write(game)
    elif len(sys.argv) == 2:
        script = sys.argv[1]

    print('watching %s for changes...' % (script, ))
    run_and_check(script)
