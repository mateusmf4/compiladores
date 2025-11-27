import sys
from dataclasses import dataclass
from typing import TypeVar

EPSILON = 'ϵ'

def main_pred():
    grammar_path = sys.argv[1]
    with open(grammar_path) as file:
        grammar_text = file.read()
    gm = parse_bnf(grammar_text)
    # print(gm)

    ipt = input("Input: ") if len(sys.argv) == 2 else sys.argv[2]

    parser = PredParser(gm)
    parser.build_table()

    print(parser.first_map)
    print(parser.follow_map)
    print(parser.table)

    rules = parser.parse(ipt.strip().split())
    for r in rules:
        print(r)

def main():
    grammar_path = sys.argv[1]
    with open(grammar_path) as file:
        grammar_text = file.read()
    gm = parse_bnf(grammar_text)
    print(gm)

    parser = SLRParser(gm)
    parser.build_states()
    parser.build_table()
    globals()['parser'] = parser

T = TypeVar('T')

@dataclass(order=True)
class Rule:
    name: str
    body: list[str]

    def __str__(self) -> str:
        return f'{self.name} -> {" ".join(self.body)}'

@dataclass
class Grammar:
    rules: list[Rule]
    # ordered in order of appearance
    non_terminals: list[str]
    terminals: list[str]
    # X: every rule X -> ...
    rule_map: dict[str, list[Rule]]

    def is_terminal(self, s: str):
        return s == '' or s in self.terminals

    def is_non_terminal(self, s: str):
        return s in self.non_terminals

    def starting_symbol(self):
        return self.rules[0].name

    def is_symbol(self, s: str):
        return s in self.terminals or s in self.non_terminals

def parse_bnf(text: str) -> Grammar:
    g = Grammar([], [], [], {})
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        if line[0] == '#': continue

        name, bodies = map(str.strip, line.split('->', 1))
        for body_str in bodies.split(' | '):
            body = body_str.split()
            if not body or body == [EPSILON]: body = ['']
            rule = Rule(name, body)
            g.rules.append(rule)
            g.rule_map.setdefault(name, []).append(rule)

    for rule in g.rules:
        if rule.name not in g.non_terminals:
            g.non_terminals.append(rule.name)

    for rule in g.rules:
        for s in rule.body:
            if s not in g.non_terminals and s and s not in g.terminals:
                g.terminals.append(s)

    g.terminals.sort()

    return g

class GrammarError(Exception):
    pass

class ParserError(Exception):
    pass

class FirstFollow:
    g: Grammar
    first_map: dict[tuple[str, ...], set[str]]
    follow_map: dict[str, set[str]]

    def __init__(self, g: Grammar):
        self.g = g
        self.first_map = {}
        self.follow_map = {}

    def first(self, syms: list[str]) -> set[str]:
        key = tuple(syms)
        if key in self.first_map: return self.first_map[key]

        if len(syms) == 1:
            if self.g.is_terminal(syms[0]):
                res = {syms[0]}
            else:
                res = set().union(*[self.first(rule.body) for rule in self.g.rule_map[syms[0]]])
        else:
            res = set()
            has_empty = True
            # X -> Y Z W
            for sym in syms:
                f = self.first([sym])
                res.update(f - {''})
                if '' not in f:
                    has_empty = False
                    break
            if has_empty: res.add('')

        self.first_map[key] = res
        return res

    def follow(self, nt: str, visited: set[int] | None = None) -> set[str]:
        if visited is None: visited = set()

        key = nt
        if key in self.follow_map: return self.follow_map[key]

        res = set()
        if nt == self.g.starting_symbol():
            res.add('$')

        for rule_idx, rule in enumerate(self.g.rules):
            if rule_idx in visited: continue
            if nt not in rule.body: continue

            for i in range(len(rule.body)):
                if rule.body[i] != nt: continue
                # not the last symbol
                if i != len(rule.body) - 1:
                    first_rest = self.first(rule.body[i + 1:])
                    res.update(first_rest - {''})
                    has_empty = '' in first_rest
                else:
                    has_empty = True

                if has_empty and rule.name != nt:
                    res.update(self.follow(rule.name, visited.union({rule_idx})))

        self.follow_map[key] = res
        return res

class PredParser(FirstFollow):
    table: dict[tuple[str, str], Rule]

    def __init__(self, g: Grammar):
        super().__init__(g)
        self.table = {}

    def build_table(self):
        for rule in self.g.rules:
            f = self.first(rule.body)
            for s in f - {''}:
                if (rule.name, s) in self.table:
                    raise GrammarError('Grammar is ambiguous')
                self.table[(rule.name, s)] = rule
            if '' in f:
                for s in self.follow(rule.name):
                    if (rule.name, s) in self.table:
                        raise GrammarError('Grammar is ambiguous')
                    self.table[(rule.name, s)] = rule

    def parse(self, tokens: list[str]) -> list[Rule]:
        out_rules = []

        tokens = [*tokens, '$']
        token_idx = 0
        stack = ['$', self.g.starting_symbol()]
        while stack[-1] != '$':
            top = stack[-1]
            a = tokens[token_idx]
            if top == a:
                token_idx += 1
                stack.pop()
            elif self.g.is_terminal(top):
                raise ParserError(f'wanted \"{top}\", got \"{a}\"')
            elif (top, a) not in self.table:
                raise ParserError(f'got \"{a}\" while parsing \"{top}\"')
            else:
                rule = self.table[(top, a)]
                out_rules.append(rule)
                stack.pop()
                for Y in reversed(rule.body):
                    if Y: stack.append(Y)

        return out_rules

