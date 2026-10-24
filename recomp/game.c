/* Small (D.J. Hoskins / Virgo Software, 1993; the Risc PC release): what
 * libroger needs to know about the game.
 *
 * !Run: Small$Dir, MODE 13 with the cursor off, *FX229 255, WimpSlot 576K,
 * the three modules (V: SpiralVibe, *DotOn and *DotFade; X: Sound-FX, the
 * FX_ SWIs; S: LZWencoder, *LZWin), *FX229 0, then !Image, the game's BASIC
 * (basic.c, translated by SuperSpider's tools/bas2c.py). The BASIC DIMs
 * its blocks and *LOADs the machine code into them: CODE into K_, CALLed
 * through the table of offsets at its start; Welcome and Congrat into I_%
 * (USR); pl into E_ (CALL). Each is translated at its block's address
 * (../tools/images.py). (!Run's RMEnsure UtilityModule 3.5 runs Cl, a patch
 * for older machines, only on RISC OS before 3.5.) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "basic_runtime.h"

#include "gen/images.inc"       /* the translations: CODE, its overlays, the modules */

/* the BASIC runtime's PAGE, and its heap from the program's TOP, where the
 * DIMs go (images.py works out the same addresses) */
int32_t bas_page = 0x8F00;
uint32_t bas_lomem = BAS_LOMEM;

/* <Small$Dir> is !Small (!Run: Set Small$dir <Obey$Dir>) */
static const char *const prefixes[] = {NULL};
static const char *const variables[] = {"Small$Dir", "!Small", NULL};

/* the BASIC has no assembler */
void bas_asm(const char *text) { fprintf(stderr, "bas_asm: not handled: %s\n", text); }

static int game_cli(const char *c)
{
    while (*c == ' ' || *c == '*') c++;
    /* PROCA_, the error handler (Escape at the title quits): it kills the
     * modules and starts the desktop - here the run ends */
    if (!strcasecmp(c, "Desktop")) roger_finish("quit");
    return 0;
}

static void init(void)
{
    bas_cli = game_cli;
    /* !Run: VDU 22,15,22,13,23,1,0;0;0;0; and *FX229 255 ... *FX229 0 */
    vdu(22, 15, 22, 13, 23, 1, 0, 0, 0, 0, 0, 0, 0, 0, -1);
    bas_main();                                  /* Run <Small$Dir>.!Image */
    roger_finish("program ended");
}

/* headless scenario (--limit=150000000): Space on the title at 20s (40M
 * instructions) starts level 1, which is under way by 28s; then forward,
 * turn right, forward, fire */
static const struct roger_key keys[] = {
    {99, 40000000, 40600000},                    /* Space: start */
    {99, 90000000, 91200000},                    /* Space: forward */
    {67, 93000000, 93600000},                    /* X: turn right */
    {99, 96000000, 97200000},                    /* Space: forward */
    {74, 100000000, 100600000},                  /* Return: fire */
};

static struct roger_config config = {
    .title = "Small (recompiled)",
    .image_path = CODE_PATH,                     /* CODE, at K_: the BASIC loads it there again */
    .image = &recomp_code_image,
    .programs = programs,
    .modules = modules,
    .appdir = "../game",
    .dir_prefixes = prefixes,
    .variables = variables,
    .initial_mode = 13,
    .wimpslot = 576 * 1024,
    .screen_size = 0x28000,                      /* two mode 13 banks */
    .vidc20 = 1,
    /* controllers: the D-pad or stick turns (Z, X) and moves on (Space), A
     * fires (Return), B drops a bomb (Ctrl), Y pauses (P), Back aborts
     * (Escape), Start starts (Space); or, connected at start (--joystick),
     * Acorn's joystick, which the game reads if Joystick_Read answers
     * (back and fire together drop a bomb) */
    .pad_map = "up=Space,left=Z,right=X,a=Return,b=Left Ctrl,y=P,back=Escape,start=Space",
    .joystick = ROGER_JOY_ACORN,
    .keys = keys,
    .nkeys = sizeof keys / sizeof keys[0],
    .init = init,
};

int main(int argc, char **argv) { roger_main(argc, argv, &config); }
