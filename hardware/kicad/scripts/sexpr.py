"""Minimal S-expression reader/writer for KiCad files.

Atoms are kept as their raw source text (quoted strings keep their quotes),
so a parsed tree writes back out unchanged.
"""


def parse(text):
    pos = 0
    n = len(text)
    stack = [[]]
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            stack.append([])
            pos += 1
        elif c == ")":
            done = stack.pop()
            stack[-1].append(done)
            pos += 1
        elif c == '"':
            end = pos + 1
            while text[end] != '"':
                end += 2 if text[end] == "\\" else 1
            stack[-1].append(text[pos:end + 1])
            pos = end + 1
        else:
            end = pos
            while end < n and text[end] not in ' \t\r\n()"':
                end += 1
            stack[-1].append(text[pos:end])
            pos = end
    return stack[0]


def dump(node, indent=0):
    if not isinstance(node, list):
        return node
    flat = "(" + " ".join(dump(x) for x in node) + ")"
    if len(flat) + indent <= 100 and not any(isinstance(x, list) and any(isinstance(y, list) for y in x) for x in node):
        return flat
    pad = "\n" + "\t" * (indent + 1)
    out = "(" + dump(node[0])
    for x in node[1:]:
        out += (pad + dump(x, indent + 1)) if isinstance(x, list) else (" " + x)
    return out + "\n" + "\t" * indent + ")"


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def unq(s):
    if s.startswith('"'):
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def find_all(node, tag):
    return [x for x in node[1:] if isinstance(x, list) and x and x[0] == tag]


def find(node, tag):
    r = find_all(node, tag)
    return r[0] if r else None
