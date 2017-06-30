=================
Rst2SILE Handbook
=================

----------------------------------------------------------------------------------------------
Or: there has to be a better way instead of me having to redo this crap every ten years or so.
----------------------------------------------------------------------------------------------

:Author: Roberto Alsina
:Version: 0.1
:Date: June 30, 2017

.. contents::

What is rst2SILE?
-----------------

It's a command to convert reStructuredText to PDFs via `SILE. <http://sile-typesetter.org>`__

Frustrated with the reliance on LaTeX exhibited by most other PDF-from-markup
tools, I googled for some modern alternatives, and found SILE. Not only does it
produce quality output, but you can learn most of it in a couple of hours, is
much easier to generate than LaTeX, and is quite hackable in a semi-reasonable
language (Lua). Really, SILE is a gem, and it worries me that it seems nobody
has heard of it.

So, ``rst2sile`` eats a ``.rst`` file and spits out a ``.sil`` file which you can process
further using SILE.

ON the other hand, as a convenience, ``rst2pdf`` eats a ``.rst`` file, and spits out a ``.pdf``
file, generated via SILE, which is probably what you want.


Is it production ready?
-----------------------

Hell no.

Known Issues
------------

* No tables.
* Footnotes/Citations are not hyperlinked.
* TOC is lame.
* Styling is limited.
* No support for page/frameset configuration yet.
* The used "book" class from SILE is only approximately adequate for this.

And surely much more.

How to use it?
--------------

Basic usage::

   rst2pdf foo.rst foo.pdf
   rst2sile foo.rst foo.sil

Not so basic usage::

   rst2sile --help

How do I style the output?
--------------------------

With the goal of making it as easy as possible to customize, rst2sile supports a
subset of CSS. By default it will use an included ``styles.css`` but you can use
custom ones via the ``--stylesheets`` option.

* It only supports "," as a selector connector. So this works::

     foo, bar { }

  But this doesn't::

     foo > bar {}
     foo bar {}

* It supports element selectors (all listed in the provided styles.css)
* It supports class selectors
* It doesn't support margins for inline elements such as classes in roles,
  or in syntax highlight.
* Sizes, such as ``font-size`` or ``margin-top`` can be expressed in the usual
  units but instead of "%" it's recommended to use "%fw / %fh" (percentage of frame
  width/height) "%pw / %ph" (percentage of page width/height)
* It only supports the following properties:

  * font-family
  * font-size
  * font-style
  * font-weight (has to be a number)
  * text-indent
  * text-align
  * margin-left
  * margin-right
  * margin-top
  * margin-bottom
  * language (for hyphenation. Special value "und" means no language)
  * script (for hyphenation and layout)
  * color

Motivation, in the form of exasperated Q&A
------------------------------------------

**What do I want?**

I want to be able to write docs using some reasonable markup (like
reStructuredText) and produce a PDF while being able to configure things like
fonts and page layout. And world peace, but the PDF thing first.

**Why PDF?**

Because it's a format where I control the layout, and as long as anyone can
open it I can trust that he will see it in a reasonable manner with the right
font and so on.

**Why not (whatever other format)?**

Probably because:

* It would not be trivial to open for some people.
* It would not look exactly the way I want it to look.
* Some other reason.

**Why not use rst2latex.py?**

Because it uses LaTex and as soon as I want to do something *crazy* like
changing the font (woah) or the paper size (woohoo) I need to learn LaTex.

**Why not pandoc?**

See previous question.

**Why not LaTeX?**

Because it's not a reasonable markup.

**Why not markdown?**

Because it's too limited.

**Why not pandoc with markdown?**

Because it's LaTeX **and** markdown, and it's like trying to blow your foot off
using a large number of very small firecrackers.

**Why not LibreOffice and print to a PDF?**

Because yeech?

**Why not HTML+CSS and print to a PDF?**

Because why would a human want to write HTML+CSS? And then I have to put the
CSS in the HTML or else the recipient has to save two files.

**Why not reStructuredText and generate HTML and print to PDF?**

For the holy third left hand of Shiva, that is crazytalk.

**Why not rst2pdf?**

Well, glad you ask! Because I wrote it 10 years ago and I can't believe it's
still, after years of becoming abandonware, still one of the easiest ways to
turn markup into PDFs without having to install 700MB of obscure 1980s code to
implement **another different more complicated markup.**

Also, because I have become a much better programmer over the last 10 years,
and therefore it *pains* me to see all the problems rst2pdf has.

**So, what do you want to use, smartass?**

I want to use something that, apparently, doesn't exist. Therefore, I wrote
this **new** piece of software.

License
-------

MIT License

Copyright (c) 2017 Roberto Alsina

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

