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
            body = re.sub(r'^(\s*lang\s*=\s*)"[^"]*"',
                          r'\g<1>"%s"' % value, match.group(1), count=1, flags=re.M)
            if body == match.group(1):            # no lang key yet
                body = '\nlang = "%s"' % value + body
            return '[main]' + body
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
            body = re.sub(r'^(\s*enabled\s*=\s*).*$', r'\g<1>%s' % flag,
                          section.group(1), count=1, flags=re.M)
            if body == section.group(1):
                body = '\nenabled = %s' % flag + body
            return text.replace(section.group(0),
                                '[main.plugins.neuromancer]' + body, 1)
        return text.rstrip() + '\n\n[main.plugins.neuromancer]\nenabled = %s\n' % flag

    if re.search(r'^\s*main\.plugins\.neuromancer\.enabled\s*=', text, re.M):
        return re.sub(r'^\s*main\.plugins\.neuromancer\.enabled\s*=.*$',
                      'main.plugins.neuromancer.enabled = %s' % flag,
                      text, count=1, flags=re.M)
    return text.rstrip() + '\nmain.plugins.neuromancer.enabled = %s\n' % flag


def main():
    if len(sys.argv) not in (3, 4) or sys.argv[2] not in ('enable', 'disable'):
        sys.exit('usage: configure.py <config.toml> enable|disable [restore-lang]')
    path, action = sys.argv[1], sys.argv[2]
    text = open(path, encoding='utf-8').read()
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
