#!/usr/bin/env python3
"""Enable the theme in a pwnagotchi config.toml, whatever style it uses.

pwnagotchi accepts two layouts for the same settings:

    flat        main.plugins.neuromancer.enabled = true
    sections    [main.plugins.neuromancer]
                enabled = true

and it rewrites configs into the section form on its own. Appending a flat key
to a file that uses sections would silently attach it to the last section, so
the plugin would never be enabled. This picks the right form.

    configure.py <config.toml> enable   -> turn the theme on
    configure.py <config.toml> disable  -> turn it off, restore the language

Prints the previous language on enable, so the installer can record it.
"""

import re
import sys


def read_plugins_dir(text):
    """Where this config says custom plugins live, in either layout.

    Flat files spell it `main.custom_plugins = "..."`; section files put a
    bare `custom_plugins` under [main]. Reading only the flat form silently
    installed the plugin into the wrong directory on releases that ship the
    section form, and pwnagotchi never loaded it.
    """
    if uses_sections(text):
        main = re.search(r'^\[main\]\s*$(.*?)(?=^\[|\Z)', text, re.M | re.S)
        if main:
            m = re.search(r'^\s*custom_plugins\s*=\s*"([^"]+)"', main.group(1), re.M)
            return m.group(1) if m else None
        return None
    m = re.search(r'^\s*main\.custom_plugins\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else None


def dedupe(body, key):
    """Drop repeated `key = ...` lines from a section body, keeping the first.

    Earlier versions of this script appended a second copy every time the
    installer ran over an already-configured file, which makes the TOML
    invalid ("Cannot overwrite a value") and stops pwnagotchi reading it.
    Repair those files rather than only avoiding new ones.
    """
    seen = False
    out = []
    for line in body.split('\n'):
        if re.match(r'^\s*%s\s*=' % key, line):
            if seen:
                continue
            seen = True
        out.append(line)
    return '\n'.join(out)


def uses_sections(text):
    return not re.search(r'^main\.[a-z]', text, re.M)


def read_lang(text):
    if uses_sections(text):
        # 'lang' inside the [main] section, before the next section header
        main = re.search(r'^\[main\]\s*$(.*?)(?=^\[|\Z)', text, re.M | re.S)
        if main:
            m = re.search(r'^\s*lang\s*=\s*"([^"]+)"', main.group(1), re.M)
            return m.group(1) if m else None
        return None
    m = re.search(r'^\s*main\.lang\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else None


def set_lang(text, value):
    if uses_sections(text):
        def repl(match):
            # count the substitutions rather than compare the text: rewriting a
            # key to the value it already holds changes nothing, and comparing
            # would read that as "key absent" and append a duplicate
            body, n = re.subn(r'^(\s*lang\s*=\s*)"[^"]*"',
                              r'\g<1>"%s"' % value, match.group(1), count=1,
                              flags=re.M)
            if not n:                             # no lang key yet
                body = '\nlang = "%s"' % value + body
            return '[main]' + dedupe(body, 'lang')
        new, n = re.subn(r'^\[main\]\s*$(.*?)(?=^\[|\Z)', repl, text, count=1,
                         flags=re.M | re.S)
        if n:
            return new
        return text.rstrip() + '\n\n[main]\nlang = "%s"\n' % value

    if re.search(r'^\s*main\.lang\s*=', text, re.M):
        return re.sub(r'^\s*main\.lang\s*=.*$', 'main.lang = "%s"' % value,
                      text, count=1, flags=re.M)
    return text.rstrip() + '\nmain.lang = "%s"\n' % value


def set_plugin(text, enabled):
    flag = 'true' if enabled else 'false'
    if uses_sections(text):
        section = re.search(r'^\[main\.plugins\.neuromancer\]\s*$(.*?)(?=^\[|\Z)',
                            text, re.M | re.S)
        if section:
            # same trap as in set_lang: re-enabling an already enabled plugin
            # leaves the text untouched, which must not be read as "key absent"
            body, n = re.subn(r'^(\s*enabled\s*=\s*).*$', r'\g<1>%s' % flag,
                              section.group(1), count=1, flags=re.M)
            if not n:
                body = '\nenabled = %s' % flag + body
            return text.replace(section.group(0),
                                '[main.plugins.neuromancer]' + dedupe(body, 'enabled'), 1)
        return text.rstrip() + '\n\n[main.plugins.neuromancer]\nenabled = %s\n' % flag

    if re.search(r'^\s*main\.plugins\.neuromancer\.enabled\s*=', text, re.M):
        return re.sub(r'^\s*main\.plugins\.neuromancer\.enabled\s*=.*$',
                      'main.plugins.neuromancer.enabled = %s' % flag,
                      text, count=1, flags=re.M)
    return text.rstrip() + '\nmain.plugins.neuromancer.enabled = %s\n' % flag


def main():
    if len(sys.argv) not in (3, 4) or sys.argv[2] not in ('enable', 'disable',
                                                         'plugins-dir'):
        sys.exit('usage: configure.py <config.toml> enable|disable|plugins-dir '
                 '[restore-lang]')
    path, action = sys.argv[1], sys.argv[2]
    text = open(path, encoding='utf-8').read()

    if action == 'plugins-dir':
        print(read_plugins_dir(text) or '')
        return

    style = 'sections' if uses_sections(text) else 'flat'
    previous = read_lang(text)

    if action == 'enable':
        text = set_plugin(text, True)
        if previous != 'neuromancer':
            text = set_lang(text, 'neuromancer')
            print('PREVIOUS_LANG=%s' % (previous or ''))
        else:
            print('PREVIOUS_LANG=')
    else:
        text = set_plugin(text, False)
        restore = sys.argv[3] if len(sys.argv) > 3 else 'en'
        if previous == 'neuromancer':
            text = set_lang(text, restore)

    open(path, 'w', encoding='utf-8').write(text)
    print('STYLE=%s' % style)


if __name__ == '__main__':
    main()
