from collections import defaultdict
import glob
import os
import string
import subprocess
import sys
import tempfile
import textwrap

from docutils import frontend, languages, nodes, writers
from docutils.parsers.rst import directives
from roman import toRoman
import tinycss

CSS_FILE = os.path.join(os.path.dirname(__file__), 'styles.css')
SILE_PATH = os.path.join(os.path.dirname(__file__), 'packages', '*.lua')

# Units allowed by SILE are different
directives.length_units = [
    'pt', 'mm', 'cm', 'in', '%pw', '%ph', '%fw', '%fh', '%lw', '%pmax',
    '%pmin', '%fmax', '%fmin'
]


def debug(*_):
    import pdb
    pdb.set_trace()


class Writer(writers.Writer):

    settings_spec = ('SILE-Specific Options', None, (
        ('Specify the CSS files (comma separated).  Default is "%s".' %
         CSS_FILE, ['--stylesheets'], {
             'default': CSS_FILE,
             'metavar': '<file>'
         }), ('Table of contents by Docutils (without page numbers). ',
              ['--use-docutils-toc'], {
                  'dest': 'use_docutils_toc',
                  'action': 'store_true',
                  'validator': frontend.validate_boolean,
                  'default': False
              }), ))

    def __init__(self):
        super(Writer, self).__init__()
        self.translator_class = SILETranslator

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()


def noop(*_):
    pass


def kill_node(*_):
    raise nodes.SkipNode


