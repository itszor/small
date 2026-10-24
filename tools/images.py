#!/usr/bin/env python3
"""The translated machine code of Small, and how it's made.

    images.py analyse   SuperSpider (analyse --full) on each image below ->
                        analysis/<name>.json; CODE's roots are its entry
                        table, which the BASIC CALLs through
    images.py gen       their C translations -> recomp/gen/<name>/, plus
                        recomp/gen/images.inc (game.c's tables)
    images.py roots LOG...   gap entries from --trace-gaps runs -> analysis/*.roots

game/!Small (libroger's appdir) comes from the original disc: $SS/tools/weave.py
extract, as recipe.json says (../build.sh).

The game is a BASIC program (!Small.!Image, translated by $SS/tools/bas2c.py
into recomp/basic.c) that DIMs its blocks and *LOADs its machine code into
them: CODE into K_ (DIM K_ 36*1024), which it CALLs through the table of
offsets at its start (CALL(K_!n+K_)); Welcome and Congrat, utilities, into
I_% (USR(I_%)); pl into E_ (CALL E_). All of them are position-independent;
each is translated at the address its block has in the BASIC runtime, whose
heap (bas_lomem) starts at the program's TOP (PAGE &8F00 + its length), as
BASIC's does. The runtime keeps no variables in the heap, so the blocks are
lower than they were under BASIC (BLOCK1-5, saved from the 1600-byte M_ by
the author's BASIC, say it was at about &97200), which nothing depends on.
"""
import os
import struct
import subprocess
import sys

TOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SS = os.environ.get('SUPERSPIDER', os.path.expanduser('~/stuff/superspider'))
SSBIN = os.path.join(SS, '_build/default/bin/main.exe')
GAME = os.path.join(TOP, 'game')
SMALL = os.path.join(GAME, '!Small')
AN = os.path.join(TOP, 'analysis')
RC = os.path.join(TOP, 'recomp')

PAGE = 0x8F00

# line 40's DIMs, in order: D_ 340, E_ (6*1024+2048), G_ 650, H_ 650,
# I_% 208*1024, J_% 282*1024, K_ 36*1024, M_ 1600
DIMS = [('D_', 340), ('E_', 6 * 1024 + 2048), ('G_', 650), ('H_', 650),
        ('I_%', 208 * 1024), ('J_%', 282 * 1024), ('K_', 36 * 1024), ('M_', 1600)]

# the modules !Run RMLoads, in its order, each in its own 64K of RMA
MODULES = [('V', 'spiralvibe'), ('X', 'soundfx'), ('S', 'lzw')]
MODBASE = 0x1840000


def find(d, name):
    """a RISC OS file in a host directory: any case, any ,load-exec suffix"""
    for f in os.listdir(d):
        if f.split(',')[0].lower() == name.lower():
            return os.path.join(d, f)
    raise FileNotFoundError(os.path.join(d, name))


def lomem():
    """TOP, word-aligned: PAGE + the BASIC's length"""
    return (PAGE + os.path.getsize(find(SMALL, '!Image')) + 3) & ~3


def blocks():
    """each DIMmed block's address, as the BASIC runtime's dim() gives them
    (DIM x n takes n+1 bytes, rounded up to a word)"""
    a, out = lomem(), {}
    for name, n in DIMS:
        out[name] = a
        a = (a + n + 1 + 3) & ~3
    return out


def images():
    """(name, file in !Small, base, roots): the program (CODE) and its overlays"""
    b = blocks()
    code = open(find(SMALL, 'CODE'), 'rb').read()
    table = [b['K_'] + o for o in struct.unpack_from('<20I', code)]
    return [('code', 'CODE', b['K_'], table),
            ('welcome', 'Welcome', b['I_%'], [b['I_%']]),
            ('congrat', 'Congrat', b['I_%'], [b['I_%']]),
            ('pl', 'pl', b['E_'], [b['E_']])]


def modules():
    """(name, file in !Small, base)"""
    return [(name, f, MODBASE + k * 0x10000) for k, (f, name) in enumerate(MODULES)]


def run(cmd, **kw):
    print('+', ' '.join(cmd))
    subprocess.run(cmd, check=True, **kw)


def roots_file(name, extra=()):
    """analysis/<name>.roots (the gaps' entries) with extra roots before them,
    in analysis/<name>.all.roots"""
    rf = os.path.join(AN, name + '.roots')
    if not os.path.exists(rf):
        open(rf, 'w').write('# gap entries from --trace-gaps runs (images.py roots)\n')
    merged = os.path.join(AN, name + '.all.roots')
    with open(merged, 'w') as f:
        f.write('# entry points (images.py)\n')
        f.writelines('%x\n' % a for a in extra)
        f.write(open(rf).read())
    return merged


def analyse():
    os.makedirs(AN, exist_ok=True)
    run(['dune', 'build'], cwd=SS)
    for name, f, base, roots in images():
        # (CODE starts with its table, not code: --exec, its first entry)
        run([SSBIN, 'analyse', find(SMALL, f), '%x' % base, '--exec', '%x' % roots[0], '--full',
             '--roots', roots_file(name, roots), '-o', os.path.join(AN, name + '.json')])
    for name, f, base in modules():
        run([SSBIN, 'analyse', find(SMALL, f), '%x' % base, '--module', '--full', '--roots', roots_file(name),
             '-o', os.path.join(AN, name + '.json')])


def gen():
    gd = os.path.join(RC, 'gen')
    if os.path.isdir(gd):
        subprocess.run(['rm', '-rf', gd], check=True)
    for k, (name, f, base, _) in enumerate(images()):
        run([SSBIN, 'gen', find(SMALL, f), '%x' % base, os.path.join(AN, name + '.json'),
             '--c', os.path.join(gd, name), '--prefix', 'P%d' % k, '--tabprefix', 'recomp_' + name])
    for k, (name, f, base) in enumerate(modules()):
        run([SSBIN, 'gen', find(SMALL, f), '%x' % base, os.path.join(AN, name + '.json'),
             '--c', os.path.join(gd, name), '--prefix', 'M%d' % k, '--tabprefix', 'recomp_' + name,
             '--files', '1'])
    with open(os.path.join(gd, 'images.inc'), 'w') as out:
        out.write('/* generated by ../tools/images.py - the translated images, for game.c */\n')
        for name, *_ in images() + modules():
            out.write('extern const struct roger_image recomp_%s_image;\n' % name)
        out.write('static const struct roger_module modules[] = {\n')
        for name, f, _ in modules():
            out.write('    {"%s", &recomp_%s_image, 0},\n' % (os.path.relpath(find(SMALL, f), RC), name))
        out.write('    {NULL, NULL, 0}};\n')
        out.write('static const struct roger_program programs[] = {\n')
        for name, f, _, _ in images()[1:]:
            out.write('    {"%s", &recomp_%s_image, 1},\n' % (f, name))
        out.write('    {NULL, NULL, 0}};\n')
        out.write('#define CODE_PATH "%s"\n' % os.path.relpath(find(SMALL, 'CODE'), RC))
        out.write('#define BAS_LOMEM 0x%X\n' % lomem())


def roots(logs):
    for name, f, base, _ in images():
        run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), find(SMALL, f), '%x' % base,
             os.path.join(AN, name + '.roots')] + logs)
    for name, f, base in modules():
        run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), find(SMALL, f), '%x' % base,
             os.path.join(AN, name + '.roots')] + logs)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'roots':
        roots(sys.argv[2:])
    else:
        for step in sys.argv[1:]:
            {'analyse': analyse, 'gen': gen}[step]()
