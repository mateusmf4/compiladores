import sys
from dataclasses import dataclass
from typing import TypeVar

def main():
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

T = TypeVar('T')

@dataclass
class Rule:
    name: str
    body: list[str]

    def __str__(self) -> str:
        return f'{self.name} → {" ".join(self.body)}'

@dataclass
class Grammar:
    rules: list[Rule]
    # ordered in order of appearance
    non_terminals: list[str]
    terminals: list[str]
    rule_map: dict[str, list[Rule]]

    def is_terminal(self, s: str):
        return s == '' or s in self.terminals

    def is_non_terminal(self, s: str):
        return s in self.non_terminals

    def starting_symbol(self):
        return self.rules[0].name

def parse_bnf(text: str) -> Grammar:
    g = Grammar([], [], [], {})
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        if line[0] == '#': continue

        name, body_str = map(str.strip, line.split('->', 1))
        body = body_str.split()
        if not body: body = ['']
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

class PredParser:
    g: Grammar
    first_map: dict[tuple[str, ...], set[str]]
    follow_map: dict[str, set[str]]
    table: dict[tuple[int, int], Rule]

    def __init__(self, g: Grammar):
        self.g = g
        self.first_map = {}
        self.follow_map = {}
        self.table = {}

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

    def follow(self, nt: str, visited: set[int] = None) -> set[str]:
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

    def build_table(self):
        for rule in self.g.rules:
            f = self.first(rule.body)
            for s in f - {''}:
                self.table[(rule.name, s)] = rule
            if '' in f:
                for s in self.follow(rule.name):
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
                raise Exception(f'parse error: wanted \"{top}\", got \"{a}\"')
            elif (top, a) not in self.table:
                raise Exception(f'parse error: got \"{a}\" while parsing \"{top}\"')
            else:
                rule = self.table[(top, a)]
                out_rules.append(rule)
                stack.pop()
                for Y in reversed(rule.body):
                    if Y: stack.append(Y)

        return out_rules

if __name__ == '__main__':
    main()