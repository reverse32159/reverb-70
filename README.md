# Reverb unit — algorithms and factory programs

This package describes the reverb unit's eleven algorithms and its 84 factory programs (42 of program set A and the 42
set B programs that differ from them) at the level needed to build a sample-accurate simulator. Each algorithm is given
as a signal network: named delay lines, taps, sums and products with their rounding and saturation rules. The
parameter laws, the run-time control and the mix are given at the same level.

## Files

| File | Content |
|---|---|
| `algorithms-and-programs.md` | The reference. **Part I** (1–5): conventions, the arithmetic, the network notation and how to evaluate a network, the eight networks with their listings. **Part II** (6–10): parameters and patches, control values, the laws that turn them into network values (with a parameter map per algorithm), the level detector with GATE / RT STOP and DECAY OPT, the delay modulation, input, output and mix, and how a whole program runs (10.4). **Part III** (11–12): the algorithms and a catalog of the factory programs. **Part IV** (13–14): data format and its encoding, sample rate |
| `reverb-programs.json` | The data (2.5 MB): the eight networks, every parameter's control value and network values for every value, the SIZE tables, every factory program with its stored values, patches and network values at rest, the modulation sequences and tables. Format: sections 13.1 and 13.2 |
| `reverb_build.py` | Network values from parameter values (the laws of sections 6–7). `python reverb_build.py check` rebuilds all 84 factory programs. Python 3.6+, standard library only |

The package contains no simulator. The text specifies every algorithm completely, and the data file holds every number
and table it refers to.

## Suggested reading order for a simulator

1. Sections 1–4 and 13.2: conventions, the arithmetic, the network notation and the encoding of the listings in the
   data file. Implement a network interpreter first: with a factory program's network values from the data file it
   produces that program at rest.
2. Section 5: the networks; section 9: the delay modulation (Chorus programs and Concert Hall); section 10: input,
   output and mix.
3. Section 8: the level detector, GATE / RT STOP and DECAY OPT (reverb programs).
4. Sections 6–7 and 10.4: how parameter values become network values, for live editing, MIDI patches and tempo.
5. Sections 11–12 for orientation.

## Quick start

```
python reverb_build.py check                     # rebuild every factory program (network and control values)
```
