Small (D.J. Hoskins / Virgo Software, 1993; Risc PC release) - static recompilation
=====================================================================================

A recipe: this repository holds no game data. It rebuilds the game as a
native executable from your own copy of the disc, recognised by content
(recipe.json), so it can be shared without distributing the game.

    ./build.sh "Small (1993)(Virgo)(RISC PC).adf"
    cd recomp && ./small

build.sh runs recipe.json's steps with SuperSpider's tools/weave.py
(~/stuff/superspider, or $SUPERSPIDER): it extracts the disc, analyses and
translates the machine code, translates the BASIC, and links it all with
libroger (~/stuff/libroger, or make ROGER=...). It takes under a minute.
Needs python3, OCaml/dune, gcc and SDL3.

What it makes:

    extracted/disc1      $SS/tools/adf_extract.py's output, via weave.py
    game/!Small          libroger's appdir (<Small$Dir>)
    analysis/*.json      SuperSpider's analyses (CODE, Welcome, Congrat, pl,
                         the three modules)
    recomp/gen/          their C translations; recomp/basic.c the BASIC's
    recomp/small         the game

Committed: recipe.json, build.sh, tools/images.py, recomp/ (Makefile,
game.c), analysis/*.roots, this file.

How the game is put together
----------------------------

!Run sets Small$Dir, MODE 13, a 576K WimpSlot, RMLoads three of the
author's modules - V (SpiralVibe: *DotOn, *DotFade, the star field),
X (Sound-FX: the FX_ SWIs and their samples), S (LZWencoder: *LZWin,
which the pictures and sprites are packed for) - and runs !Image, the
game's BASIC (its variable names squashed; H on the disc is the author's
unsquashed source of an earlier version, which isn't used). The BASIC
runs the title, the attract sequence, the between-level text and scores,
and builds each level's objects from the data file; it DIMs its blocks
and *LOADs the machine code into them:

- CODE into K_ (DIM K_ 36*1024): a table of 20 offsets, then the code,
  position-independent. The BASIC CALLs it through the table
  (CALL(K_!n+K_)): the 3D maze view, the sprites and particles, the game
  itself (K_!4).
- Welcome and Congrat, utilities, into I_% (USR(I_%)): the title and
  end-of-game pictures with their music player.
- pl into E_ (CALL E_): the end sequence's zoomer.

Each is translated at its block's address in the BASIC runtime, whose heap
starts at the program's TOP (tools/images.py works the addresses out and
writes them to recomp/gen/images.inc). The runtime keeps no variables in
the heap, so the blocks are lower than under BASIC; nothing depends on
where they are.

- recomp/basic.c: !Image, translated by $SS/tools/bas2c.py, on
  SuperSpider's BASIC runtime ($SS/runtime/basic_runtime.c).
- recomp/game.c: !Run by hand, the config, a headless scenario; the
  error handler's *Desktop (Escape on the title) ends the run.

Everything translates: SuperSpider's analysis leaves nothing unresolved,
and runs through the title, the attract sequence and a level interpret
nothing. Small needed, in SuperSpider (general mechanisms):

- unrolled loops entered in two steps: add r12,pc,#&14 ; add r2,r2,r2,lsl
  #1 ; add r2,r12,r2,lsl #2 ; ... ; mov pc,r2 (the wall and sprite
  scalers in CODE and pl: 241 blocks of 3 or 5 instructions), the loop
  around them coming back to the mov pc,r2 with r12 reused;
- a table of stubs at a known address (add pc,r8,r6,lsl #3 into 8-byte
  bl handler ; b join entries: the object handlers);

in bas2c.py: WHILE/ENDWHILE, NEXT closing several loops (NEXT,), CALL with
a parameter list, DIM x (n) with a space being a block rather than an
array, and a REPEAT never closed (left on BASIC's stack) not taken to
enclose the DEFs after it; and in libroger, *FX with its number straight
after the name (*FX19, *FX112,1), which the BASIC uses for its bank
switching and vsync waits, and *Load's address given with a '&' (*LOAD
<Small$Dir>.TI &1FEC000: the panel on the right, loaded straight into
the second screen bank and copied to the first).

Speed
-----

The game paces itself: CODE's main loop waits for two vsyncs a frame
(OS_Byte 19) and the BASIC's sequences wait on TIME and *FX19, so it runs
at the original speed without a CPU-speed setting (libroger's default,
unthrottled, is right). The level timers count real time.

Controls
--------

Z/X turn, Space moves forward (and starts a game on the title), Return
fires, Ctrl drops a bomb, P pauses, Q sound, Escape aborts; Return on the
title asks for a password (given every five levels). A game controller:
D-pad or stick turns and moves, A fires, B bombs, Y pauses, Back aborts,
Start starts; with --joystick (or a controller connected at start) it's
Acorn's joystick instead, which the game reads (back and fire together
drop a bomb).

Headless runs: `./small --limit=110000000` plays the title and the start of
level 1 (game.c's scenario).

Not tested: the end sequence (after level 50: Congrat and pl), which
translate but haven't been reached.
