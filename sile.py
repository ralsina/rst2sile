from collections import defaultdict

from docutils import nodes, writers
from roman import toRoman
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

def kill_node(self, node):
    node.children = []

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
            keys = [s.strip() for s in rule.selector.as_css().lower().split(',')]
            value = {}
            for dec in rule.declarations:
                name = dec.name
                # CSS synonyms
                if name.startswith('font-'):
                    name = name[5:]
                value[name] = dec.value.as_css()
            for k in keys:
                styles[k] = value

        self.styles = defaultdict(dict)
        self.styles.update(styles)

    def format_args(self, **kwargs):
        opts = ''
        if kwargs:
            opts = '[%s]' % ','.join('%s=%s' % (k, v)
                                     for k, v in kwargs.items())
        return opts

    def start_cmd(self, envname, **kwargs):
        opts = self.format_args(**kwargs)
        cmd = '\\%s%s{' % (envname, opts)
        self.doc.append(cmd)

    def end_cmd(self, _=None):
        self.doc.append('}')

    def start_env(self, envname, **kwargs):
        opts = ''
        if kwargs:
            opts = '[%s]' % ','.join('%s=%s' % (k, v)
                                     for k, v in kwargs.items())
        self.doc.append('\\begin%s{%s}' % (opts, envname))

    def end_env(self, envname):
        self.doc.append('\\end{%s}\n\n' % envname)

    def apply_classes(self, node):
        start = ''
        end = ''
        classes = ['.' + c for c in node.get('classes', [])]
        classes.insert(0, node.__class__.__name__)
        for cl in classes:
            s, e = css_to_sile(self.styles[cl])
            start +=s
            end += e
        self.doc.append(start)
        node._pending = end

    def close_classes(self, node):
        self.doc.append(node._pending)

    def visit_document(self, node):
        # TODO Handle packages better
        s, t = css_to_sile(self.styles['body'])
        self.doc.append('''\\begin[class=book]{document}
        \\script[src=packages/verbatim]
        \\script[src=packages/pdf]
        \\script[src=packages/color]
        \\script[src=packages/rules]
        \\define[command="verbatim:font"]{\\font%s}
        \\set[parameter=document.parskip,value=12pt]
        \\set[parameter=document.parindent,value=0pt]
        %s
        \n\n''' % (self.format_args(**self.styles['verbatim']), s))
        node._pending = t

    def depart_document(self, node):
        self.doc.append(node._pending)
        self.end_env('document')

    visit_paragraph = apply_classes

    def depart_paragraph(self, node):
        self.close_classes(node)
        self.doc.append('\n\n')

    visit_inline = apply_classes
    depart_inline = close_classes

    def visit_Text(self, node):
        text = sile_quote(node.astext())
        self.doc.append(text)

    def depart_Text(self, node):
        pass

    def visit_literal(self, node):
        s, t = css_to_sile(self.styles['literal'])
        self.doc.append(s)
        node._pending = t

    def depart_literal(self, node):
        self.doc.append(node._pending)

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

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    def visit_bullet_list(self, node):
        self.start_cmd(
            'set',
            parameter='document.lskip',
            value='%dpt' % (self.list_depth * 12 + 12))
        self.list_depth += 1

    def depart_bullet_list(self, node):
        self.end_cmd()
        self.list_depth -= 1

    def visit_list_item(self, node):
        # TODO: move the bullet out of the text flow (see pullquote and rebox packages)
        self.doc.append('%s ' % self.bullet_for_node(node))

    depart_list_item = noop

    visit_enumerated_list = visit_bullet_list
    depart_enumerated_list = depart_bullet_list

    def visit_block_quote(self, node):
        s, t = css_to_sile(self.styles['blockquote'])
        self.doc.append(s)
        node._pending = t

    def depart_block_quote(self, node):
        self.doc.append('%s\n\n' % node._pending)

    def visit_attribution(self, node):
        s, t = css_to_sile(self.styles['attribution'])
        self.doc.append(s)
        node._pending = t

    def depart_attribution(self, node):
        self.doc.append(node._pending)

    def visit_transition(self, node):
        # TODO: style
        self.doc.append('\n\n\\hrule[width=80%pw, height=0.5pt]\n\n')

    depart_transition = noop

    def visit_title(self, node):
        # TODO: do sections as macros because the book class is too limited
        # TODO: handle classes?
        if isinstance(node.parent, nodes.topic):  # Topic title
            s, t = css_to_sile(self.styles['topic-title'])
            self.doc.append(s)
            node._pending = t
        elif self.section_level == 0:  # Doc Title
            s, t = css_to_sile(self.styles['title'])
            self.doc.append(s)
            node._pending = t
        elif self.section_level == 1:
            self.start_cmd('chapter')
            node._pending='}'
        elif self.section_level == 2:
            self.start_cmd('section')
            node._pending='}'
        elif self.section_level == 3:
            self.start_cmd('subsection')
            node._pending='}'
        else:
            raise Exception('Too deep')

    def depart_title(self, node):
        self.close_classes(node)
        self.doc.append('\n\n')

    def visit_subtitle(self, node):
        if self.section_level == 0:  # Doc SubTitle
            self.doc.append('\\noindent')
            self.start_cmd('font', **self.styles['subtitle'])
        else:
            raise Exception('Too deep')
    depart_subtitle = depart_title

    visit_comment = kill_node
    depart_comment = noop

    # TODO: implement headers/footers at some point
    visit_decoration = kill_node
    depart_decoration = noop

    visit_figure = noop
    depart_figure = noop
    visit_image = noop
    depart_image = noop

    # TODO: implement raw SILE
    visit_raw = kill_node
    depart_raw = noop
    visit_topic = apply_classes
    depart_topic = close_classes
    visit_reference = noop
    depart_reference = noop

    def astext(self):
        return ''.join(self.doc)

    # Originally from rst2pdf
    def bullet_for_node(self, node):
        """Takes a node, assumes it's some sort of
           item whose parent is a list, and
           returns the bullet text it should have"""
        b = ""
        t = 'item'
        if node.parent.get('start'):
            start = int(node.parent.get('start'))
        else:
            start = 1

        if node.parent.get('bullet') or isinstance(node.parent,
                                                   nodes.bullet_list):
            b = node.parent.get('bullet', '*')
            if b == "None":
                b = ""
            t = 'bullet'

        elif node.parent.get('enumtype') == 'arabic':
            b = str(node.parent.children.index(node) + start) + '.'

        elif node.parent.get('enumtype') == 'lowerroman':
            b = toRoman(node.parent.children.index(node) + start).lower() + '.'
        elif node.parent.get('enumtype') == 'upperroman':
            b = toRoman(node.parent.children.index(node) + start).upper() + '.'
        elif node.parent.get('enumtype') == 'loweralpha':
            b = string.lowercase[node.parent.children.index(node) +
                                 start - 1] + '.'
        elif node.parent.get('enumtype') == 'upperalpha':
            b = string.uppercase[node.parent.children.index(node) +
                                 start - 1] + '.'
        else:
            log.critical("Unknown kind of list_item %s [%s]", node.parent,
                         nodeid(node))
        return b


