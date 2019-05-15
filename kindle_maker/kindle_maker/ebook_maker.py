# coding=utf8

import io
import os
import sys
import uuid
import datetime
import shutil
import tempfile
from jinja2 import Environment, FileSystemLoader

templates_env = Environment(loader=FileSystemLoader('%s/templates/' % os.path.dirname(os.path.realpath(__file__))))

_default_output_dir = os.path.join(tempfile.gettempdir(), 'kindle_maker')


def render_file(template_name, context, output_name, output_dir):
    template = templates_env.get_template(template_name)
    with io.open(os.path.join(output_dir, output_name), mode="w", encoding='utf-8') as f:
        f.write(template.render(**context))


def render_toc_ncx(headers, output_dir, title=None, author=None):
    """

    :param headers:
    :param output_dir:
    :param title:
    :param author:
    :return:
    """
    render_file(
        'toc.xml',
        {
            'headers': headers,
            'title': title or 'jachinlin.github.io' + str(datetime.date.today()),
            'author': author or 'jachinlin.github.io'
        },
        'toc.ncx',
        output_dir
    )


def render_toc_html(headers, output_dir):
    """

    :param headers:
    :param output_dir:
    :return:
    """
    render_file('toc.html', {'headers': headers}, 'toc.html', output_dir)


def render_opf(headers, title, output_dir, author=None):
    """

    :param headers:
    :param title:
    :param output_dir:
    :param author:
    :return:
    """
    render_file('opf.xml', {'headers': headers, 'title': title,
                            'author': author or 'jachinlin.github.io'}, '{}.opf'.format(title), output_dir)


def parse_headers(toc_file_name):
    """

    :param toc_file_name:
    :return:
    """
    headers_info = []

    with io.open(toc_file_name, mode='r', encoding='utf-8') as f:
        headers = f.readlines()
        order = 1
        if not headers:
            return None, None
        title_line = 0
        while (not headers[title_line].strip()) or title_line == len(headers):
            title_line += 1

        if title_line == len(headers):
            return None, None

        title = headers[title_line].strip()

        for h in headers[title_line + 1:]:
            if h.startswith('# '):
                order += 1
                headers_info.append({
                    'title': h[2:].strip(),
                    'play_order': order,
                    'next_headers': []
                })

            if h.startswith('## '):
                if len(headers) == 0:
                    continue
                order += 1
                headers_info[-1]['next_headers'].append({
                    'title': h[2:].strip(),
                    'play_order': order,
                })

    return title, headers_info


def make_toc_html(tmp_dir, headers):
    if os.path.exists(os.path.join(tmp_dir, 'toc.html')):
        return
    cover_file_name = os.path.join(tmp_dir, 'cover.jpg')
    if not os.path.isfile(cover_file_name):
        cover = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates', 'cover.jpg')
        shutil.copy(cover, tmp_dir)
    # render toc.ncx file
    render_toc_ncx(headers, tmp_dir)
    # render toc.html file
    render_toc_html(headers, tmp_dir)


def get_toc_title_and_headers(tmp_dir):
    toc_file_name = os.path.join(tmp_dir, 'toc.md')
    if not os.path.isfile(toc_file_name):
        raise ValueError('not exists toc md file')
    return parse_headers(toc_file_name)


def make_ebook(source_dir, output_dir=None, make_mobi=False, link_html=True):
    """
    make ebook with the files in source_dir and put the ebook made in output_dir
    """
    output_dir = output_dir or _default_output_dir
    tmp_dir = source_dir
    title, headers = get_toc_title_and_headers(tmp_dir)
    make_toc_html(tmp_dir, headers)
    if make_mobi:
        # make a tmp dir in output_dir
        tmp_dir = os.path.join(output_dir, str(uuid.uuid4()))
        # copy source files to tmp dir
        shutil.copytree(source_dir, tmp_dir)
        # render opf file
        render_opf(headers, title, tmp_dir)
        # make mobi ebook in tmp dir
        opf_file = os.path.join(tmp_dir, title + '.opf')
        mobi_file = os.path.join(tmp_dir, title + '.mobi')
        os.system("%s -dont_append_source %s" % ('kindlegen', opf_file))
        # copy mobi file to output dir
        os.system("cp %s %s" % (mobi_file, output_dir))
        # remove tmp dir
        shutil.rmtree(tmp_dir)
    if link_html:
        link_toc_html(tmp_dir, output_dir, title)


def link_toc_html(tmp_dir, output_dir, title):
    html_file = f"{os.path.join(output_dir, title + '.html')}"
    toc_path = os.path.relpath(tmp_dir, output_dir)
    if not os.path.exists(html_file):
        os.system(f"ln -s {os.path.join(toc_path, 'toc.html')}  {html_file}")


def make_mobi_command():
    args = sys.argv[1:]
    if len(args) < 2:
        print("""make_mobi usage:
1. prepare html files and a toc.md file in a source dir, and then call 
2. make_mobi <source_dir> <ogitutput_dir>
        """)
        return

    make_ebook(args[0], args[1])

    print("success")