@dataclass(order=True)
class RuleItem:
    rule: Rule
    idx: int = 0

    # symbol right after the dot
    def symbol_after(self) -> str | None:
        if self.idx == len(self.rule.body): return None
        return self.rule.body[self.idx]

    # symbol right before the dot
    def symbol_before(self) -> str | None:
        if self.idx == 0: return None
        return self.rule.body[self.idx - 1]

    def __str__(self) -> str:
        return f'{self.rule.name} -> {" ".join(self.rule.body[:self.idx])}.{" ".join(self.rule.body[self.idx:])}'

@dataclass
class LRShift:
    state: int

@dataclass
class LRReduce:
    rule_idx: int

@dataclass
class LRAccept: pass

type LRAction = LRShift | LRReduce | LRAccept

@dataclass
class LRState:
    items: list[RuleItem]

    def normalize(self):
        self.items.sort()

    def __str__(self) -> str:
        return 'LRState:\n  ' + '\n  '.join(map(str, self.items))

def extend_grammar(g: Grammar) -> Grammar:
    s = g.starting_symbol()
    candidates = [f"{s}'", 'S', 'START', "START'"]
    for c in candidates:
        if not g.is_symbol(c):
            new = c
            break
    else:
        raise GrammarError('Could not extend grammar - do not use START as a symbol')

    new_rule = Rule(new, [s])
    g.rules.insert(0, new_rule)
    g.non_terminals.insert(0, new)
    g.rule_map[new] = [new_rule]
    return g

class SLRParser(FirstFollow):
    action_table: dict[tuple[int, str], LRAction]
    goto_table: dict[tuple[int, str], int]
    states: list[LRState]
    state_trans: dict[tuple[int, str], int]

    def __init__(self, g: Grammar):
        super().__init__(extend_grammar(g))
        self.action_table = {}
        self.goto_table = {}
        self.states = []
        self.state_trans = {}

    def closure(self, items: list[RuleItem]) -> LRState:
        state = LRState(items)
        start_i = 0
        while True:
            prev_size = len(state.items)
            for i in range(start_i, len(state.items)):
                sym = state.items[i].symbol_after()
                if sym is not None and self.g.is_non_terminal(sym):
                    items = [RuleItem(rule) for rule in self.g.rule_map[sym]]
                    for item in items:
                        if item not in state.items:
                            state.items.append(item)

            # were there any new items
            if prev_size == len(state.items):
                break
            # skip over ones we've already checked
            start_i = prev_size
        state.normalize()
        return state

    def goto(self, state: LRState, sym: str) -> LRState:
        items = []
        for prev in state.items:
            if prev.symbol_after() == sym:
                items.append(RuleItem(prev.rule, prev.idx + 1))
        return self.closure(items)

    def build_states(self):
        states = self.states
        states.append(self.closure([RuleItem(self.g.rules[0])]))

        start_i = 0
        while True:
            prev_size = len(states)
            for i in range(start_i, len(states)):
                for sym in [*self.g.non_terminals, *self.g.terminals]:
                    if sym == self.g.starting_symbol(): continue
                    new_state = self.goto(states[i], sym)
                    # ignore empty states
                    if not new_state.items: continue
                    try:
                        j = states.index(new_state)
                    except ValueError:
                        j = None
                    # new_state isn't in states
                    if j is None:
                        j = len(states)
                        states.append(new_state)
                    self.state_trans[(i, sym)] = j

            if prev_size == len(states):
                break
            start_i = prev_size

    def build_table(self):
        for i, state in enumerate(self.states):
            # S' -> S.
            if RuleItem(self.g.rules[0], 1) in state.items:
                self.action_table[(i, '$')] = LRAccept()

            for s in self.g.terminals:
                j = self.state_trans.get((i, s))
                if j is not None:
                    self.action_table[(i, s)] = LRShift(j)
            for item in state.items:
                if item.symbol_after() is None and item.rule.name != self.g.starting_symbol():
                    follow = self.follow(item.rule.name)
                    for c in follow:
                        if (i, c) in self.action_table:
                            kind = 'R/R' if isinstance(self.action_table[(i, c)], LRReduce) else 'S/R'
                            raise GrammarError(f'Grammar is ambiguous ({kind} conflict)')
                        self.action_table[(i, c)] = LRReduce(self.g.rules.index(item.rule))

            for n in self.g.non_terminals:
                if n == self.g.starting_symbol(): continue
                j = self.state_trans.get((i, n))
                if j is not None:
                    self.goto_table[(i, n)] = j

if __name__ == '__main__':
    main()