def sile_quote(text):
    return text.translate(
        str.maketrans({
            '{': '\\{',
            '}': '\\}',
            '%': '\\%',
            '\\': '\\\\'
        }))


def css_to_sile(style):
    """Given a CSS-like style, create a SILE environment."""

    font_keys = {'script', 'language','style', 'weight', 'family', 'size'}
    margin_keys = {'margin-left', 'margin-right', 'margin-top', 'margin-bottom'}

    keys = set(style.keys())
    has_font = bool(keys.intersection(font_keys))
    has_alignment = 'text-align' in keys
    has_color = 'color' in keys
    has_margin = bool(keys.intersection(margin_keys))
    has_indent = 'text-indent' in keys

    start = ''
    trailer = ''

    if has_alignment:
        value = style['text-align']
        if value == 'right':
            start += '\\begin{raggedleft}'
            trailer = '\\end{raggedleft}' + trailer
        elif value == 'center':
            start += '\\begin{center}'
            trailer = '\\end{center}' + trailer
        elif value in ['left']:
            start += '\\begin{raggedright}'
            trailer = '\\end{raggedright}' + trailer
        # Fully justified is default

    if has_margin:
        if 'margin-right' in keys:
            start += '\\set[parameter=document.rskip,value=%s]' % style['margin-right']
            trailer = '\\set[parameter=document.rskip,value=0]' + trailer
        if 'margin-left' in keys:
            start += '\\set[parameter=document.lskip,value=%s]' % style['margin-left']
            trailer = '\\set[parameter=document.lskip,value=0]' + trailer
        if 'margin-top' in keys:
            start += '\\skip[height=%s]' % style['margin-top']
        if 'margin-bottom' in keys:
            trailer = '\\skip[height=%s]' % style['margin-bottom'] + trailer

    if has_font:
        opts = ','.join('%s=%s' % (k,style[k]) for k in font_keys if k in style)
        s = '\\font[%s]{' % opts
        start += s
        trailer = '}' + trailer

    if has_color:
        start += '\\color[color=%s]{' % style['color']
        trailer = '}' + trailer

    if has_indent:
        start += '\\set[parameter=document.parindent,value=%s]' % style['text-indent']

    return start, trailer