class SILETranslator(nodes.NodeVisitor):
    def __init__(self, document):
        super(SILETranslator, self).__init__(document)
        self.settings = document.settings
        lcode = self.settings.language_code
        self.language = languages.get_language(lcode, document.reporter)
        self.doc = []
        self.section_level = 0
        self.list_depth = 0

        self.use_docutils_toc = self.settings.use_docutils_toc

        # Pre-load all custom packages to simplify package path / loading
        self.package_code = []
        for package in glob.glob(SILE_PATH):
            p_name = os.path.splitext(package)[0]
            p_name = os.path.join('packages', os.path.basename(p_name))
            self.package_code.append(
                '\\script[src="%s"]\n' % p_name)

        css_parser = tinycss.make_parser('page3')
        stylesheets = self.document.settings.stylesheets.split(',')
        self.styles = defaultdict(dict)
        for ssheet in stylesheets:
            rules = css_parser.parse_stylesheet_file(ssheet).rules
            styles = {}
            for rule in rules:
                keys = [
                    s.strip()
                    for s in rule.selector.as_css().lower().split(',')
                ]
                value = {}
                for dec in rule.declarations:
                    name = dec.name
                    # CSS synonyms
                    if name.startswith('font-'):
                        name = name[5:]
                    value[name] = dec.value.as_css()
                for k in keys:
                    styles[k] = value
            self.styles.update(styles)

    def start_cmd(self, envname, **kwargs):
        opts = format_args(**kwargs)
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
        for classname in classes:
            head, tail = css_to_sile(self.styles[classname])
            start += head
            end = tail + end
        self.doc.append(start)
        node.pending_tail = end

    def close_classes(self, node):
        self.doc.append(node.pending_tail)

    def visit_document(self, node):
        # TODO Handle packages better
        head, tail = css_to_sile(self.styles['body'])

        scripts = ''.join(self.package_code)

        self.doc.append('''\\begin[class=book]{document}
        \\script[src=packages/verbatim]
        \\script[src=packages/color]
        \\script[src=packages/rules]
        \\script[src=packages/pdf]
        \\script[src=packages/image]
        \\define[command="verbatim:font"]{\\font%s}
        \\set[parameter=document.parskip,value=12pt]
        \\set[parameter=document.parindent,value=0pt]
        %s
        %s
        \n\n''' % (format_args(**self.styles['verbatim']), scripts, head))
        node.pending_tail = tail

    def depart_document(self, node):
        self.doc.append(node.pending_tail)
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
        head, tail = css_to_sile(self.styles['literal'])
        self.doc.append(head)
        node.pending_tail = tail

    def depart_literal(self, node):
        self.doc.append(node.pending_tail)

    def visit_emphasis(self, _):
        self.start_cmd('em')

    depart_emphasis = end_cmd

    def visit_strong(self, _):
        self.start_cmd('font', weight=800)

    depart_strong = end_cmd

    def visit_literal_block(self, _):
        # FIXME: this has horrible vertical separations
        self.start_env('verbatim')

    def depart_literal_block(self, _):
        self.end_env('verbatim')

    def visit_section(self, _):
        self.section_level += 1

    def depart_section(self, _):
        self.section_level -= 1

    def visit_bullet_list(self, _):
        if self.list_depth:
            self.start_cmd('relindent', left="3em")
        self.list_depth += 1

    def depart_bullet_list(self, _):
        self.list_depth -= 1
        if self.list_depth:
            self.end_cmd()

    def visit_list_item(self, node):
        # TODO: move the bullet out of the text
        # flow (see pullquote and rebox packages)
        bullet = bullet_for_node(node)
        bullets = {
            '*': '\u2022',
            '-': '\u25e6',
            '+': '\u2023',
        }
        bullet = bullets.get(bullet, bullet)
        self.doc.append('%s ' % bullet)

    depart_list_item = noop

    visit_enumerated_list = visit_bullet_list
    depart_enumerated_list = depart_bullet_list

    visit_block_quote = apply_classes

    def depart_block_quote(self, node):
        self.doc.append('%s\n\n' % node.pending_tail)

    visit_attribution = apply_classes
    depart_attribution = close_classes

    def visit_transition(self, _):
        # TODO: style
        self.doc.append('\n\n\\hrule[width=100%fw, height=0.5pt]\n\n')

    depart_transition = noop

    def add_target(self, target_id):
        self.start_cmd('pdf:destination', name=target_id)
        self.end_cmd()

    def visit_title(self, node):
        # TODO: do sections as macros because the book class is too limited
        # TODO: handle classes?

        if isinstance(node.parent, nodes.topic):  # Topic title
            head, tail = css_to_sile(self.styles['topic-title'])
            self.doc.append(head)
            node.pending_tail = tail
        elif isinstance(node.parent, nodes.sidebar):  # Sidebar title
            head, tail = css_to_sile(self.styles['sidebar-title'])
            self.doc.append(head)
            node.pending_tail = tail
        elif self.section_level == 0:  # Doc Title
            head, tail = css_to_sile(self.styles['title'])
            self.doc.append(head)
            node.pending_tail = tail
        elif self.section_level == 1:
            self.start_cmd('chapter')
            node.pending_tail = '}'
        elif self.section_level == 2:
            self.start_cmd('section')
            node.pending_tail = '}'
        elif self.section_level == 3:
            self.start_cmd('subsection')
            node.pending_tail = '}'
        else:
            raise Exception('Too deep')
        # target for this title
        if 'refid' in node:
            self.add_target(node['refid'])
        # targets for the section in which this title is
        if isinstance(node.parent, nodes.section):
            for node_id in node.parent['ids']:
                self.add_target(node_id)

    def depart_title(self, node):
        self.close_classes(node)
        self.doc.append('\n\n')

    def visit_subtitle(self, node):
        if self.section_level == 0:  # Doc SubTitle
            self.apply_classes(node)
        else:
            raise Exception('Too deep')

    depart_subtitle = depart_title

    visit_comment = kill_node
    depart_comment = noop

    visit_sidebar = apply_classes
    depart_sidebar = close_classes

    # TODO: implement headers/footers at some point
    visit_decoration = kill_node
    depart_decoration = noop

    # TODO: implement raw SILE
    def visit_raw(self, node):
        if node['format'] != 'sile':
            raise nodes.SkipNode
        else:
            self.doc.append(node.astext())
            raise nodes.SkipChildren

    depart_raw = noop

    def visit_topic(self, node):
        self.apply_classes(node)
        if 'contents' in node['classes']:
            # FIXME: Contents is not in TOC
            # FIXME: native TOC has no links
            # FIXME: last item in the TOC is shorter (?!)
            if not self.use_docutils_toc:
                self.start_cmd('define', command='tableofcontents:title')
                self.doc.append(node.next_node().astext())
                self.end_cmd()
                for command, style in {
                        "tableofcontents:headerfont": 'toc-header',
                        "tableofcontents:level1item": 'toc-l1',
                        "tableofcontents:level2item": 'toc-l2',
                        "tableofcontents:level3item": 'toc-l3'
                }.items():
                    self.start_cmd('define', command=command)
                    head, tail = css_to_sile(self.styles[style])
                    self.doc.append(head)
                    self.doc.append('\\process\\break')
                    self.doc.append(tail + '\n')
                    self.end_cmd()
                node.pending_tail = '\\tableofcontents' + node.pending_tail
                raise nodes.SkipChildren

    depart_topic = close_classes

    visit_docinfo = apply_classes
    depart_docinfo = close_classes

    def visit_docinfo_node(self, node, name):
        # FIXME: classes are not right
        self.doc.append(self.language.labels[name])
        self.doc.append(': ')
        self.doc.append(node.astext() + '\\break ')
        raise nodes.SkipNode

    def depart_docinfo_node(self, node):
        pass

    # FIXME: text alignments are tricky
    visit_field_list = apply_classes
    depart_field_list = close_classes
    visit_field = apply_classes
    depart_field = close_classes

    visit_field_name = apply_classes

    def depart_field_name(self, node):
        self.doc.append(': ')
        self.close_classes(node)

    visit_field_body = apply_classes
    depart_field_body = close_classes

    def visit_author(self, node):
        self.visit_docinfo_node(node, 'author')

    depart_author = depart_docinfo_node

    def visit_date(self, node):
        self.visit_docinfo_node(node, 'date')

    depart_date = depart_docinfo_node

    def visit_version(self, node):
        self.visit_docinfo_node(node, 'version')

    depart_version = depart_docinfo_node

    def visit_copyright(self, node):
        self.visit_docinfo_node(node, 'copyright')

    depart_copyright = depart_docinfo_node

    def visit_admonition(self, node, name):
        # TODO: handle specific classes like "note" or "warning"
        head1, tail1 = css_to_sile(self.styles['admonition'])
        self.doc.append(head1)
        if name:
            head2, tail2 = css_to_sile(self.styles['admonition-title'])
            self.doc.append(head2)
            self.doc.append(name)
            self.doc.append(tail2)
        node.pending_tail = tail1

    def visit_attention(self, node):
        self.visit_admonition(node, 'Attention')

    depart_attention = close_classes

    def visit_caution(self, node):
        self.visit_admonition(node, 'Caution')

    depart_caution = close_classes

    def visit_danger(self, node):
        self.visit_admonition(node, 'Danger')

    depart_danger = close_classes

    def visit_error(self, node):
        self.visit_admonition(node, 'Error')

    depart_error = close_classes

    def visit_hint(self, node):
        self.visit_admonition(node, 'Hint')

    depart_hint = close_classes

    def visit_important(self, node):
        self.visit_admonition(node, 'Important')

    depart_important = close_classes

    def visit_note(self, node):
        self.visit_admonition(node, 'Note')

    depart_note = close_classes

    def visit_tip(self, node):
        self.visit_admonition(node, 'Tip')

    depart_tip = close_classes

    def visit_warning(self, node):
        self.visit_admonition(node, 'Warning')

    depart_warning = close_classes

    # TODO: links, footnote refs have a bad left-space
    def visit_footnote_reference(self, node):
        self.start_cmd('raise', height='.5em')
        self.apply_classes(node)

    def depart_footnote_reference(self, node):
        self.end_cmd()
        self.close_classes(node)

    visit_citation_reference = visit_footnote_reference
    depart_citation_reference = depart_footnote_reference

    def visit_footnote(self, node):
        self.start_cmd('footnote')
        self.apply_classes(node)

    def depart_footnote(self, node):
        self.end_cmd()
        self.close_classes(node)

    visit_citation = visit_footnote
    depart_citation = depart_footnote

    def visit_label(self, node):
        self.apply_classes(node)

    def depart_label(self, node):
        self.doc.append('.  ')
        self.close_classes(node)

    visit_system_message = apply_classes
    depart_system_message = close_classes

    def astext(self):
        sile_code = ''.join(self.doc)
        if sys.argv[0].endswith('rst2pdf'):
            with tempfile.NamedTemporaryFile('w', delete=False) as sil_file:
                sil_file.write(sile_code)
                pdf_path = sil_file.name + '.pdf'
                toc_path = sil_file.name + '.toc'
                env = os.environ.copy()
                env['SILE_PATH'] = os.path.dirname(__file__)
                subprocess.check_call(
                    ['sile', sil_file.name, '-o', pdf_path], env=env)
                if os.path.isfile(
                        toc_path
                ) and not self.use_docutils_toc:  # Need to run twice
                    subprocess.check_call(
                        ['sile', sil_file.name, '-o', pdf_path], env=env)
            with open(pdf_path, 'rb') as pdf_file:
                return pdf_file.read()
        else:
            return sile_code

    visit_definition_list = noop
    depart_definition_list = noop
    visit_definition_list_item = noop
    depart_definition_list_item = noop
    visit_definition = apply_classes
    depart_definition = close_classes
    visit_term = apply_classes

    def depart_term(self, node):
        self.close_classes(node)
        self.doc.append('\\break ')

    def visit_option_list(self, node):
        node.table = []

    def depart_option_list(self, node):
        self.start_env('verbatim')
        oplen = max(len(r[0]) for r in node.table) + 2
        for row in node.table:
            # The option itself
            option = row[0] + ' ' * (oplen - len(row[0]))
            if len(row) > 1:
                desclines = [line.strip() for line in row[1].splitlines()]
                self.doc.append(option + desclines[0] + '\n')
                for line in desclines[1:]:
                    self.doc.append(' ' * oplen + line + '\n')
            else:
                self.doc.append(option + '\n')
        self.end_env('verbatim')

    visit_option_group = noop
    depart_option_group = noop

    @staticmethod
    def visit_option(node):
        listnode = node.parent.parent.parent
        listnode.table.append([node.astext()])
        raise nodes.SkipChildren()

    depart_option = noop
    visit_option_string = kill_node
    depart_option_string = noop

    @staticmethod
    def visit_description(node):
        listnode = node.parent.parent
        listnode.table[-1].append('\n'.join(textwrap.wrap(node.astext(), 40)))
        raise nodes.SkipChildren()

    depart_description = noop
    visit_option_argument = noop
    depart_option_argument = noop
    visit_option_list_item = noop
    depart_option_list_item = noop

    def visit_reference(self, node):
        self.apply_classes(node)
        if 'refuri' in node:
            self.start_cmd('pdf:link', dest=node['refuri'], external="true")
        else:
            self.start_cmd('pdf:link', dest=node['refid'])

    def depart_reference(self, node):
        self.end_cmd()
        self.close_classes(node)

    def visit_target(self, node):
        self.add_target(node['refid'])

    depart_target = end_cmd

    def visit_image(self, node):
        self.apply_classes(node)
        args = {'src': node['uri']}
        if 'width' in node:
            args['width'] = node['width']
            if args['width'].endswith('%'):
                args['width'] += 'fw'
        if 'height' in node:
            args['height'] = node['height']
        self.start_cmd('img', **args)

    def depart_image(self, node):
        self.end_cmd()
        self.close_classes(node)

    visit_figure = apply_classes
    depart_figure = close_classes
    visit_caption = apply_classes
    depart_caption = close_classes


