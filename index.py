from pyscript import document, when, window
from impl.syntax import PredParser, parse_bnf
import html

EPSILON = 'ϵ'

def log(*args):
    window.console.log(*[x if isinstance(x, str) else repr(x) for x in args])

def fmt_set(terms):
    l = []
    for t in sorted(terms):
        if t == '': t = EPSILON
        elif t in '{},();': t = f'\'{t}\''
        l.append(t)
    return '{' + ', '.join(l) + '}'

def escaped_fmt(fmt: str, *args):
    return fmt.format(*[html.unescape(str(x)) for x in args])

parser: PredParser | None = None

@when("click", "#btn-execute")
def click_handler(_event):
    global parser
    document.querySelector('my-result').style.display = 'none'
    for n in document.querySelectorAll('.py-error'):
        n.remove()

    grammar_raw = document.getElementById('ipt-grammar').value
    try:
        gm = parse_bnf(grammar_raw)
    except Exception as e:
        window.console.error("Error when parsing BNF", str(e))
        return

    parser = PredParser(gm)

    rule_list = document.getElementById('rule-list')
    new_html = ''
    for rule in gm.rules:
        new_html += escaped_fmt('<li>{}</li>\n', str(rule))
    rule_list.innerHTML = new_html

    tb_body = document.getElementById('table-first-follow').querySelector('tbody')
    new_html = ''
    for nt in gm.non_terminals:
        first = parser.first([nt])
        follow = parser.follow(nt)

        row = escaped_fmt(
            '<tr><td>{}</td><td>{}</td><td>{}</td></tr>',
            nt, fmt_set(first), fmt_set(follow)
        )
        new_html += row + '\n'
    tb_body.innerHTML = new_html

    parser.build_table()
    show_table(parser, rules_as_idx=document.getElementById('ipt-table-rule-idx').checked)

    document.querySelector('my-result').style.display = ''

@when("change", "#ipt-table-rule-idx")
def click_handler(event):
    active = event.target.checked
    if parser:
        show_table(parser, rules_as_idx=active)

def show_table(parser: PredParser, rules_as_idx: bool):
    gm = parser.g
    big_table = document.getElementById('table-pred')

    ext_terminals = [*gm.terminals, '$']
    head_html = ''.join(escaped_fmt('<th>{}</th>', t) for t in ext_terminals)
    head_html = f'<thead><tr><th></th>{head_html}</tr></thead>'

    body_html = ''
    for nt in gm.non_terminals:
        row = escaped_fmt('<th>{}</th>', nt)
        for t in ext_terminals:
            rule = parser.table.get((nt, t))
            if rule is None:
                text = ''
            elif rules_as_idx:
                text = str(gm.rules.index(rule) + 1)
            else:
                text = str(rule)
            row += escaped_fmt('<td>{}</td>', text)
        body_html += f'<tr>{row}</tr>'
    body_html = f'<tbody>{body_html}</tbody>'

    big_table.innerHTML = head_html + body_html