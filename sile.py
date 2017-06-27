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


class SILETranslator(nodes.NodeVisitor):
    def __init__(self, document):
        super(SILETranslator, self).__init__(document)
        self.doc = []

    def visit_document(self, node):
        self.doc.append('\\begin{document}')
    def depart_document(self, node):
        self.doc.append('\\end{document}')

    def visit_paragraph(self, node):
        pass
    def depart_paragraph(self, node):
        self.doc.extend([''])

    def visit_Text(self, node):
        text = node.astext()
        self.doc.append(text)
    def depart_Text(self, node):
        pass

    def astext(self):
        return '\n'.join(self.doc)
