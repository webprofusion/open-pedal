"""Compare a netlist exported by KiCad with the one design.py intends.

usage: check_netlist.py exported.net
"""
import sys

from sexpr import parse, find, find_all, unq
from common import netlist


def main(path):
    tree = parse(open(path, encoding="utf8").read())[0]
    got = {}
    for net in find_all(find(tree, "nets"), "net"):
        name = unq(find(net, "name")[1]).lstrip("/")
        nodes = sorted((unq(find(n, "ref")[1]), unq(find(n, "pin")[1])) for n in find_all(net, "node"))
        got[name] = nodes
    want = netlist()
    # KiCad names single-pin and unnamed nets itself; compare by membership.
    want_sets = {frozenset(v): k for k, v in want.items()}
    got_sets = {frozenset(v): k for k, v in got.items() if not k.startswith("unconnected-")}
    bad = 0
    for members, name in want_sets.items():
        if members not in got_sets:
            bad += 1
            print(f"MISSING or different: {name}: {sorted(members)}")
    for members, name in got_sets.items():
        if members not in want_sets:
            bad += 1
            print(f"UNEXPECTED: {name}: {sorted(members)}")
        elif want_sets[members] != name:
            bad += 1
            print(f"NAME: wanted {want_sets[members]}, KiCad has {name}")
    print(f"netlist check: {len(want)} nets, {sum(len(v) for v in want.values())} pins, {bad} differences")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
