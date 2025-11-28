from pyscript import document, when, window
from impl.syntax import PredParser, parse_bnf, Grammar, SLRParser, LRAccept, LRShift, LRReduce, ParserError, GrammarError
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
    document.querySelector('my-result').style.display = 'none'
    for n in document.querySelectorAll('.py-error'):
        n.remove()

    try:
        grammar_raw = document.getElementById('ipt-grammar').value
        try:
            gm = parse_bnf(grammar_raw)
        except Exception as e:
            raise Exception("Error when parsing BNF", str(e))

        if document.getElementById('ipt-algo-preditivo').checked:
            handle_pred(gm)
        elif document.getElementById('ipt-algo-slr').checked:
            handle_slr(gm)
    except RecursionError as e:
        error_handler(e)
    except Exception as e:
        error_handler(e)

def error_handler(e):
    if isinstance(e, RecursionError):
        msg = 'Houve uma recursão infinita ao calcular first ou follow (gramática tem recursão?)'
    elif isinstance(e, GrammarError):
        msg = f'Houve um erro na gramática: {str(e)}'
    elif isinstance(e, ParserError):
        msg = f'Houve um erro no parser: {str(e)}'
    else:
        msg = f'Houve um erro: {str(e)}'

    elem = document.querySelector('#error-dialog p')
    elem.textContent = msg
    document.getElementById('error-dialog').showModal()

def handle_pred(gm: Grammar):
    global parser
    parser = PredParser(gm)

    document.getElementById('table-first-follow').style.display = ''
    document.querySelector('label:has(> #ipt-table-rule-idx)').style.display = ''

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

def handle_slr(gm: Grammar):
    parser = SLRParser(gm)
    parser.build_states()
    parser.build_table()

    rule_list = document.getElementById('rule-list')
    new_html = ''
    for i, rule in enumerate(gm.rules):
        if i == 0:
            new_html += escaped_fmt('<li><u>{}</u></li>\n', str(rule))
        else:
            new_html += escaped_fmt('<li>{}</li>\n', str(rule))
    rule_list.innerHTML = new_html

    document.getElementById('table-first-follow').style.display = 'none'
    document.querySelector('label:has(> #ipt-table-rule-idx)').style.display = 'none'

    big_table = document.getElementById('table-pred')

    ext_terminals = [*gm.terminals, '$']
    non_terminals = [x for x in gm.non_terminals if x != gm.starting_symbol()]

    th_terminals = ''.join(escaped_fmt('<th>{}</th>', t) for t in ext_terminals)
    th_non_terms = ''.join(escaped_fmt('<th>{}</th>', t) for t in non_terminals)
    head_html = f'''<thead>
        <tr>
            <th></th>
            <th colspan="{len(ext_terminals)}">Action</th>
            <th colspan="{len(gm.non_terminals) - 1}">Goto</th>
        </tr>
        <tr>
            <th></th>
            {th_terminals}
            {th_non_terms}
        </tr>
    </thead>'''

    body_html = ''
    for i, _ in enumerate(parser.states):
        row = escaped_fmt('<th>{}</th>', i)
        for t in ext_terminals:
            action = parser.action_table.get((i, t))
            if action is None:
                text = ''
            elif isinstance(action, LRAccept):
                text = 'acc'
            elif isinstance(action, LRShift):
                text = f's{action.state}'
            elif isinstance(action, LRReduce):
                text = f'r{action.rule_idx}'
            row += escaped_fmt('<td>{}</td>', text)

        for nt in non_terminals:
            goto = parser.goto_table.get((i, nt))
            if goto is None:
                text = ''
            else:
                text = str(goto)
            row += escaped_fmt('<td>{}</td>', text)
        body_html += f'<tr>{row}</tr>'
    body_html = f'<tbody>{body_html}</tbody>'

    big_table.innerHTML = head_html + body_html

    document.querySelector('my-result').style.display = ''