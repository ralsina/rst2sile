from collections import defaultdict

from docutils import nodes, writers
import tinycss

class Writer(writers.Writer):
    pass

    def __init__(self):
        super(Writer, self).__init__()
        self.translator_class = SILETranslator

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()

def noop(self, node):
    pass

class SILETranslator(nodes.NodeVisitor):
    def __init__(self, document):
        super(SILETranslator, self).__init__(document)
        self.doc = []
        self.section_level = 0
        self.list_depth = 0
        css_parser = tinycss.make_parser('page3')
        rules = css_parser.parse_stylesheet_file('styles.css').rules
        styles = {}
        for rule in rules:
            key = rule.selector.as_css().lower()
            value = {}
            for dec in rule.declarations:
                name = dec.name
                # CSS synonyms
                if name.startswith('font-'):
                    name = name[5:]
                value[name] = dec.value.as_css()
            styles[key] = value

        default = styles['body'].copy()
        # for k in styles:
        #     v = {}
        #     v.update(default)
        #     v.update(styles[k])
        #     styles[k] = v

        self.styles = defaultdict(dict)
        self.styles.update(styles)

    def format_args(self, **kwargs):
        opts = ''
        if kwargs:
            opts = '[%s]' % ','.join('%s=%s' % (k,v) for k,v in kwargs.items())
        return opts

    def start_cmd(self, envname, **kwargs):
        # TODO: handle font specially, since color and alignment are separate commands.
        opts = self.format_args(**kwargs)
        cmd = '\\%s%s{' % (envname, opts)
        self.doc.append(cmd)
    def end_cmd(self, _=None):
        self.doc.append('}')

    def start_env(self, envname, **kwargs):
        opts = ''
        if kwargs:
            opts = '[%s]' % ','.join('%s=%s' % (k,v) for k,v in kwargs.items())
        self.doc.append('\\begin%s{%s}' % (opts, envname))
    def end_env(self, envname):
        self.doc.append('\\end{%s}\n\n' % envname)

    def visit_document(self, node):
        # TODO Handle packages better
        self.doc.append('''\\begin[class=book]{document}
        \\script[src=packages/verbatim]
        \\script[src=packages/pdf]
        \\script[src=packages/rules]
        \\define[command="verbatim:font"]{\\font%s}
        \n\n''' % self.format_args(**self.styles['verbatim']))

    def depart_document(self, node):
        self.end_env('document')

    def visit_paragraph(self, node):
        pass
    def depart_paragraph(self, node):
        self.doc.append('\n\n')

    def visit_Text(self, node):
        text = sile_quote(node.astext())
        self.doc.append(text)
    def depart_Text(self, node):
        pass

    def visit_literal(self, node):
        self.start_cmd('font', **self.styles['literal'])
    depart_literal = end_cmd

    def visit_emphasis(self, node):
        self.start_cmd('em')
    depart_emphasis = end_cmd

    def visit_strong(self, node):
        self.start_cmd('font', weight=800)
    depart_strong = end_cmd

    def visit_literal_block(self, node):
        self.start_env('verbatim')
    def depart_literal_block(self, node):
        self.end_env('verbatim')

    def visit_inline(self, node):
        for cl in node.get('classes', []):
            self.start_cmd('font', **self.styles['.' + cl])
    def depart_inline(self, node):
        for cl in node.get('classes', []):
            self.end_cmd()

    def visit_section(self, node):
        self.section_level += 1
    def depart_section(self, node):
        self.section_level -= 1

    def visit_bullet_list(self, node):
        self.start_cmd('set', parameter='document.lskip', value='%dpt' % (self.list_depth*12))
        self.list_depth += 1
    def depart_bullet_list(self, node):
        self.end_cmd()
        self.list_depth -= 1
    def visit_list_item(self, node):
        self.doc.append('* ')
    depart_list_item = noop

    visit_enumerated_list = visit_bullet_list
    depart_enumerated_list = depart_bullet_list

    def visit_transition(self, node):
        # TODO: style
        self.doc.append('\n\n\hrule[width=80%pw, height=0.5pt]\n\n')
    depart_transition = noop

    def visit_title(self, node):
        # TODO: do sections as macros because the book class is too limited
        if self.section_level == 0:  # Doc Title
            self.doc.append('\\noindent')
            self.start_cmd('font', **self.styles['title'])
        elif self.section_level == 1:
            self.start_cmd('chapter')
        elif self.section_level == 2:
            self.start_cmd('section')
        elif self.section_level == 3:
            self.start_cmd('subsection')
        else:
            raise Exception('Too deep')
    def depart_title(self, node):
        self.end_cmd()
        if self.section_level < 2:  # Doc Title
            self.doc.append('\\bigskip')
        else:
            self.doc.append('\\medskip')
        self.doc.append('\n\n')

    def visit_subtitle(self, node):
        if self.section_level == 0:  # Doc SubTitle
            self.doc.append('\\noindent')
            self.start_cmd('font', **self.styles['subtitle'])
        else:
            raise Exception('Too deep')
    depart_subtitle = depart_title

    def astext(self):
        return ''.join(self.doc)

def sile_quote(text):
    return text.translate(str.maketrans({
        '{': '\\{',
        '}': '\\}',
        '%': '\\%',
        '\\': '\\\\'
    }))