# Originally from rst2pdf
def bullet_for_node(node):
    """Takes a node, assumes it's some sort of
        item whose parent is a list, and
        returns the bullet text it should have"""
    b = ""
    if node.parent.get('start'):
        start = int(node.parent.get('start'))
    else:
        start = 1

    if node.parent.get('bullet') or isinstance(node.parent, nodes.bullet_list):
        b = node.parent.get('bullet', '*')
        if b == "None":
            b = ""

    elif node.parent.get('enumtype') == 'arabic':
        b = str(node.parent.children.index(node) + start) + '.'

    elif node.parent.get('enumtype') == 'lowerroman':
        b = toRoman(node.parent.children.index(node) + start).lower() + '.'
    elif node.parent.get('enumtype') == 'upperroman':
        b = toRoman(node.parent.children.index(node) + start).upper() + '.'
    elif node.parent.get('enumtype') == 'loweralpha':
        b = string.ascii_lowercase[node.parent.children.index(node) +
                                   start - 1] + '.'
    elif node.parent.get('enumtype') == 'upperalpha':
        b = string.ascii_uppercase[node.parent.children.index(node) +
                                   start - 1] + '.'
    else:
        # FIXME log
        print("Unknown kind of list_item %s [%s]" % (node.parent, node))
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

    font_keys = {'script', 'language', 'style', 'weight', 'family', 'size'}
    margin_keys = {
        'margin-left', 'margin-right', 'margin-top', 'margin-bottom'
    }

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
            start += '\\relindent[right=%s]' % style['margin-right']
            trailer = '\\relindent[right=-%s]' % style['margin-right'] + trailer
        if 'margin-left' in keys:
            start += '\\relindent[left=%s]' % style['margin-left']
            trailer = '\\relindent[left=-%s]' % style['margin-left'] + trailer
        if 'margin-top' in keys:
            start += '\\skip[height=%s]' % style['margin-top']
        if 'margin-bottom' in keys:
            trailer = '\\skip[height=%s]' % style['margin-bottom'] + trailer

    if has_font:
        opts = ','.join('%s=%s' % (k, style[k]) for k in font_keys
                        if k in style)
        head = '\\font[%s]{' % opts
        start += head
        trailer = '}' + trailer

    if has_color:
        start += '\\color[color=%s]{' % style['color']
        trailer = '}' + trailer

    if has_indent:
        start += '\\set[parameter=document.parindent,value=%s]' % style[
            'text-indent']

    return start, trailer


def format_args(**kwargs):
    opts = ''
    if kwargs:
        opts = '[%s]' % ','.join('%s=%s' % (k, v) for k, v in kwargs.items())
    return opts
