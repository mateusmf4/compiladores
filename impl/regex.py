import sys
from dataclasses import dataclass
from typing import TypeVar
import copy

def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else input("Regex: ")
    pat = f'({pat})#'

    root = parse(pat)
    assign_ids(root)

    dfa = gen_dfa(root)
    print(dfa)

T = TypeVar('T')
type Node = Leaf | Concat | Union | Star

@dataclass
class Concat:
    c1: Node
    c2: Node

@dataclass
class Union:
    c1: Node
    c2: Node

@dataclass
class Star:
    c1: Node

@dataclass
class Leaf:
    c: str
    i: int = 0

def parse(sub):
    last: Node = Leaf('')
    i = 0
    while i < len(sub):
        c = sub[i]
        if c == '|':
            rest = parse(sub[i + 1:])
            last = Union(last, rest)
            break
        else:
            if c == '(':
                close = sub.rindex(')')
                c = parse(sub[i + 1:close])
                i = close
            elif c == '[':
                elems = []
                i += 1
                while sub[i] != ']':
                    if sub[i] == '-':
                        a, b = sub[i - 1], sub[i + 1]
                        elems.extend(chr(j) for j in range(ord(a), ord(b) + 1))
                    else:
                        elems.append(sub[i])
                    i += 1
                c = Leaf(elems[0])
                for x in elems[1:]:
                    c = Union(c, Leaf(x))
            else:
                c = Leaf(c)
            
            if i + 1 < len(sub):
                if sub[i + 1] == '*':
                    c = Star(c)
                    i += 1
                elif sub[i + 1] == '?':
                    c = Union(c, Leaf(''))
                    i += 1
                elif sub[i + 1] == '+':
                    c = Concat(c, Star(copy.deepcopy(c)))
                    i += 1

            if isinstance(last, Leaf) and last.c == '':
                last = c
            else:
                last = Concat(last, c)
        i += 1
    return last

def assign_ids(root: Node):
    counter = 1
    def recurse(node: Node):
        nonlocal counter
        if isinstance(node, Concat) or isinstance(node, Union):
            recurse(node.c1)
            recurse(node.c2)
        elif isinstance(node, Star):
            recurse(node.c1)
        elif isinstance(node, Leaf):
            node.i = counter
            counter += 1
    recurse(root)

def gen_dfa(root: Node):
    _null = {}
    def nullable(n: Node):
        nonlocal _null
        if id(n) in _null: return _null[id(n)]
        if isinstance(n, Leaf): res = n.c == ''
        elif isinstance(n, Union):
            res = nullable(n.c1) or nullable(n.c2)
        elif isinstance(n, Concat):
            res = nullable(n.c1) and nullable(n.c2)
        elif isinstance(n, Star):
            res = True
        _null[id(n)] = res
        return res
    
    _first = {}
    def firstpos(n: Node):
        nonlocal _first
        if id(n) in _first: return _first[id(n)]
        if isinstance(n, Leaf): res = {n.i} if n.c else set()
        elif isinstance(n, Union):
            res = firstpos(n.c1).union(firstpos(n.c2))
        elif isinstance(n, Concat):
            if nullable(n.c1):
                res = firstpos(n.c1).union(firstpos(n.c2))
            else:
                res = firstpos(n.c1)
        elif isinstance(n, Star):
            res = firstpos(n.c1)
        _first[id(n)] = res
        return res
    
    _last = {}
    def lastpos(n: Node):
        nonlocal _last
        if id(n) in _last: return _last[id(n)]
        if isinstance(n, Leaf): res = {n.i} if n.c else set()
        elif isinstance(n, Union):
            res = lastpos(n.c1).union(lastpos(n.c2))
        elif isinstance(n, Concat):
            if nullable(n.c2):
                res = lastpos(n.c1).union(lastpos(n.c2))
            else:
                res = lastpos(n.c2)
        elif isinstance(n, Star):
            res = lastpos(n.c1)
        _last[id(n)] = res
        return res
    
    followpos = {}
    def add_follow(i, others):
        nonlocal followpos
        if i not in followpos: followpos[i] = set()
        followpos[i].update(others)
    chars = {}
    def recurse(n: Node):
        nonlocal chars
        if isinstance(n, Concat):
            recurse(n.c1)
            recurse(n.c2)
            l = lastpos(n.c1)
            r = firstpos(n.c2)
            for i in l:
                add_follow(i, r)
        elif isinstance(n, Union):
            recurse(n.c1)
            recurse(n.c2)
        elif isinstance(n, Star):
            recurse(n.c1)
            l = lastpos(n)
            r = firstpos(n)
            for i in l:
                add_follow(i, r)
        elif isinstance(n, Leaf):
            chars[n.i] = n.c
    recurse(root)
    i_terminal = [i for i, c in chars.items() if c == '#'][0]
    alphabet = sorted(set(chars.values()).difference({'#', ''}))
    
    def to_state(s): return ','.join(map(str, sorted(s)))
    
    initial = to_state(firstpos(root))
    states = {initial}
    queue = [initial]
    accept_states = set()
    trans = {}
    while queue:
        S_state = queue[0]
        queue.pop(0)
        S = list(map(int, S_state.split(','))) if S_state else set()
        if i_terminal in S: accept_states.add(S_state)
        for x in alphabet:
            U = set().union(*[followpos.get(i, set()) for i in S if chars[i] == x])
            U_state = to_state(U) if U else 'X'
            if U and U_state not in states:
                states.add(U_state)
                queue.append(U_state)
            trans[(S_state, x)] = U_state

    counter = 1
    state_names = {}
    for state in states:
        if state == initial: continue
        state_names[state] = f'q{counter}'
        counter += 1
    state_names[initial] = 'q0'
    state_names['X'] = 'X'

    for x in alphabet:
        trans[('X', x)] = 'X'
    states.add('X')

    yml = 'states: [' + ', '.join(f'"{state_names[s]}"' for s in states) + ']\n'
    yml += 'input_alphabet: [' + ', '.join(alphabet) + ']\n'
    yml += f'start_state: \"{state_names[initial]}\"\n'
    yml += 'accept_states: [' + ', '.join(f'"{state_names[s]}"' for s in accept_states) + ']\n'
    yml += 'delta:\n'
    for s in states:
        yml += f' {state_names[s]}:\n'
        for x in alphabet:
            yml += f'  {x}: {state_names[trans[(s, x)]]}\n'

    return yml

if __name__ == '__main__':
    main()