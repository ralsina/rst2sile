from docutils import nodes, writers

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

    def start_cmd(self, envname, **kwargs):
        opts = ''
        if kwargs:
            opts = '[%s]' % ','.join('%s=%s' % (k,v) for k,v in kwargs.items())
        self.doc.append('\\%s%s{' % (envname, opts))
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
        \script[src=packages/verbatim]
        \script[src=packages/pdf]
        \script[src=packages/color]
        ''')
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
        self.start_cmd('code')
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
        # TODO: implement class
        pass
    def depart_inline(self, node):
        pass

    def visit_section(self, node):
        self.section_level += 1
    def depart_section(self, node):
        self.section_level -= 1

    def visit_title(self, node):
        # TODO: do titles using class
        if self.section_level == 0:  # Doc Title
            self.start_cmd('color', color='red')
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
        self.doc.append('\n\n')

    visit_subtitle = visit_title
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