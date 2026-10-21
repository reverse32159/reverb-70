# Reverb unit — algorithms and factory programs: simulation reference

This reference describes the reverb unit's eleven algorithms and its 84 factory programs at the level needed to
re-implement them sample by sample: the arithmetic, the eight signal networks the algorithms run on, how parameter
values become the networks' coefficients and delays, the run-time control (patches, MIDI, the level-driven gate and
DECAY OPT, the delay modulation), the mix, and a catalog of the factory programs. It describes the signal processing
and its control only.

* **Part I** (sections 1–5): conventions, the arithmetic, the network notation and the eight networks.
* **Part II** (sections 6–10): parameters and their laws, run-time control, delay modulation, input, output and mix.
* **Part III** (sections 11–12): the algorithms and the factory programs.
* **Part IV** (sections 13–14): data file and tools, sample rate.

# Part I — Signal processing

Part I gives the per-sample processing of every algorithm: a fixed network of sums, products and delays with
named coefficients and delays (section 5), computed with the arithmetic of section 3. With the network values of a
factory program from the data file, it gives that program at rest.

## 1. Conventions

* **Sample rate.** fs = **33 854.17 Hz** (13 000 000 / 384). All delays are in samples at this rate. A simulator at
  another rate resamples the input and output (section 14).
* **Channels.** One (mono) input and two outputs, L and R, for every algorithm.
* **Program sets.** The unit's factory programs come in two sets. **Set A** has 42 programs on eleven algorithms.
  **Set B** has 42 programs on ten algorithms (no Inverse Room) and differs from set A in its own Multiband network
  (section 5.4), the control-value law of V LC, the absence of the MIDI CLK patch source, its own delay-modulation
  sequence and its programs. Everything not marked "set B" holds for both sets. The data file holds every program of
  both sets (section 12), except one set B program that equals a set A program.
* **Parameters.** A parameter is addressed by its front-panel position "row.column" (for example 1.1). Its stored
  value is v (the index of its display value); patches add to v and give the effective value (section 6.2). Each
  parameter's law turns the effective value into a **control value** b, an integer 0…255, or a sample count for delay
  parameters (section 6.3). The network values follow from the control values (section 7).
* **Notation.** ⌊ ⌋ rounds down (towards −∞). Coefficients are written as fractions; a coefficient symbol has a
  resolution of 1/8 or 1/32 and its value is stored as an integer number of these units (section 4).

## 2. Overview

```
                      ┌────────────────────────── dry gain ──────────────────────────┐
 in ─► input stage ─► 16-bit sampling ─► NETWORK (section 5, once per sample) ─► L, R ─► wet gain ─► Σ ─► out L, R
       (10.1)                                ▲   coefficients, delays
                                             │
   front panel, MIDI ─► patches ─► control values (6) ─► network values (7)
                                             ▲
                       level detector, GATE, DECAY OPT (8) · delay modulation (9)
```

Three layers produce the sound:

1. **The network** of the algorithm (section 5) turns each input sample into a left and a right output sample.
2. **The parameter laws** (sections 6 and 7) compute the network's coefficients and delays from the parameter values,
   the patches (MIDI controllers and the SOFT KNOB) and the rhythm tempo.
3. **The run-time control** changes some network values while audio runs: the reverbs' level detector moves the
   reverberation-time values (GATE, RT STOP, DECAY OPT, section 8), and the Chorus and Concert Hall algorithms move
   interpolated delay taps in a bounded random walk (section 9). MIX and FX ADJ set the wet and dry gains (10.3).

For a program at rest (no MIDI, no level-driven effects) the data file gives every network value (section 12), so only
the network and the delay modulation are needed.

## 3. Arithmetic (exact)

### 3.1 Values

Every signal value is an integer y with −2^17 ≤ y ≤ 2^17 − 1; full scale ±1 corresponds to ±2^17. A 16-bit input
sample x16 enters as **x = 4·x16 + 3**. An output sample is **⌊y/4⌋** (16 bits).

### 3.2 Coefficients and products

A coefficient c has a resolution of 1/8 (c = m/8, |m| ≤ 7) or 1/32 (c = m/32, |m| ≤ 31). Some 1/32 coefficients
also take the values 1 … 63/32 (m = 32 … 63); the networks name them. A product of a coefficient and a value is

    c·y  =  sgn(c) · ⌊ |c| · y ⌋

(the magnitude is scaled and rounded down, then the sign is applied). A coefficient 0 contributes nothing.

### 3.3 Sums

Each signal of a network is a sum `s = start ± c1·y1 ± c2·y2 …`, evaluated **left to right**:

* After every addition the running sum **saturates**: values above 2^17 − 1 become 2^17 − 1, values below −2^17
  become −2^17. Values never wrap.
* The start is a value (an operand) or a product. A product start with a coefficient ≥ 1 saturates as well.
* A sum that **starts with a negative product** starts at **−⌊|c|·y⌋ − 1**, not at −⌊|c|·y⌋ (0 when c = 0).
  Negative means the value of the coefficient as used, including a sign written in the listing: `sym` with a negative
  value is negative, `−sym` with a negative value is positive, and only the value counts. The starts that can be
  negative are: Multiband (5.3) s11 (`vlc1_x`), s17 (`vlc2_x`), s24 (`vlc3_x`), s30 (`vlc4_x`), s36 (`vlc5_x`), s41 (`vlc6_x`); Chamber (5.5) s29 (−1/2); Inverse (5.6) s21 (`−g2`), s29 (−1/2); Plate (5.7) s32 (−1/2); Hall (5.8) s21 (`rthc_x`). Terms (after the start) have no such rule.
* One coefficient (set B Multiband, voice 6 low-cut) has its own rule for values ≥ 1, given with its network.

The order of the terms matters only through saturation and the rule above; the listings give the exact order.

### 3.4 Stored signals and taps

A signal marked **stored** is kept for later samples with 16 bits: the network stores **w = ⌊y/4⌋**, and a tap that
reads it d samples later returns **4w + 3**. A tap therefore always sees the rounded value, while the signal itself,
used within the same sample without brackets, keeps all its bits. A tap with delay 0 returns the value stored in the
same sample (the stored signal always comes earlier in the list).

### 3.5 Output timing

Both outputs of a sample belong to the same input sample.

## 4. Network notation

Each algorithm runs one of eight networks (section 5). A network is a list of signals s1, s2, … that are computed once
per sample, **in the listed order**:

* **Operands**: `x` (the input sample), `sj` (signal j of this sample, always listed earlier), and `sj[d]`, a **tap**:
  the stored value of sj from d samples ago (3.4). `sj[0]` is this sample's stored value of sj.
* **Delays** d are numbers or delay symbols: `pd` (predelay), `rd1`… (reflection delays), `dly1`… (voice delays),
  `pit1`… (resonator lengths), `pdl1`… (resonator predelays), `t1`… (delays scaled by SIZE, section 7.5) and
  `mA1`, `mB1`… (the modulated taps, section 9).
* **Coefficients** are fractions or symbols; `−sym` is the negated value. The tables under each listing say which
  parameter law sets each symbol (section 7). Coefficients of 0 that no parameter can change are left out, and a start
  product with the fixed coefficient 1 is written as its operand alone (⌊1·y⌋ = y).
* **stored** marks the signals that later samples read. Each needs a circular delay line as long as its longest tap
  plus one; 32 768 samples per line suffice for every program.
* **out L, out R** mark the two output signals.

The networks are built from a few recurring forms, always with the exact term order of the listing:

* **Allpass**, gain k, delay d: `w = u + k·w[d]` (w stored), `y = w[d] − k·w`. The tank allpasses use the variant
  `w = u + k·v` with v from another line; the listings give each one exactly.
* **One-pole low-pass**: `y = p·u + q·y[1]` with q ≈ 1 − p (section 7.1).
* **Halved difference**: `D = B − 1/2·A − 1/2·A`, two separate halvings, for the interpolated taps (9.1) and the
  RT LOW shelves (7.6).

**Evaluating a network.** Keep one circular buffer of 32 768 values per stored signal and a sample counter t. For
each input sample, compute the signals in the listed order. A tap sj[d] reads the buffer of sj at index
(t − d) mod 32 768; a stored signal writes its rounded value (3.4) at index t as soon as it is computed, so a later
signal's tap with delay 0 sees it. After the last signal, the two output signals give the output sample (3.1), and t
increases by 1. Coefficient and delay symbols are looked up in the current network values; values changed by the
run-time control (sections 8 and 9) apply from the next sample computed with them. The listings are stored in the data
file in a form that can be interpreted directly (section 13.2), and the special rules under each listing (the
interpolated taps, the DIFFUSION 0 bypass, one start rule of the set B Multiband) are part of the network.

## 5. The networks

Each listing below is exact. The symbol tables say what sets each coefficient (sections 7 and 8) and each delay
(section 7.3). Section 11 describes what the networks do, at the level of signal blocks.

### 5.1 Chorus network (Chorus + Echo, Chorus + Rhythm)

Six voices on two echo lines. The input is stored (s1) and diffused twice: s23–s28 (allpasses of 50, 159 and 408 samples) and s31–s36 (59, 188, 503). Each diffuser output plus the feedback of three voices (s2, s29) passes the HC one-pole (s3, s30) into an echo line. Voices 1–3 tap echo line s3, voices 4–6 echo line s30 (`dly1`…`dly6`), each into its own short chorus line (s4–s9). The modulated taps of section 9 read the chorus lines (s10/s11 … s21/s22) and give the voice outputs; levels (s37–s42) and pans form the outputs.

43 signals, 33 of them stored. Out L = s20, out R = s43.

```
s1   = x   ▸ stored
s2   = 31/32·s36[1] + fb1·s11[1] + fb2·s13[1] + fb3·s15[1]
s3   = hc_y·s3[1] + hc_x·s2   ▸ stored
s4   = 31/32·s3[dly1]   ▸ stored
s5   = 31/32·s3[dly2]   ▸ stored
s6   = 31/32·s3[dly3]   ▸ stored
s7   = 31/32·s30[dly4]   ▸ stored
s8   = 31/32·s30[dly5]   ▸ stored
s9   = 31/32·s30[dly6]   ▸ stored
s10  = s4[mB1] − 1/2·s4[mA1] − 1/2·s4[mA1]
s11  = s4[mA1] + m1·s10   ▸ stored
s12  = s5[mB2] − 1/2·s5[mA2] − 1/2·s5[mA2]
s13  = s5[mA2] + m2·s12   ▸ stored
s14  = s6[mB3] − 1/2·s6[mA3] − 1/2·s6[mA3]
s15  = s6[mA3] + m3·s14   ▸ stored
s16  = s7[mB4] − 1/2·s7[mA4] − 1/2·s7[mA4]
s17  = s7[mA4] + m4·s16   ▸ stored
s18  = s8[mB5] − 1/2·s8[mA5] − 1/2·s8[mA5]
s19  = s8[mA5] + m5·s18   ▸ stored
s20  = panL1·s37[1] + panL2·s38[1] + panL3·s39[1] + panL4·s40[1] + panL5·s41[1] + panL6·s42[1]   ▸ out L
s21  = s9[mB6] − 1/2·s9[mA6] − 1/2·s9[mA6]
s22  = s9[mA6] + m6·s21   ▸ stored
s23  = s1[1] + dif6·s23[50]   ▸ stored
s24  = s23[50] − dif6·s23   ▸ stored
s25  = s24[1] + dif5·s25[159]   ▸ stored
s26  = s25[159] − dif5·s25   ▸ stored
s27  = s26[1] + dif3·s27[408]   ▸ stored
s28  = s27[408] − dif3·s27   ▸ stored
s29  = 31/32·s28[0] + fb4·s17[1] + fb5·s19[1] + fb6·s22[1]
s30  = hc_y·s30[1] + hc_x·s29   ▸ stored
s31  = s1[2] + dif6·s31[59]   ▸ stored
s32  = s31[59] − dif6·s31   ▸ stored
s33  = s32[1] + dif5·s33[188]   ▸ stored
s34  = s33[188] − dif5·s33   ▸ stored
s35  = s34[1] + dif3·s35[503]   ▸ stored
s36  = s35[503] − dif3·s35   ▸ stored
s37  = lvl1·s11[1]   ▸ stored
s38  = lvl2·s13[1]   ▸ stored
s39  = lvl3·s15[1]   ▸ stored
s40  = lvl4·s17[1]   ▸ stored
s41  = lvl5·s19[1]   ▸ stored
s42  = lvl6·s22[1]   ▸ stored
s43  = panR1·s37[1] + panR2·s38[1] + panR3·s39[1] + panR4·s40[1] + panR5·s41[1] + panR6·s42[1]   ▸ out R
```

Special rules:

* s11: when m1 = 32/32, s11 = s4[mB1] exactly (section 9.1).
* s13: when m2 = 32/32, s13 = s5[mB2] exactly (section 9.1).
* s15: when m3 = 32/32, s15 = s6[mB3] exactly (section 9.1).
* s17: when m4 = 32/32, s17 = s7[mB4] exactly (section 9.1).
* s19: when m5 = 32/32, s19 = s8[mB5] exactly (section 9.1).
* s22: when m6 = 32/32, s22 = s9[mB6] exactly (section 9.1).
* DIFFUSION control value 0: s36[1] by s1[1]; s28[0] by s1[0].

| Symbol | Unit | Set by |
|---|---|---|
| `fb1` | 1/8 | V FDBK % 1: feedback law (7.2) |
| `fb2` | 1/8 | V FDBK % 2: feedback law (7.2) |
| `fb3` | 1/8 | V FDBK % 3: feedback law (7.2) |
| `hc_y` | 1/32 | HC: min(31, 32 − ⌊b/8⌋)/32 |
| `hc_x` | 1/32 | HC: ⌊b/8⌋/32 |
| `m1`…`m5` | 1/32 | delay modulation (9.1) |
| `panL1` | 1/32 | V PAN 1: min(31, 32 − ⌊b/8⌋)/32 |
| `panL2`…`panL6` | 1/8 | V PAN 2–6: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `m6` | 1/32 | delay modulation (9.1) |
| `dif6` | 1/32 | DIFFUSION: slope 6 (7.4) |
| `dif5` | 1/32 | DIFFUSION: slope 5 (7.4) |
| `dif3` | 1/32 | DIFFUSION: slope 3 (7.4) |
| `fb4` | 1/8 | V FDBK % 4: feedback law (7.2) |
| `fb5` | 1/8 | V FDBK % 5: feedback law (7.2) |
| `fb6` | 1/8 | V FDBK % 6: feedback law (7.2) |
| `lvl1`…`lvl6` | 1/32 | V LVL 1–6: ⌊b/8⌋/32 |
| `panR1` | 1/32 | V PAN 1: ⌊b/8⌋/32 |
| `panR2`…`panR6` | 1/8 | V PAN 2–6: ⌊b/32⌋/8 |

Delays: `dly1`…`dly6`: V DLY MS 1–6 / V DLY 1–6; `mA1`…`mA6`, `mB1`…`mB6`: delay modulation (9.1). Laws in 7.3.

### 5.2 Chords network (Resonant Chords, Rhythmic Chords)

Six resonators. The input, scaled by 17/32, is stored with the cross feedback of two predelay taps (s2). Resonator j takes the predelay tap s2[`pdlj`] and adds its own output from `pitj` samples ago times its resonance (s3, s6, …), then a one-pole low-pass with the HC L (voices 1–3) or HC R (voices 4–6) coefficients (s4, s7, …); the voice level follows (s5, s8, …). The pans sum the levels into the outputs (s12, s22).

22 signals, 13 of them stored. Out L = s12, out R = s22.

```
s1   = x
s2   = 17/32·s1 + fbm·s2[pdl3] + fbp·s2[pdl6]   ▸ stored
s3   = 31/32·s2[pdl1] + res1·s4[pit1]
s4   = hcl_y·s4[1] + hcl_x·s3   ▸ stored
s5   = lvl1·s4   ▸ stored
s6   = 31/32·s2[pdl2] + res2·s7[pit2]
s7   = hcl_y·s7[1] + hcl_x·s6   ▸ stored
s8   = lvl2·s7   ▸ stored
s9   = 31/32·s2[pdl3] + res3·s10[pit3]
s10  = hcl_y·s10[1] + hcl_x·s9   ▸ stored
s11  = lvl3·s10   ▸ stored
s12  = panL1·s5[1] + panL2·s8[1] + panL3·s11[1] + panL4·s15[1] + panL5·s18[1] + panL6·s21[1]   ▸ out L
s13  = 31/32·s2[pdl4] + res4·s14[pit4]
s14  = hcr_y·s14[1] + hcr_x·s13   ▸ stored
s15  = lvl4·s14   ▸ stored
s16  = 31/32·s2[pdl5] + res5·s17[pit5]
s17  = hcr_y·s17[1] + hcr_x·s16   ▸ stored
s18  = lvl5·s17   ▸ stored
s19  = 31/32·s2[pdl6] + res6·s20[pit6]
s20  = hcr_y·s20[1] + hcr_x·s19   ▸ stored
s21  = lvl6·s20   ▸ stored
s22  = panR1·s5[1] + panR2·s8[1] + panR3·s11[1] + panR4·s15[1] + panR5·s18[1] + panR6·s21[1]   ▸ out R
```

| Symbol | Unit | Set by |
|---|---|---|
| `fbm` | 1/32 | V3 FDBK - %: −⌊b/8⌋/32 |
| `fbp` | 1/32 | V6 FDBK + %: ⌊b/8⌋/32 |
| `res1` | 1/32 | V RESN % 1: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| `hcl_y` | 1/32 | HC L: min(31, 32 − ⌊b/8⌋)/32 |
| `hcl_x` | 1/32 | HC L: ⌊b/8⌋/32 |
| `lvl1` | 1/32 | V LVL 1: ⌊b/8⌋/32 |
| `res2` | 1/32 | V RESN % 2: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| `lvl2` | 1/32 | V LVL 2: ⌊b/8⌋/32 |
| `res3` | 1/32 | V RESN % 3: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| `lvl3` | 1/32 | V LVL 3: ⌊b/8⌋/32 |
| `panL1`…`panL6` | 1/32 | V PAN 1–6: min(31, 32 − ⌊b/8⌋)/32 |
| `res4` | 1/32 | V RESN % 4: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| `hcr_y` | 1/32 | HC R: min(31, 32 − ⌊b/8⌋)/32 |
| `hcr_x` | 1/32 | HC R: ⌊b/8⌋/32 |
| `lvl4` | 1/32 | V LVL 4: ⌊b/8⌋/32 |
| `res5` | 1/32 | V RESN % 5: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| `lvl5` | 1/32 | V LVL 5: ⌊b/8⌋/32 |
| `res6` | 1/32 | V RESN % 6: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| `lvl6` | 1/32 | V LVL 6: ⌊b/8⌋/32 |
| `panR1`…`panR6` | 1/32 | V PAN 1–6: ⌊b/8⌋/32 |

Delays: `pdl3`: V PDL MS 3 / V DLY 3; `pdl6`: V PDL MS 6 / V DLY 6; `pdl1`: V PDL MS 1 / V DLY 1; `pit1`: V PITCH 1; `pdl2`: V PDL MS 2 / V DLY 2; `pit2`…`pit3`: V PITCH 2–3; `pdl4`: V PDL MS 4 / V DLY 4; `pit4`: V PITCH 4; `pdl5`: V PDL MS 5 / V DLY 5; `pit5`…`pit6`: V PITCH 5–6. Laws in 7.3.

### 5.3 Multiband network (Multiband Delay, Multiband Rhythm; set A)

Six voices on one delay line. The input plus the feedback of voices 1 and 2 (s1) passes three diffuser allpasses (s2–s7) into the delay line s7, which the voice taps read (`dly1`…`dly6`). Each voice runs a high-cut and a low-cut section of first-order stages with its V HC and V LC coefficients (voices 1–2: s8–s13 and s14–s19; voices 3–6 apply their level first: s21–s26, …, s39–s42). The pans sum the voices into the outputs (s20, s43).

43 signals, 35 of them stored. Out L = s20, out R = s43.

```
s1   = x + fb1·s9[2] + fb2·s15[2]   ▸ stored
s2   = s1[1] + dif5·s2[59]   ▸ stored
s3   = s2[59] − dif5·s2   ▸ stored
s4   = s3[2] + dif4·s4[188]   ▸ stored
s5   = s4[188] − dif4·s4   ▸ stored
s6   = s5[2] + dif3·s6[503]   ▸ stored
s7   = s6[503] − dif3·s6   ▸ stored
s8   = s7[dly1]
s9   = vhc1_x·s8 + vhc1_y·s9[1]   ▸ stored
s10  = vhc1_x·s9[1] + vhc1_y·s10[1]   ▸ stored
s11  = vlc1_x·s10[1] + vlc1_y·s11[1]   ▸ stored
s12  = −vlc1_x·s11[1] + vlc1_y·s12[1]   ▸ stored
s13  = lvl1·s10[1] + lvl1·s12   ▸ stored
s14  = s7[dly2]
s15  = vhc2_x·s14 + vhc2_y·s15[1]   ▸ stored
s16  = vhc2_x·s15[1] + vhc2_y·s16[1]   ▸ stored
s17  = vlc2_x·s16[1] + vlc2_y·s17[1]   ▸ stored
s18  = −vlc2_x·s17[1] + vlc2_y·s18[1]   ▸ stored
s19  = lvl2·s16[1] + lvl2·s18   ▸ stored
s20  = panL1·s13[0] + panL2·s19[0] + panL3·s26[1] + panL4·s32[1] + panL5·s38[1] + panL6·s42[1]   ▸ out L
s21  = lvl3·s7[dly3]
s22  = vhc3_x·s21 + vhc3_y·s22[1]   ▸ stored
s23  = vhc3_x·s22[1] + vhc3_y·s23[1]   ▸ stored
s24  = vlc3_x·s23[1] + vlc3_y·s24[1]   ▸ stored
s25  = −vlc3_x·s24[1] + vlc3_y·s25[1]   ▸ stored
s26  = s25 + 31/32·s23[1]   ▸ stored
s27  = lvl4·s7[dly4]
s28  = vhc4_x·s27 + vhc4_y·s28[1]   ▸ stored
s29  = vhc4_x·s28[1] + vhc4_y·s29[1]   ▸ stored
s30  = vlc4_x·s29[1] + vlc4_y·s30[1]   ▸ stored
s31  = −vlc4_x·s30[1] + vlc4_y·s31[1]   ▸ stored
s32  = s31 + 31/32·s29[1]   ▸ stored
s33  = lvl5·s7[dly5]
s34  = vhc5_x·s33 + vhc5_y·s34[1]   ▸ stored
s35  = vhc5_x·s34[1] + vhc5_y·s35[1]   ▸ stored
s36  = vlc5_x·s35[1] + vlc5_y·s36[1]   ▸ stored
s37  = −vlc5_x·s36[1] + vlc5_y·s37[1]   ▸ stored
s38  = s37 + 31/32·s35[1]   ▸ stored
s39  = lvl6·s7[dly6]
s40  = vhc6_x·s39 + vhc6_y·s40[1]   ▸ stored
s41  = vlc6_x·s40[1] + vlc6_y·s41[1]   ▸ stored
s42  = s41 + 31/32·s40[1]   ▸ stored
s43  = panR1·s13[0] + panR2·s19[0] + panR3·s26[0] + panR4·s32[1] + panR5·s38[1] + panR6·s42[1]   ▸ out R
```

Special rules:

* DIFFUSION control value 0: s7[dly1] by s1[dly1 − 1]; s7[dly2] by s1[dly2 − 1]; s7[dly3] by s1[dly3 − 1]; s7[dly4] by s1[dly4 − 1]; s7[dly5] by s1[dly5 − 1]; s7[dly6] by s1[dly6 − 1].

| Symbol | Unit | Set by |
|---|---|---|
| `fb1` | 1/32 | V1 FDBK %: ⌊b/8⌋/32 |
| `fb2` | 1/32 | V2 FDBK %: ⌊b/8⌋/32 |
| `dif5` | 1/32 | DIFFUSION: slope 5 (7.4) |
| `dif4` | 1/32 | DIFFUSION: slope 4 (7.4) |
| `dif3` | 1/32 | DIFFUSION: slope 3 (7.4) |
| `vhc1_x` | 1/32 | V HC 1: ⌊b/8⌋/32 |
| `vhc1_y` | 1/8 | V HC 1: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc1_x` | 1/32 | V LC 1: −⌊b/8⌋/32 |
| `vlc1_y` | 1/8 | V LC 1: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl1` | 1/32 | V LVL 1: ⌊b/8⌋/32 |
| `vhc2_x` | 1/32 | V HC 2: ⌊b/8⌋/32 |
| `vhc2_y` | 1/8 | V HC 2: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc2_x` | 1/32 | V LC 2: −⌊b/8⌋/32 |
| `vlc2_y` | 1/8 | V LC 2: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl2` | 1/32 | V LVL 2: ⌊b/8⌋/32 |
| `panL1` | 1/32 | V PAN 1: min(31, 32 − ⌊b/8⌋)/32 |
| `panL2`…`panL6` | 1/8 | V PAN 2–6: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl3` | 1/32 | V LVL 3: ⌊b/8⌋/32 |
| `vhc3_x` | 1/32 | V HC 3: ⌊b/8⌋/32 |
| `vhc3_y` | 1/8 | V HC 3: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc3_x` | 1/32 | V LC 3: −⌊b/8⌋/32 |
| `vlc3_y` | 1/8 | V LC 3: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl4` | 1/32 | V LVL 4: ⌊b/8⌋/32 |
| `vhc4_x` | 1/32 | V HC 4: ⌊b/8⌋/32 |
| `vhc4_y` | 1/8 | V HC 4: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc4_x` | 1/32 | V LC 4: −⌊b/8⌋/32 |
| `vlc4_y` | 1/8 | V LC 4: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl5` | 1/32 | V LVL 5: ⌊b/8⌋/32 |
| `vhc5_x` | 1/32 | V HC 5: ⌊b/8⌋/32 |
| `vhc5_y` | 1/8 | V HC 5: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc5_x` | 1/32 | V LC 5: −⌊b/8⌋/32 |
| `vlc5_y` | 1/8 | V LC 5: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl6` | 1/32 | V LVL 6: ⌊b/8⌋/32 |
| `vhc6_x` | 1/32 | V HC 6: ⌊b/8⌋/32 |
| `vhc6_y` | 1/8 | V HC 6: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc6_x` | 1/32 | V LC 6: −⌊b/8⌋/32 |
| `vlc6_y` | 1/8 | V LC 6: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `panR1` | 1/32 | V PAN 1: ⌊b/8⌋/32 |
| `panR2`…`panR6` | 1/8 | V PAN 2–6: ⌊b/32⌋/8 |

Delays: `dly1`…`dly6`: V DLY MS 1–6 / V DLY 1–6. Laws in 7.3.

### 5.4 Multiband B network (Multiband Delay, Multiband Rhythm; set B)

The set B Multiband: the same input, feedback, diffusers and voice taps as the set A network (s1–s7), with a different arrangement of the voice filters (s8–s37): each voice has two one-pole low-pass stages and a low-cut section of two stages.

38 signals, 30 of them stored. Out L = s19, out R = s38.

```
s1   = x + fb1·s9[2] + fb2·s15[2]   ▸ stored
s2   = s1[1] + dif5·s2[59]   ▸ stored
s3   = s2[59] − dif5·s2   ▸ stored
s4   = s3[2] + dif4·s4[188]   ▸ stored
s5   = s4[188] − dif4·s4   ▸ stored
s6   = s5[2] + dif3·s6[503]   ▸ stored
s7   = s6[503] − dif3·s6   ▸ stored
s8   = s7[dly1]
s9   = vhc1_y·s9[1] + vhc1_x·s8   ▸ stored
s10  = vhc1_y·s10[1] + vhc1_x·s9[1]   ▸ stored
s11  = vlc1_y·s9[1] + vlc1_x·s11[1]   ▸ stored
s12  = vlc1_y·s11[1] + vlc1_x·s12[1]   ▸ stored
s13  = lvl1·s12   ▸ stored
s14  = s7[dly2]
s15  = vhc2_y·s15[1] + vhc2_x·s14   ▸ stored
s16  = vhc2_y·s16[1] + vhc2_x·s15[1]   ▸ stored
s17  = vlc2_y·s16[3] + vlc2_x·s17[1]   ▸ stored
s18  = lvl2·s17   ▸ stored
s19  = panL1·s13[0] + panL2·s18[0] + panL3·s24[1] + panL4·s29[1] + panL5·s34[1] + panL6·s37[1]   ▸ out L
s20  = lvl3·s7[dly3]
s21  = vhc3_y·s21[1] + vhc3_x·s20   ▸ stored
s22  = vhc3_y·s22[1] + vhc3_x·s21[1]   ▸ stored
s23  = vlc3_y·s21[1] + vlc3_x·s23[1]   ▸ stored
s24  = vlc3_y·s23[1] + vlc3_x·s24[1]   ▸ stored
s25  = lvl4·s7[dly4]
s26  = vhc4_x·s25 + vhc4_y·s26[1]   ▸ stored
s27  = vhc4_x·s26[1] + vhc4_y·s27[1]   ▸ stored
s28  = vlc4_y·s27[1] + vlc4_x·s28[1]   ▸ stored
s29  = vlc4_y·s28[1] + vlc4_x·s29[1]   ▸ stored
s30  = lvl5·s7[dly5]
s31  = vhc5_x·s30 + vhc5_y·s31[1]   ▸ stored
s32  = vhc5_x·s31[1] + vhc5_y·s32[1]   ▸ stored
s33  = vlc5_y·s32[1] + vlc5_x·s33[1]   ▸ stored
s34  = vlc5_y·s33[1] + vlc5_x·s34[1]   ▸ stored
s35  = lvl6·s7[dly6]
s36  = vhc6_x·s35 + vhc6_y·s36[1]   ▸ stored
s37  = vlc6_y·s36[1] + vlc6_x·s37[1]   ▸ stored
s38  = panR1·s13[0] + panR2·s18[0] + panR3·s24[0] + panR4·s29[1] + panR5·s34[1] + panR6·s37[1]   ▸ out R
```

Special rules:

* s37: when vlc6_y ≥ 1, the first product is replaced by s36 + (vlc6_y − 1)·s36[1] (section 3.3).
* DIFFUSION control value 0: s7[dly1] by s1[dly1 − 1]; s7[dly2] by s1[dly2 − 1]; s7[dly3] by s1[dly3 − 1]; s7[dly4] by s1[dly4 − 1]; s7[dly5] by s1[dly5 − 1]; s7[dly6] by s1[dly6 − 1].

| Symbol | Unit | Set by |
|---|---|---|
| `fb1` | 1/32 | V1 FDBK %: ⌊b/8⌋/32 |
| `fb2` | 1/32 | V2 FDBK %: ⌊b/8⌋/32 |
| `dif5` | 1/32 | DIFFUSION: slope 5 (7.4) |
| `dif4` | 1/32 | DIFFUSION: slope 4 (7.4) |
| `dif3` | 1/32 | DIFFUSION: slope 3 (7.4) |
| `vhc1_y` | 1/32 | V HC 1: min(31, 32 − ⌊b/8⌋)/32 |
| `vhc1_x` | 1/32 | V HC 1: ⌊b/8⌋/32 |
| `vlc1_y` | 1/32 | V LC 1: (32 − ⌊b/8⌋)/32 |
| `vlc1_x` | 1/32 | V LC 1: −⌊b/8⌋/32 |
| `lvl1` | 1/32 | V LVL 1: ⌊b/8⌋/32 |
| `vhc2_y` | 1/32 | V HC 2: min(31, 32 − ⌊b/8⌋)/32 |
| `vhc2_x` | 1/32 | V HC 2: ⌊b/8⌋/32 |
| `vlc2_y` | 1/32 | V LC 2: (32 − ⌊b/8⌋)/32 |
| `vlc2_x` | 1/32 | V LC 2: −⌊b/8⌋/32 |
| `lvl2` | 1/32 | V LVL 2: ⌊b/8⌋/32 |
| `panL1` | 1/32 | V PAN 1: min(31, 32 − ⌊b/8⌋)/32 |
| `panL2`…`panL6` | 1/8 | V PAN 2–6: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `lvl3` | 1/32 | V LVL 3: ⌊b/8⌋/32 |
| `vhc3_y` | 1/32 | V HC 3: min(31, 32 − ⌊b/8⌋)/32 |
| `vhc3_x` | 1/32 | V HC 3: ⌊b/8⌋/32 |
| `vlc3_y` | 1/32 | V LC 3: (32 − ⌊b/8⌋)/32 |
| `vlc3_x` | 1/32 | V LC 3: −⌊b/8⌋/32 |
| `lvl4` | 1/32 | V LVL 4: ⌊b/8⌋/32 |
| `vhc4_x` | 1/32 | V HC 4: ⌊b/8⌋/32 |
| `vhc4_y` | 1/8 | V HC 4: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc4_y` | 1/32 | V LC 4: (32 − ⌊b/8⌋)/32 |
| `vlc4_x` | 1/8 | V LC 4: −⌊b/32⌋/8 |
| `lvl5` | 1/32 | V LVL 5: ⌊b/8⌋/32 |
| `vhc5_x` | 1/32 | V HC 5: ⌊b/8⌋/32 |
| `vhc5_y` | 1/8 | V HC 5: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc5_y` | 1/32 | V LC 5: (32 − ⌊b/8⌋)/32 |
| `vlc5_x` | 1/8 | V LC 5: −⌊b/32⌋/8 |
| `lvl6` | 1/32 | V LVL 6: ⌊b/8⌋/32 |
| `vhc6_x` | 1/32 | V HC 6: ⌊b/8⌋/32 |
| `vhc6_y` | 1/8 | V HC 6: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `vlc6_y` | 1/32 | V LC 6: (32 − ⌊b/8⌋)/32 |
| `vlc6_x` | 1/8 | V LC 6: −⌊b/32⌋/8 |
| `panR1` | 1/32 | V PAN 1: ⌊b/8⌋/32 |
| `panR2`…`panR6` | 1/8 | V PAN 2–6: ⌊b/32⌋/8 |

Delays: `dly1`…`dly6`: V DLY MS 1–6 / V DLY 1–6. Laws in 7.3.

### 5.5 Chamber network (Rich Chamber, Infinite Chamber)

A figure-of-eight tank of two halves. The input is stored (s1) and read at the predelay `pd` by two input diffusers (s2–s5 and s17–s20, allpasses dif6 and dif5). Half A (s6–s14): the diffused input and the end of half B (s6 = g·s28[t4]) enter the in-loop allpass ap5 (s7/s8); the RT HC one-pole (s9), the crossover low-pass (s10) and the RT LOW shelf with a mid gain (s11) follow, then two in-loop allpasses ap3 (s11–s14) with a mid gain each. Half B (s21–s28) takes the end of half A and the second diffused input, then the RT HC one-pole (s22) and three in-loop allpasses (ap5, ap3, ap3) with mid gains. Six mid gains per round trip. Each output sums 15 fixed taps of both halves, three early reflections from the input line (`rd`), an ATTACK tap of the diffused input, and an HC one-pole (s16, s30).

30 signals, 24 of them stored. Out L = s16, out R = s30.

```
s1   = x   ▸ stored
s2   = inp·s1[pd] + dif6·s2[t1]   ▸ stored
s3   = s2[t1] − dif6·s2   ▸ stored
s4   = s3[t2] + dif5·s4[t3]   ▸ stored
s5   = s4[t3] − dif5·s4
s6   = g·s28[t4]
s7   = 7/8·s5 − 1/2·s6 − 1/2·s6 + ap5·s7[t5]   ▸ stored
s8   = s7[t5] − ap5·s7   ▸ stored
s9   = rthc_x·s8[t6] + rthc_y·s9[1]   ▸ stored
s10  = xo_x·s9[1] + xo_y·s10[1]   ▸ stored
s11  = g·s9[1] + shelf·s10 + ap3·s11[t7]   ▸ stored
s12  = s11[t7] − ap3·s11   ▸ stored
s13  = g·s12[t8] + ap3·s13[t9]   ▸ stored
s14  = s13[t9] − ap3·s13   ▸ stored
s15  = 1/2·s8[t10] − 1/2·s8[t11] + 3/8·s8[t12] − 1/2·s11[t13] + 3/8·s12[t14] + 1/2·s13[t15] − 1/2·s14[t16]
        + 3/8·s23[t17] − 1/2·s24[t18] + 3/8·s24[t19] + 1/2·s25[t20] − 1/2·s26[t21] + 3/8·s26[t22] − 1/2·s27[t23]
        + 3/8·s28[t24] + rfl1·s1[rd1] + rfl2·s1[rd2] + rfl3·s1[rd3] + att0·s5
s16  = hc_y·s16[1] + hc_x·s15   ▸ stored, out L
s17  = inp·s1[pd] + dif6·s17[t25]   ▸ stored
s18  = s17[t25] − dif6·s17   ▸ stored
s19  = s18[t26] + dif5·s19[t27]   ▸ stored
s20  = s19[t27] − dif5·s19
s21  = g·s14[t28] + 7/8·s20
s22  = rthc_x·s21 + rthc_y·s22[1]   ▸ stored
s23  = s22 + ap5·s23[t29]   ▸ stored
s24  = s23[t29] − ap5·s23   ▸ stored
s25  = g·s24[t30] + ap3·s25[t31]   ▸ stored
s26  = s25[t31] − ap3·s25   ▸ stored
s27  = g·s26[t32] + ap3·s27[t33]   ▸ stored
s28  = s27[t33] − ap3·s27   ▸ stored
s29  = −1/2·s8[t34] + 3/8·s8[t35] + 1/2·s11[t36] − 1/2·s12[t37] + 3/8·s12[t38] − 1/2·s13[t39] + 3/8·s14[t40]
        + 1/2·s24[t41] − 1/2·s24[t42] + 3/8·s24[t43] − 1/2·s26[t44] + 3/8·s26[t45] + 1/2·s27[t46] − 1/2·s28[0]
        + 3/8·s28[t47] + rfl4·s1[rd4] + rfl5·s1[rd5] + rfl6·s1[rd6] + att0·s20
s30  = hc_y·s30[1] + hc_x·s29   ▸ stored, out R
```

| Symbol | Unit | Set by |
|---|---|---|
| `inp` | 1/32 | REV TIME S: 20/32 (0 when b ≥ 253: freeze) |
| `dif6` | 1/32 | DIFFUSION: slope 6, negative (7.4) |
| `dif5` | 1/32 | DIFFUSION: slope 5, negative (7.4) |
| `g` | 1/32 | REV TIME S: ⌊b/8⌋/32 (1 when b ≥ 253); RT MID S: ⌊b/8⌋/32; detector (8) |
| `ap5` | 1/32 | REV TIME S: in-loop allpass, slope 5 (7.6); DEFINITION: in-loop allpass, slope 5 (7.6); RT MID S: in-loop allpass, slope 5 (7.6); detector (8) |
| `rthc_x` | 1/32 | RT HC: ⌊b/8⌋/32 |
| `rthc_y` | 1/8 | RT HC: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `xo_x` | 1/32 | XOVER: ⌊b/8⌋/32 |
| `xo_y` | 1/8 | XOVER: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `shelf` | 1/8 | REV TIME S: shelf (7.6); RT LOW S: shelf (7.6); RT MID S: shelf (7.6); detector (8) |
| `ap3` | 1/32 | REV TIME S: in-loop allpass, slope 3 (7.6); DEFINITION: in-loop allpass, slope 3 (7.6); RT MID S: in-loop allpass, slope 3 (7.6); detector (8) |
| `rfl1` | 1/8 | RFL 1: ⌊b/32⌋/8 |
| `rfl2` | 1/8 | RFL 2: −⌊b/32⌋/8 |
| `rfl3` | 1/8 | RFL 3: ⌊b/32⌋/8 |
| `att0` | 1/8 | ATTACK: ⌊min(A0, 31)/4⌋/8 (7.4) |
| `hc_y` | 1/32 | HC: min(31, 32 − ⌊b/8⌋)/32 |
| `hc_x` | 1/32 | HC: ⌊b/8⌋/32 |
| `rfl4` | 1/8 | RFL 4: ⌊b/32⌋/8 |
| `rfl5` | 1/8 | RFL 5: −⌊b/32⌋/8 |
| `rfl6` | 1/8 | RFL 6: ⌊b/32⌋/8 |

Delays: `pd`: PDELAY MS; `rd1`…`rd6`: RFL MS 1–6. Laws in 7.3.

SIZE-scaled delays `t1`…`t47` at the smallest SIZE, at SIZE s = 21 (A SOFT AMBIENC) and at the largest SIZE (every value in the data file, `size.table`):

```
       s=0  s=21  s=38          s=0  s=21  s=38          s=0  s=21  s=38          s=0  s=21  s=38
t1      45   163   258   t2       1     3     6   t3      74   269   426   t4     422  1530  2427
t5     129   467   741   t6     721  2614  4146   t7     228   826  1311   t8     622  2255  3577
t9     285  1033  1638   t10     25    91   144   t11    327  1186  1881   t12    615  2230  3537
t13    218   790  1254   t14    388  1407  2231   t15     61   221   350   t16    175   635  1007
t17     67   243   385   t18    295  1070  1697   t19    649  2353  3732   t20     76   276   437
t21    201   728  1156   t22    560  2030  3220   t23    243   881  1397   t24    177   642  1018
t25     39   142   225   t26      1     3     5   t27     62   225   357   t28    443  1606  2548
t29    117   424   672   t30    855  3100  4917   t31    225   816  1294   t32    624  2262  3588
t33    428  1551  2461   t34    207   751  1191   t35    472  1711  2714   t36     65   235   374
t37    144   522   828   t38    605  2193  3479   t39    271   982  1558   t40    354  1283  2036
t41     88   319   506   t42    450  1631  2588   t43    827  2998  4756   t44     29   105   167
t45    388  1406  2231   t46     77   279   443   t47    324  1175  1863
f1 16 / 58 / 92, largest predelay / reflection count 25046 / 11656 / 817
```

### 5.6 Inverse network (Inverse Room)

The Chamber network with its loop opened: the input of half A is (7/8 − g2) times the diffused input (s6, s7) instead of the end of half B, and half B takes its own diffused input the same way (s21) instead of the end of half A. Each half is therefore a chain without recirculation; MD SLOPE sets the stage gains `g` (up to 63/32), so the output taps (`otap`, 3/8 or 5/8) rise or fall along the chain. The outputs are formed as in the Chamber.

30 signals, 24 of them stored. Out L = s16, out R = s30.

```
s1   = x   ▸ stored
s2   = 5/8·s1[pd] + dif6·s2[t1]   ▸ stored
s3   = s2[t1] − dif6·s2   ▸ stored
s4   = s3[t2] + dif5·s4[t3]   ▸ stored
s5   = s4[t3] − dif5·s4
s6   = g2·s5
s7   = 7/8·s5 − 1/2·s6 − 1/2·s6 + ap5·s7[t4]   ▸ stored
s8   = s7[t4] − ap5·s7   ▸ stored
s9   = rthc_x·s8[t5] + rthc_y·s9[1]   ▸ stored
s10  = xo_x·s9[1] + xo_y·s10[1]   ▸ stored
s11  = g·s9[1] + shelf·s10 + ap3·s11[t6]   ▸ stored
s12  = s11[t6] − ap3·s11   ▸ stored
s13  = g·s12[t7] + ap3·s13[t8]   ▸ stored
s14  = s13[t8] − ap3·s13   ▸ stored
s15  = 1/2·s8[t9] − 1/2·s8[t10] + otap·s8[t11] − 1/2·s11[t12] + otap·s12[t13] + 1/2·s13[t14] − 1/2·s14[t15]
        + otap·s23[t16] − 1/2·s24[t17] + otap·s24[t18] + 1/2·s25[t19] − 1/2·s26[t20] + otap·s26[t21] − 1/2·s27[t22]
        + otap·s28[t23] + rfl1·s1[rd1] + rfl2·s1[rd2] + rfl3·s1[rd3] + att0·s5
s16  = hc_y·s16[1] + hc_x·s15   ▸ stored, out L
s17  = 5/8·s1[pd] + dif6·s17[t24]   ▸ stored
s18  = s17[t24] − dif6·s17   ▸ stored
s19  = s18[t25] + dif5·s19[t26]   ▸ stored
s20  = s19[t26] − dif5·s19
s21  = −g2·s20 + 7/8·s20
s22  = rthc_x·s21 + rthc_y·s22[1]   ▸ stored
s23  = s22 + ap5·s23[t27]   ▸ stored
s24  = s23[t27] − ap5·s23   ▸ stored
s25  = g·s24[t28] + ap3·s25[t29]   ▸ stored
s26  = s25[t29] − ap3·s25   ▸ stored
s27  = g·s26[t30] + ap3·s27[t31]   ▸ stored
s28  = s27[t31] − ap3·s27   ▸ stored
s29  = −1/2·s8[t32] + otap·s8[t33] + 1/2·s11[t34] − 1/2·s12[t35] + otap·s12[t36] − 1/2·s13[t37] + otap·s14[t38]
        + 1/2·s24[t39] − 1/2·s24[t40] + otap·s24[t41] − 1/2·s26[t42] + otap·s26[t43] + 1/2·s27[t44] − 1/2·s28[0]
        + otap·s28[t45] + rfl4·s1[rd4] + rfl5·s1[rd5] + rfl6·s1[rd6] + att0·s20
s30  = hc_y·s30[1] + hc_x·s29   ▸ stored, out R
```

| Symbol | Unit | Set by |
|---|---|---|
| `dif6` | 1/32 | DIFFUSION: slope 6, negative (7.4) |
| `dif5` | 1/32 | DIFFUSION: slope 5, negative (7.4) |
| `g2` | 1/32 | MD SLOPE %: ⌊5b/64⌋/32 |
| `ap5` | 1/32 | MD SLOPE %: in-loop allpass, slope 5 (7.6); DEFINITION: in-loop allpass, slope 5 (7.6) |
| `rthc_x` | 1/32 | RT HC: ⌊b/8⌋/32 |
| `rthc_y` | 1/8 | RT HC: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `xo_x` | 1/32 | XOVER: ⌊b/8⌋/32 |
| `xo_y` | 1/8 | XOVER: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `g` | 1/32 | MD SLOPE %: ⌊b/4⌋/32 (up to 63/32) |
| `shelf` | 1/8 | LO SLOPE %: shelf (7.6); MD SLOPE %: shelf (7.6) |
| `ap3` | 1/32 | MD SLOPE %: in-loop allpass, slope 3 (7.6); DEFINITION: in-loop allpass, slope 3 (7.6) |
| `otap` | 1/8 | MD SLOPE %: 5/8 if b > 128, else 3/8 |
| `rfl1` | 1/8 | RFL 1: ⌊b/32⌋/8 |
| `rfl2` | 1/8 | RFL 2: −⌊b/32⌋/8 |
| `rfl3` | 1/8 | RFL 3: ⌊b/32⌋/8 |
| `att0` | 1/8 | ATTACK: ⌊min(A0, 31)/4⌋/8 (7.4) |
| `hc_y` | 1/32 | HC: min(31, 32 − ⌊b/8⌋)/32 |
| `hc_x` | 1/32 | HC: ⌊b/8⌋/32 |
| `rfl4` | 1/8 | RFL 4: ⌊b/32⌋/8 |
| `rfl5` | 1/8 | RFL 5: −⌊b/32⌋/8 |
| `rfl6` | 1/8 | RFL 6: ⌊b/32⌋/8 |

Delays: `pd`: PDELAY MS; `rd1`…`rd6`: RFL MS 1–6. Laws in 7.3.

SIZE-scaled delays `t1`…`t45` at the smallest SIZE, at SIZE s = 21 (A INVERSE ROOM) and at the largest SIZE (every value in the data file, `size.table`):

```
       s=0  s=21  s=38          s=0  s=21  s=38          s=0  s=21  s=38          s=0  s=21  s=38
t1      45   163   258   t2       1     3     6   t3      74   269   426   t4     129   467   741
t5     721  2614  4146   t6     228   826  1311   t7     622  2255  3577   t8     285  1033  1638
t9      25    91   144   t10    327  1186  1881   t11    615  2230  3537   t12    218   790  1254
t13    388  1407  2231   t14     61   221   350   t15    175   635  1007   t16     67   243   385
t17    295  1070  1697   t18    649  2353  3732   t19     76   276   437   t20    201   728  1156
t21    560  2030  3220   t22    243   881  1397   t23    177   642  1018   t24     39   142   225
t25      1     3     5   t26     62   225   357   t27    117   424   672   t28    855  3100  4917
t29    225   816  1294   t30    624  2262  3588   t31    428  1551  2461   t32    207   751  1191
t33    472  1711  2714   t34     65   235   374   t35    144   522   828   t36    605  2193  3479
t37    271   982  1558   t38    354  1283  2036   t39     88   319   506   t40    450  1631  2588
t41    827  2998  4756   t42     29   105   167   t43    388  1406  2231   t44     77   279   443
t45    324  1175  1863
f1 16 / 58 / 92, largest predelay / reflection count 25046 / 11656 / 817
```

### 5.7 Plate network (Rich Plate)

A single loop through both halves. The input (s1) is read at the predelay `pd`; each input passes three diffuser allpasses (s3–s8, s18–s23). Half A (s9–s15): the end of the loop (s9 = g·s29[t4]) and the left diffused input enter the in-loop allpass s10/s11; the RT HC one-pole (s12), the crossover (s13) with the RT LOW shelf (s14) and a second allpass (s14/s15) follow. The loop continues through s30/s31, then takes the right diffused input (s24), and runs through s25–s29 (an allpass, a mid gain, the RT HC one-pole, an allpass) back to half A. Five mid gains and five in-loop allpasses per round trip. The outputs are formed as in the Chamber (15 taps, three reflections, ATTACK, HC).

33 signals, 27 of them stored. Out L = s17, out R = s33.

```
s1   = x   ▸ stored
s2   = 5/8·s1[pd]   ▸ stored
s3   = s2 + dif6·s3[t1]   ▸ stored
s4   = s3[t1] − dif6·s3   ▸ stored
s5   = s4 + dif5·s5[t2]   ▸ stored
s6   = s5[t2] − dif5·s5   ▸ stored
s7   = s6 + dif4·s7[t3]   ▸ stored
s8   = s7[t3] − dif4·s7
s9   = g·s29[t4]
s10  = 7/8·s8 − 1/2·s9 − 1/2·s9 + ap5·s10[t5]   ▸ stored
s11  = s10[t5] − ap5·s10   ▸ stored
s12  = rthc_x·s11[t6] + rthc_y·s12[1]   ▸ stored
s13  = xo_x·s12[1] + xo_y·s13[1]   ▸ stored
s14  = g·s12[1] + shelf·s13 + ap5·s14[t7]   ▸ stored
s15  = s14[t7] − ap5·s14   ▸ stored
s16  = 1/2·s11[t8] − 1/2·s11[t9] + 3/8·s11[t10] − 1/2·s14[t11] + 3/8·s15[t12] + 3/8·s15[t13] + 1/2·s30[t14]
        − 3/8·s31[t15] + 3/8·s31[t16] − 1/2·s25[t17] + 1/2·s25[t18] + 3/8·s25[t19] + 1/2·s28[t20] − 3/8·s28[t21]
        + 3/8·s29[t22] + rfl1·s1[rd1] + rfl2·s1[rd2] + rfl3·s1[rd3] + att0·s8
s17  = hc_y·s17[1] + hc_x·s16   ▸ stored, out L
s18  = 5/8·s1[pd] + dif6·s18[t23]   ▸ stored
s19  = s18[t23] − dif6·s18   ▸ stored
s20  = s19 + dif5·s20[t24]   ▸ stored
s21  = s20[t24] − dif5·s20   ▸ stored
s22  = s21 + dif4·s22[t25]   ▸ stored
s23  = s22[t25] − dif4·s22
s24  = g·s31[t26] + 7/8·s23 + ap5·s24[t27]   ▸ stored
s25  = s24[t27] − ap5·s24   ▸ stored
s26  = g·s25[t28]
s27  = rthc_x·s26 + rthc_y·s27[1]   ▸ stored
s28  = s27 + ap5·s28[t29]   ▸ stored
s29  = s28[t29] − ap5·s28   ▸ stored
s30  = g·s15[t30] + ap5·s30[t31]   ▸ stored
s31  = s30[t31] − ap5·s30   ▸ stored
s32  = −1/2·s11[t32] + 1/2·s11[t33] + 3/8·s11[t34] − 1/2·s15[t35] + 3/8·s15[t36] − 3/8·s15[t37] + 1/2·s30[t38]
        + 3/8·s31[t39] + 1/2·s24[t40] + 1/2·s25[t41] − 3/8·s25[t42] + 3/8·s25[t43] − 1/2·s28[t44] + 3/8·s29[t45]
        + 3/8·s29[t46] + rfl4·s1[rd4] + rfl5·s1[rd5] + rfl6·s1[rd6] + att0·s23
s33  = hc_y·s33[1] + hc_x·s32   ▸ stored, out R
```

| Symbol | Unit | Set by |
|---|---|---|
| `dif6` | 1/32 | DIFFUSION: slope 6, negative (7.4) |
| `dif5` | 1/32 | DIFFUSION: slope 5, negative (7.4) |
| `dif4` | 1/32 | DIFFUSION: slope 4, negative (7.4) |
| `g` | 1/32 | RT MID S: ⌊b/8⌋/32; detector (8) |
| `ap5` | 1/32 | RT MID S: in-loop allpass, slope 5 (7.6); DEFINITION: in-loop allpass, slope 5 (7.6); detector (8) |
| `rthc_x` | 1/32 | RT HC: ⌊b/8⌋/32 |
| `rthc_y` | 1/8 | RT HC: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `xo_x` | 1/32 | XOVER: ⌊b/8⌋/32 |
| `xo_y` | 1/8 | XOVER: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `shelf` | 1/8 | RT LOW S: shelf (7.6); RT MID S: shelf (7.6); detector (8) |
| `rfl1`…`rfl2` | 1/8 | RFL 1–2: −⌊b/32⌋/8 |
| `rfl3` | 1/8 | RFL 3: ⌊b/32⌋/8 |
| `att0` | 1/8 | ATTACK: ⌊min(A0, 31)/4⌋/8 (7.4) |
| `hc_y` | 1/32 | HC: min(31, 32 − ⌊b/8⌋)/32 |
| `hc_x` | 1/32 | HC: ⌊b/8⌋/32 |
| `rfl4`…`rfl5` | 1/8 | RFL 4–5: −⌊b/32⌋/8 |
| `rfl6` | 1/8 | RFL 6: ⌊b/32⌋/8 |

Delays: `pd`: PDELAY MS; `rd1`…`rd6`: RFL MS 1–6. Laws in 7.3.

SIZE-scaled delays `t1`…`t46` at the smallest SIZE, at SIZE s = 29 (A VOX PLATE) and at the largest SIZE (every value in the data file, `size.table`):

```
       s=0  s=29  s=41          s=0  s=29  s=41          s=0  s=29  s=41          s=0  s=29  s=41
t1       7    32    42   t2      22   101   134   t3      55   255   337   t4     409  1833  2423
t5     111   513   679   t6     739  3418  4527   t7     232  1073  1421   t8      47   217   288
t9     319  1475  1954   t10    592  2738  3626   t11    117   541   716   t12    176   814  1078
t13    485  2243  2970   t14    118   546   723   t15     37   171   226   t16    325  1503  1990
t17    165   763  1011   t18    410  1897  2512   t19    686  3173  4202   t20    164   759  1004
t21    422  1952  2584   t22    258  1193  1580   t23      8    37    49   t24     27   125   166
t25     46   213   282   t26    339  1568  2076   t27    122   564   747   t28    850  3932  5207
t29    441  2040  2701   t30    618  2858  3785   t31    389  1799  2383   t32    193   893  1183
t33    433  2003  2653   t34    721  3335  4417   t35     30   139   184   t36    335  1549  2052
t37    608  2812  3724   t38    295  1364  1807   t39    191   884  1170   t40    100   463   613
t41    307  1420  1881   t42    584  2701  3577   t43    841  3890  5151   t44    276  1277  1690
t45    105   485   643   t46    393  1817  2407
f1 16 / 74 / 98, largest predelay / reflection count 26638 / 11287 / 4934
```

### 5.8 Hall network (Concert Hall)

The input passes the HC one-pole (s4), which also feeds the predelay and the reflections. Two tank halves are cross-coupled (s15 reads the end of the right half, s36 the end of the left). Each half runs DIFFUSION allpasses (s15–s18 | s36–s39), nested allpass chains with the DEFINITION and in-loop coefficients (s2–s12 | s24–s35) that contain one modulated tap each (s13/s14 | s28/s29, section 9), a mid gain with its own crossover and RT LOW shelf, into which half the predelayed input enters (s19/s20 | s40/s41), and the RT HC stage: in the left half the fixed gain rthc_x·rthc_y (s21, s22), in the right half a one-pole (s42). The outputs sum ATTACK taps and two reflections each, with no output filter.

43 signals, 36 of them stored. Out L = s23, out R = s43.

```
s1   = x   ▸ stored
s2   = s5[t1] + def·s2[t2]   ▸ stored
s3   = s2[t2] − def·s2   ▸ stored
s4   = hc_x·s1[0] + hc_y·s4[1]   ▸ stored
s5   = s18[t3] + ap5·s3[t4]   ▸ stored
s6   = s3[t4] − ap5·s5   ▸ stored
s7   = s6[t5] + ap5·s10[t6]   ▸ stored
s8   = s10[t6] − ap5·s7   ▸ stored
s9   = s7[t7] + def·s12[t8]   ▸ stored
s10  = s12[t8] − def·s9   ▸ stored
s11  = s9[t9] + def·s14[t10]   ▸ stored
s12  = s14[t10] − def·s11   ▸ stored
s13  = s11[mB1] − 1/2·s11[mA1] − 1/2·s11[mA1]
s14  = s11[mA1] + m1·s13   ▸ stored
s15  = s42[2] + dif6·s15[t11]   ▸ stored
s16  = s15[t11] − dif6·s15   ▸ stored
s17  = s16[t12] + dif5·s17[t13]   ▸ stored
s18  = s17[t13] − dif5·s17   ▸ stored
s19  = xo_y·s19[1] + xo_x·s8[t14]   ▸ stored
s20  = g·s8[t14] + 1/2·s4[pd] + shelf·s19
s21  = rthc_x·s20
s22  = rthc_y·s21   ▸ stored
s23  = att3·s8[t15] + att0e·s18[t16] + att1e·s6[t17] − att1e·s27[t18] + rfl1·s4[rd1] + rfl2·s4[rd2]   ▸ out L
s24  = s26[t19] + def·s24[t20]   ▸ stored
s25  = s24[t20] − def·s24   ▸ stored
s26  = s39[t21] + ap5·s25[t22]   ▸ stored
s27  = s25[t22] − ap5·s26   ▸ stored
s28  = s34[mB2] − 1/2·s34[mA2] − 1/2·s34[mA2]
s29  = s34[mA2] + m2·s28   ▸ stored
s30  = s27[t23] + ap5·s33[t24]   ▸ stored
s31  = s33[t24] − ap5·s30   ▸ stored
s32  = s30[t25] + def·s35[t26]   ▸ stored
s33  = s35[t26] − def·s32   ▸ stored
s34  = s32[t27] + def·s29[t28]   ▸ stored
s35  = s29[t28] − def·s34   ▸ stored
s36  = s22[1] + dif6·s36[t29]   ▸ stored
s37  = s36[t29] − dif6·s36   ▸ stored
s38  = s37[t30] + dif5·s38[t31]   ▸ stored
s39  = s38[t31] − dif5·s38   ▸ stored
s40  = xo_y·s40[1] + xo_x2·s31[0]   ▸ stored
s41  = g·s31[0] + 1/2·s4[pd] + shelf·s40
s42  = −rthc_x·s41 + rthc_y2·s42[1]   ▸ stored
s43  = att3·s31[0] + att0e·s39[t32] + att1e·s27[t33] + att1·s6[t34] + rfl3·s4[rd3] + rfl4·s4[rd4]   ▸ out R
```

Special rules:

* s14: when m1 = 32/32, s14 = s11[mB1] exactly (section 9.1).
* s29: when m2 = 32/32, s29 = s34[mB2] exactly (section 9.1).

| Symbol | Unit | Set by |
|---|---|---|
| `def` | 1/32 | DEFINITION: min(8, ⌊5e/8⌋)/32, e = 63 − ⌊b/4⌋ |
| `hc_x` | 1/32 | HC: ⌊b/8⌋/32 |
| `hc_y` | 1/32 | HC: min(31, 32 − ⌊b/8⌋)/32 |
| `ap5` | 1/32 | RT MID S: in-loop allpass, slope 5 (7.6); DEFINITION: in-loop allpass, slope 5 (7.6); detector (8) |
| `m1` | 1/32 | delay modulation (9.1) |
| `dif6` | 1/32 | DIFFUSION: slope 6 (7.4) |
| `dif5` | 1/32 | DIFFUSION: slope 5 (7.4) |
| `xo_y` | 1/32 | XOVER: min(31, 32 − ⌊b/8⌋)/32 |
| `xo_x` | 1/32 | XOVER: ⌊b/8⌋/32 |
| `g` | 1/32 | RT MID S: ⌊b/8⌋/32; detector (8) |
| `shelf` | 1/32 | RT LOW S: shelf (7.6); RT MID S: shelf (7.6); detector (8) |
| `rthc_x` | 1/32 | RT HC: −⌊b/8⌋/32 |
| `rthc_y` | 1/32 | RT HC: 1 + (32 − ⌊b/8⌋)/32; 1 when b < 8 |
| `att3` | 1/32 | ATTACK: A3/32 (7.4) |
| `att0e` | 1/8 | ATTACK: ⌊min(A0, 31)/4⌋/8 (7.4) |
| `att1e` | 1/8 | ATTACK: ⌊min(A1, 31)/4⌋/8 (7.4) |
| `rfl1`…`rfl2` | 1/8 | RFL 1–2: ⌊b/32⌋/8 |
| `m2` | 1/32 | delay modulation (9.1) |
| `xo_x2` | 1/8 | XOVER: ⌊b/32⌋/8 |
| `rthc_y2` | 1/8 | RT HC: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| `att1` | 1/32 | ATTACK: −A1/32 (7.4) |
| `rfl3`…`rfl4` | 1/8 | RFL 3–4: ⌊b/32⌋/8 |

Delays: `pd`: PDELAY MS; `rd1`…`rd4`: RFL MS 1–4; `mA1`…`mA2`, `mB1`…`mB2`: delay modulation (9.1). Laws in 7.3.

SIZE-scaled delays `t1`…`t34` at the smallest SIZE, at SIZE s = 46 (A SUSTAIN HALL) and at the largest SIZE (every value in the data file, `size.table`):

```
       s=0  s=46  s=49          s=0  s=46  s=49          s=0  s=46  s=49          s=0  s=46  s=49
t1      69   703   742   t2     171  1742  1838   t3     119  1212  1279   t4       1    10    11
t5      31   316   333   t6     126  1283  1354   t7       1    10    11   t8      86   877   925
t9       1    10    10   t10    128  1304  1376   t11     84   225   225   t12      1     3     3
t13    138   371   371   t14    125  1274  1344   t15      9    92    97   t16      1    10    10
t17      1    10    10   t18      1    10    10   t19     47   478   505   t20    178  1814  1914
t21    142  1447  1526   t22      1    10    11   t23     32   326   344   t24    133  1355  1430
t25      1    10    10   t26     76   775   817   t27      1    10    11   t28    148  1507  1591
t29     72   193   193   t30      1     3     3   t31    116   311   311   t32     12   122   129
t33     31   316   333   t34     30   306   322
f1 16 / 163 / 172, largest predelay / reflection count 29725 / 14722 / 13804
```


### 5.9 Program change

When a program is loaded the unit mutes its output and clears its delay lines: a new program starts with every
stored value at 0, and the wet gain is off during the load (10.3).

# Part II — Parameters and control

Part II covers how parameter values become network values (sections 6 and 7), the control that runs while audio
plays (sections 8 and 9), and the input, output and mix (section 10).

## 6. Parameters

### 6.1 The parameter matrix

Each algorithm has a matrix of up to 10 rows × 10 columns of parameters ("row.column"). Row 0 holds the global
parameters (MIX, FX ADJ, SOFT KNOB and per-algorithm ones); the other rows group a parameter family, often as a MASTER
in column 0 and voices 1–6 in columns 1–6. The data file lists every parameter of every algorithm with its range
`lo`…`hi` of stored values and, for every value: the display text, the control value and the network values that
change when only this parameter changes (section 13).

### 6.2 Patches (Dynamic MIDI)

A program holds up to 10 patches. Each has a **source**, a **destination** parameter (row·10 + column) and a **scale**
s (−128…127). Sources:

| Source | Name | Value x |
|---|---|---|
| 0 | PATCH OFF | – |
| 1–32 | CTRL 0 … CTRL 31 (2 = MOD WHEEL, 3 BREATH, 5 FOOT CTRL, 6 PORT TIME, 7 DATA ENTR, 8 VOLUME) | MIDI control change 0–31, 0…127 |
| 33–64 | SUSTAIN (64), PORT SW, SOSTENUTO, SOFT PED, SWITCH 68 … SWITCH 95 | control change 64–95, 0…127 |
| 65 | PCH WHEEL | pitch bend, MSB m: x = m − 64, then x + 1 if x < 0 (−63…63; LSB ignored) |
| 66 | AFTER TCH | channel aftertouch 0…127 |
| 67 | LAST NOTE | note number of the last note-on with velocity > 0 |
| 68 | LAST VEL | its velocity 1…127 |
| 69 | SOFT KNOB | the SOFT KNOB parameter (0.2), 0…127 |
| 70 | MIDI CLK | tempo from MIDI clock, x = BPM − 64 (section 6.6); set B: not available |

Only messages on the unit's MIDI channel count. Control changes 32–63 are ignored. Every source keeps its last value
across program changes and starts at 0 after power-up (the SOFT KNOB source follows the knob's stored value).

**Law (exact).** With s' = s + 1 for s ≥ 0 and s' = s for s < 0 (so the scale runs −128…−1, 1…128), every parameter
uses the **effective value**

    v_eff = clamp( v + ⌊(64 + Σ s'_i · x_i) / 128⌋,  lo, hi )

over the patches i to that parameter: v plus the patch sum in units of 1/128 step, rounded half up, limited to the
parameter's range. A scale of 127 (s' = 128) moves the parameter one step per source step; several patches to one
parameter add. The display shows `<` or `>` when a patch drives the value against a limit. A simulator evaluates the
law whenever a source changes and recomputes that parameter's network values.

SOFT KNOB (0.2), DECAY OPT and empty matrix cells cannot be patched. A patch to a **MASTER** parameter (LVL / DLY /
FDBK / PAN MST, PCH / RESN / PDL MST, LC / HC MST) adds the same s'·x to every voice of its row, so the voices move
together.

### 6.3 Control values

Each parameter's effective value v gives its control value b (exact; the data file lists every value):

| Family | Law |
|---|---|
| Percent (DIFFUSION, ATTACK, DEFINITION, CHORUSING) | b = ⌊254·v/99⌋ for v = 0…99 (table `percent`) |
| Signed percent (V FDBK, V RESN, V1/V2 FDBK, V3/V6 FDBK) | table (data file) |
| RT LOW, RT MID, RTL/RTM STOP, REV TIME | b = 8·(v + 16) (v = −16…15 → 0…248); REV TIME v = 16 (INF) → 254 |
| HC, RT HC, XOVER, V HC, HC L/R, LO/MD SLOPE | b = 8·(v + 16) |
| V LC | set A: table (data file, 8 distinct settings); set B: b = 8·(v + 15) |
| SIZE (DURATION) | b = v + 24 (Hall), v + 21 (Plate), v + 19 (Chamber, Infinite, Inverse DURATION) |
| PDELAY | b = v + 127; delay count 68·b samples (2.009 ms per step) |
| Delays in ms (V DLY MS, RFL MS) | a sample count (16 bits) |
| Rhythm delays (V DLY in beats) | count n·⌊T/24⌋ for n/24 of a beat (section 6.5) |
| Levels (V LVL, RFL) | b = 4·n, n = min(63, round(64·10^(dB/20))); −3 dB has n = 46; OFF = 0 |
| Pan | table 0 (50 LT) … 254 (50 RT) (data file) |
| Resonator pitch (V PITCH) | a loop length 12…976 samples (data file) |
| Resonator predelay (V PDL MS) | b = v + 102 (section 7.3) |
| GATE | OFF, or a hold time of b = v + 128 detector ticks (× 18 ms); the unit displays hold 0 as `MS` with no number (data text) |
| DECAY OPT | on / off |
| CHORUS (voices, mode) | c = number of voices (1…6) for mode S, 128 + number of voices for mode T; OFF = 0 (section 9.2) |

MIX and FX ADJ have no control values; they set the wet and dry gains (section 10.3). The MASTER parameters act on
their voices (6.4). A RATE change recomputes every rhythm voice delay (6.5).

### 6.4 MASTER parameters

A MASTER parameter (column 0 of a voice row) is relative. Turning it by Δ adds Δ to the stored value of every voice of
its row; the voices' own limits apply only to their effective values, so a voice driven past a limit keeps its offset
and returns when the MASTER comes back. The MASTER's own stored value is limited to its range (±35, ±30, ±100 …) and has
no other effect.

### 6.5 Rhythm tempo

In Chorus + Rhythm, Multiband Rhythm and Rhythmic Chords the voice delays are set in 24ths of a beat. With the tempo
RATE in BPM (64…191), T = round(60·fs / BPM) samples per beat (table `tempo_samples_per_beat`, index BPM − 64), and a
voice at n/24 beat gets the count n·⌊T/24⌋ (exact). At 64 BPM, 1/24 → 1 322 samples and 6/24 → 7 932. Chorus + Rhythm
lowers n until the count is at most 14 847. Rhythmic Chords rounds the count to steps of 128 samples:
128·min(196, 2·⌊(n·⌊T/24⌋ + 128)/256⌋). The delays then follow section 7.3.

### 6.6 MIDI clock (set A)

The unit counts 24 MIDI clock messages per beat and times each beat in units of 8 samples (236 µs). With d = such
units per beat, it updates the tempo when |8·d − T_cur| ≥ 50 samples: the new tempo index is the first i (0…126) with
T_i < 8·d + 28 (T_i = round(60·fs/(64 + i))), else 127. MIDI clock reaches a program only as patch source 70 (x = i);
the factory programs patch it to RATE or to the delay MASTER with scale 127. A tempo given in BPM
gives x = clamp(BPM − 64, 0, 127). Set B ignores MIDI clock.

## 7. Network values from control values

Every law below is exact. A program at rest uses the effective values with all patch sources at rest; the data file
lists the result of every law for every value of every parameter (with the other parameters at the algorithm's base
program), and `reverb_build.py` applies them and rebuilds all 84 factory programs identically. Notation: b = the
parameter's control value; a coefficient is given as units / resolution.

**Signs and authority.** The general laws in 7.1–7.6 give magnitudes. The value a network uses can be negative
(Chamber, Plate and Inverse diffusers, several reflection levels, the Multiband V LC input coefficients, the Chords
V3 FDBK, the Hall's RT HC input and ATTACK 1) or have the form 1 + k (the Hall's left RT HC stage, 7.1). The symbol tables of section 5
and the parameter maps of 7.9 give every symbol's law **with its sign and form as the network uses it**. The per-value
tables of the data file (`set`) and the closed forms of 5 and 7.9 give the same values.

### 7.1 One-pole filters

Every high-cut (HC, RT HC, XOVER, V HC, HC L/R) is a one-pole low-pass y = p·u + q·y[1] with p ≈ b/256, where b is
the control value 8·(v + 16). Its input coefficient `_x` has the magnitude ⌊b/8⌋/32. Its feedback coefficient `_y`
is either (32 − ⌊b/8⌋)/32 (a 1/32 symbol; written min(31, …) where the program limits it to 31/32) or, where the
symbol has a resolution of 1/8, min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8: the feedback is then rounded to 1/8 and the filter's DC
gain p/(1 − q) is not exactly 1 (0.625…1.0). The displayed frequency is −fs·ln(1 − b/256)/2π. V LC (Multiband) is
the complementary one-pole high-pass with the same magnitudes; its `_x` symbol carries a negative value (the listings
give its form). One stage differs from this pattern: the Hall's left RT HC stage, whose `_y` symbol has the form
1 + k and which is a fixed gain, not a one-pole (5.8).

### 7.2 Levels, pan, feedback, resonance

| Family | Network values |
|---|---|
| Voice level (V LVL) | ⌊b/8⌋/32, b = 4·n (6.3), so ⌊n/2⌋/32 |
| Reflection level (RFL) | ⌊b/32⌋/8 |
| Pan (V PAN) | right ⌊b/8⌋/32 (or ⌊b/32⌋/8); left min(31, 32 − ⌊b/8⌋)/32 (or min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8); b = 0 (50 LT) … 254 (50 RT) |
| Chorus feedback (V FDBK) | ⌊(b − 128)/16⌋/8 for b ≥ 128, −min(7, ⌊(131 − b)/16⌋)/8 below; b = 128 + ⌊127·v/97⌋ |
| Multiband feedback (V1/V2 FDBK) | ⌊b/8⌋/32 |
| Resonance (V RESN) | clamp(⌊(b − 128)/4⌋, −31, 31)/32; b as for FDBK |
| Chords cross feedback (V3 FDBK −, V6 FDBK +) | ⌊b/8⌋/32 |

### 7.3 Delays

A delay parameter's tap delay is its count plus a fixed offset:

| Delay | Law |
|---|---|
| Voice delays `dly` (Chorus, Multiband; V DLY MS and the rhythm V DLY) | d = c' + 1, c' = count, or 257·h when ⌊count/256⌋ > h; h = 57 (Chorus: 14 649 samples, 432 ms), 118 (Multiband: 30 326 samples, 896 ms) |
| Resonator lengths `pit` (Chords) | d = length + 1 (length 12…976 from the pitch table) |
| Resonator predelays `pdl` (Resonant Chords V PDL MS, Rhythmic Chords V DLY) | d = 128·b + 1 |
| Predelay `pd` and reflections `rd` (Chamber, Plate, Hall, Infinite, Inverse) | d = min(count, C(SIZE)) + 1; C = the largest count at that SIZE (`max_count` of the SIZE table, 7.5), the largest that keeps the tap inside the delay memory |
| DIFFUSION = 0 (Chorus, Multiband) | the diffusers are bypassed: the network's bypass rule (5.1, 5.3, 5.4) |

For example the Chamber's reflection 3 at a count of 927 sits at a delay of 928 samples, and at the largest SIZE every
long reflection is limited to the count C = 817.

**Delay-memory limit.** All delay lines of a program share one memory of 32 768 samples, and C keeps every predelay
and reflection tap inside it: the count is limited to C as above.

**Delay changes while audio runs.** A change of a delay parameter's control value while the program runs (an edit, a
patch source, MIDI, or a RATE / MIDI-clock tempo change of the rhythm delays, 6.5) is applied in one of four ways:

| Parameters | Applied as |
|---|---|
| Voice delays: V DLY MS and V DLY (Chorus, Multiband), V PITCH, V PDL MS and V DLY (Chords); reflections RFL MS (Chamber, Infinite, Plate, Hall, Inverse) | per-tap ramp |
| PDELAY (Chamber, Infinite, Plate, Hall, Inverse) | group ramp |
| SIZE, DURATION | a program load with the new value (5.9) |
| DIFFUSION to or from 0 (the bypass, Chorus, Multiband) | the taps switch at once |

The delay-modulation taps (9) take no part in this. Changes are taken one at a time, in the order they arrive: patches in
the order of the program's patch list (6.2), a tempo or MASTER change voice by voice (each voice's parts as below). A
value that is not a delay (a level, say) is set when it is taken, so it gives the k of a later ramp or waits for a
running one.

**The ramped coefficients** are those of the products that read the changed delay, as listed in section 5 (data:
`delay_ramp` of each network, 13.2). Each product reads the delay through its own tap, which switches in that
product's ramp:

| Network | Delay | Ramped coefficient |
|---|---|---|
| Chorus | dlyn | the start 31/32 of s(n + 3) (s4 … s9) |
| Chords | pitn | resn (the term of s3, s6, s9, s13, s16, s19 that reads pitn) |
| Chords | pdln | the start 31/32 of the same signal; for pdl3 first fbm, for pdl6 first fbp (both in s2) |
| Multiband | dly1, dly2 | the start 1 of s8, s14 |
| Multiband | dly3 … dly6 | lvl3 … lvl6 (the starts of s21, s27, s33, s39) |
| Multiband B | dly1, dly2 | the start 1 of s8, s14 |
| Multiband B | dly3 … dly6 | lvl3 … lvl6 (the starts of s20, s25, s30, s35) |
| Chamber (Infinite) | rd1 … rd6 | rfl1 … rfl6 (terms of s15 and s29) |
| Chamber (Infinite) | pd | the starts inp of s2 and s17 |
| Inverse | rd1 … rd6 | rfl1 … rfl6 (terms of s15 and s29) |
| Inverse | pd | the starts 5/8 of s2 and s17 |
| Plate | rd1 … rd6 | rfl1 … rfl6 (terms of s16 and s32) |
| Plate | pd | the starts 5/8 of s2 and s18 |
| Hall | rd1 … rd4 | rfl1 … rfl4 (terms of s23 and s43) |
| Hall | pd | the terms 1/2 (resolution 1/8) of s20 and s41 |

**Per-tap ramp.** For each ramped coefficient in turn (in the order of the table), with k = its magnitude in units of
its resolution (1/8 or 1/32) when the ramp starts, and times counted in samples from the start of the block after the
change (each step takes effect at its own sample):

1. The magnitude steps down by one unit per step, with its sign kept: step j (j = 1 … k) at 2j.
2. The delay takes its new value at 2k + 3.
3. The magnitude steps back up by one unit per step: step j at 2k + 3 + 2j, back to k.

The next coefficient's ramp starts with its first step 2 samples after the last step of the previous one. Special
cases:

* k = 0: no ramp; the delay switches at once.
* The start 1 of Multiband dly1, dly2 (`unity`) ramps with k = 32: step 1 down gives 31/32, the others 30/32 … 0;
  up, steps 1 … 30 give 1/32 … 30/32 and step 31 gives 1.
* A 1/32 coefficient of magnitude exactly 16 is 0 from its first step down until its last step up, and 16 again at
  that last step (the times of a ramp with k = 16).

**Counts in two parts.** The counts of V DLY MS (Chorus, Multiband), RFL MS and the rhythm V DLY of Chorus + Rhythm
and Multiband Rhythm come in two parts, high = ⌊count/256⌋ and low = count mod 256, taken in that order. Each part
that changes gives one complete per-tap ramp, also when the delay that results does not change: the first ramp sets
the delay of the count (new high, old low) by the law above, the second the final delay. The second part, like any
other change that waits (the next voice of a tempo change), is taken 220 samples after the previous ramp has ended. A
change of only one part gives one ramp.

**During a per-tap ramp**, and the 220 samples before a change that waits, the unit's control does nothing else: further
parameter changes wait, no delay-modulation updates run (9.3: no time budget is added), no group-ramp passes run, and
no detector tick runs. The tick counting of 8.5
goes on; a fast or slow tick that falls due in that time runs once when it ends, with the level of that
sample (both kinds: one sequence, fast first, 8.5).

**Group ramp (PDELAY).** The products that read pd (table) are ramped together. Each has a counter e in units of 1/32
with a fixed rest value, its listing magnitude in 1/32 units (a 1/8 coefficient m/8 counts as 4m): Chamber, Infinite,
Inverse, Plate 20, Hall 16 (the Infinite Chamber's counters are 0 while it is at INF). The ramp runs in passes, one every Tg samples (Chamber,
Infinite, Inverse 42; Plate 41; Hall 44; `delay_ramp.group`), the first pass 160 samples after the start of the block
after the change, counted outside pauses; each pass takes effect at its own sample:

1. **Down:** each pass lowers every e above 0 by 1. A product's coefficient is e/32 (1/32 resolution) or ⌊e/4⌋/8
   (1/8 resolution), with its sign kept.
2. **Switch:** the first pass that finds every e at 0 sets pd to the latest PDELAY value.
3. **Up:** each following pass raises every e below its rest value by 1; the pass that finds every e at its rest
   value ends the ramp. (Infinite Chamber: no up phase when it is at INF at the switch, inp then stays 0; a rewrite of
   the RT-dependent values during the ramp sets inp by the RT law (8.2) until the next pass.)

A PDELAY change during a group ramp: pd takes the latest count at the switch. If the new count differs from the count
pd was last set to, a ramp in its up phase turns down again from its current counters (and without a ramp running, a
ramp starts); if it equals that count, no new ramp starts and a running ramp goes on. The passes pause during per-tap
ramps and during the detector's busy time (8.5); a tick and a pass on the same sample: the tick first.

### 7.4 DIFFUSION, ATTACK, DEFINITION

* **DIFFUSION** (every network with diffusers): each diffuser allpass `difS` gets k = min(26, ⌊S·⌊b/4⌋/8⌋)/32 with the
  slope S = 6, 5, 4 or 3 its name gives.
* **ATTACK** (reverbs): four 4-point rows y (tables `attack_hall` for Concert Hall, `attack_chamber_plate` for the
  others), interpolated at t = 3b, seg = ⌊t/256⌋, f = t mod 256: A = ⌊(256·y[seg] + (y[seg+1] − y[seg])·f + 128)/256⌋.
  Row r gives `Ar`. A 1/32 symbol gets A/32; a 1/8 symbol gets ⌊min(A, 31)/4⌋/8.
* **DEFINITION** (reverbs): e = 63 − ⌊b/4⌋, L = ⌊e/2⌋ limits the in-loop allpasses (7.6). The Concert Hall's
  diffuser allpasses `def` get min(8, ⌊5e/8⌋)/32.

### 7.5 SIZE

SIZE (Chamber, Plate, Hall, Infinite; Inverse Room's DURATION) scales the tank delays `t1`… and moves no coefficient.
Its control value s gives:

* the SIZE factor **f1 = ⌊16·min(β + s, cap)/β⌋** (β, cap = 8, 46 Chamber; 8, 49 Plate; 5, 54 Hall), which also sets the
  DECAY OPT period and the tail rate (section 8);
* every tank delay `t1`, `t2`, … (exact table `size.table[s].delays` of each network);
* the largest predelay / reflection count C(s) (`max_count`).

The tank delays grow roughly in proportion to f1/16: the tank by f1/16, the input diffusers' region by a second factor,
the reflections with the end of the tank. Section 5 gives the values at the smallest, a typical and the largest SIZE.

### 7.6 Reverberation time

The RT-dependent values are computed from a current RT LOW control value l and RT MID control value m (normally the
parameters RT LOW and RT MID; while GATE has stopped the input, the RTL / RTM STOP values; section 8):

* **Mid gains** `g`: ⌊m/8⌋/32 per stage; m ≥ 253 gives exactly 1 (Infinite).
* **RT LOW shelf** `shelf`: with N = mid-gain stages per shelf (Chamber 6, Plate 5, Hall 1) and a = ⌊l/8⌋ − ⌊m/8⌋:
  for N ≥ 2: x = 8·⌊m/8⌋, then N − 2 times x := ⌊x·8·⌊m/8⌋/256⌋, x := max(x, 64),
  q = min(⌊256·(|a| mod 64)/x⌋, 31), and `shelf` = sgn(a)·⌊q/4⌋/8. For N = 1 (Hall): `shelf` = sgn(a)·min(|a|, 31)/32.
  The display texts assume ideal stages; with a 1/8 shelf the low band follows these values, not the displayed RT LOW.
* **In-loop allpasses** `ap5`, `ap3`: k = max(0, min(16, ⌊S·x/4⌋) − n)/32 with x = min(⌊m/8⌋, L), the slope S of the
  name, L from DEFINITION (7.4) and n the DECAY OPT count (section 8).
* **Infinite Chamber.** REV TIME is the RT MID value; RT LOW is fixed at 254. At INF (254) the mid gains are 1 and the
  input coefficient `inp` goes from 20/32 to 0: the tank is frozen.
* **Inverse Room.** LO SLOPE and MD SLOPE take the places of RT LOW and RT MID. MD SLOPE sets the mid gains `g` to
  ⌊b/4⌋/32 (up to 63/32: gains above 1 give the rising envelope above b = 128), `g2` to ⌊5b/64⌋/32 and the output taps
  `otap` to 5/8 for b > 128, else 3/8. The shelf and in-loop allpasses follow the rules above with l = LO SLOPE,
  m = MD SLOPE.

### 7.7 Modulation parameters

CHORUSING sets the walk's period and step size, CHORUS the number of active voices and the mode (section 9). In
Chorus + Rhythm the voices beyond the CHORUS count keep their taps where the program load put them.

### 7.8 Control-only parameters

GATE, DECAY OPT, RTL STOP, RTM STOP and the rhythm RATE change no network value directly; they act through the run-time
control (sections 6.5 and 8).

### 7.9 Parameter maps

For each algorithm, the network values each parameter sets and the law. Parameters not listed (MIX, FX ADJ, SOFT KNOB,
the MASTER parameters, empty cells) set no network value.

##### Chorus + Echo (set A, network 5.1)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | CHORUSING | delay modulation (9) |
| 0.4 | CHORUS | delay modulation (9) |
| 0.5 | HC | `hc_y`: min(31, 32 − ⌊b/8⌋)/32; `hc_x`: ⌊b/8⌋/32 |
| 0.6 | DIFFUSION | `dif6`: slope 6 (7.4); `dif5`: slope 5 (7.4); `dif3`: slope 3 (7.4); 0 = bypass (5.1) |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V DLY MS 1 | `dly1`: delay law (7.3) |
| 2.2 | V DLY MS 2 | `dly2`: delay law (7.3) |
| 2.3 | V DLY MS 3 | `dly3`: delay law (7.3) |
| 2.4 | V DLY MS 4 | `dly4`: delay law (7.3) |
| 2.5 | V DLY MS 5 | `dly5`: delay law (7.3) |
| 2.6 | V DLY MS 6 | `dly6`: delay law (7.3) |
| 3.1 | V FDBK % 1 | `fb1`: feedback law (7.2) |
| 3.2 | V FDBK % 2 | `fb2`: feedback law (7.2) |
| 3.3 | V FDBK % 3 | `fb3`: feedback law (7.2) |
| 3.4 | V FDBK % 4 | `fb4`: feedback law (7.2) |
| 3.5 | V FDBK % 5 | `fb5`: feedback law (7.2) |
| 3.6 | V FDBK % 6 | `fb6`: feedback law (7.2) |
| 4.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 4.2 | V PAN 2 | `panL2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR2`: ⌊b/32⌋/8 |
| 4.3 | V PAN 3 | `panL3`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR3`: ⌊b/32⌋/8 |
| 4.4 | V PAN 4 | `panL4`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR4`: ⌊b/32⌋/8 |
| 4.5 | V PAN 5 | `panL5`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR5`: ⌊b/32⌋/8 |
| 4.6 | V PAN 6 | `panL6`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR6`: ⌊b/32⌋/8 |

##### Chorus + Rhythm (set A, network 5.1)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | CHORUSING | delay modulation (9) |
| 0.4 | CHORUS | delay modulation (9) |
| 0.5 | HC | `hc_y`: min(31, 32 − ⌊b/8⌋)/32; `hc_x`: ⌊b/8⌋/32 |
| 0.6 | DIFFUSION | `dif6`: slope 6 (7.4); `dif5`: slope 5 (7.4); `dif3`: slope 3 (7.4); 0 = bypass (5.1) |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V DLY 1 | `dly1`: delay law (7.3) |
| 2.2 | V DLY 2 | `dly2`: delay law (7.3) |
| 2.3 | V DLY 3 | `dly3`: delay law (7.3) |
| 2.4 | V DLY 4 | `dly4`: delay law (7.3) |
| 2.5 | V DLY 5 | `dly5`: delay law (7.3) |
| 2.6 | V DLY 6 | `dly6`: delay law (7.3) |
| 3.1 | V FDBK % 1 | `fb1`: feedback law (7.2) |
| 3.2 | V FDBK % 2 | `fb2`: feedback law (7.2) |
| 3.3 | V FDBK % 3 | `fb3`: feedback law (7.2) |
| 3.4 | V FDBK % 4 | `fb4`: feedback law (7.2) |
| 3.5 | V FDBK % 5 | `fb5`: feedback law (7.2) |
| 3.6 | V FDBK % 6 | `fb6`: feedback law (7.2) |
| 4.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 4.2 | V PAN 2 | `panL2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR2`: ⌊b/32⌋/8 |
| 4.3 | V PAN 3 | `panL3`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR3`: ⌊b/32⌋/8 |
| 4.4 | V PAN 4 | `panL4`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR4`: ⌊b/32⌋/8 |
| 4.5 | V PAN 5 | `panL5`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR5`: ⌊b/32⌋/8 |
| 4.6 | V PAN 6 | `panL6`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR6`: ⌊b/32⌋/8 |

##### Resonant Chords (set A, network 5.2)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | V3 FDBK - % | `fbm`: −⌊b/8⌋/32 |
| 0.4 | V6 FDBK + % | `fbp`: ⌊b/8⌋/32 |
| 0.5 | HC L | `hcl_y`: min(31, 32 − ⌊b/8⌋)/32; `hcl_x`: ⌊b/8⌋/32 |
| 0.6 | HC R | `hcr_y`: min(31, 32 − ⌊b/8⌋)/32; `hcr_x`: ⌊b/8⌋/32 |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V PITCH 1 | `pit1`: delay law (7.3) |
| 2.2 | V PITCH 2 | `pit2`: delay law (7.3) |
| 2.3 | V PITCH 3 | `pit3`: delay law (7.3) |
| 2.4 | V PITCH 4 | `pit4`: delay law (7.3) |
| 2.5 | V PITCH 5 | `pit5`: delay law (7.3) |
| 2.6 | V PITCH 6 | `pit6`: delay law (7.3) |
| 3.1 | V RESN % 1 | `res1`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.2 | V RESN % 2 | `res2`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.3 | V RESN % 3 | `res3`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.4 | V RESN % 4 | `res4`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.5 | V RESN % 5 | `res5`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.6 | V RESN % 6 | `res6`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 4.1 | V PDL MS 1 | `pdl1`: delay law (7.3) |
| 4.2 | V PDL MS 2 | `pdl2`: delay law (7.3) |
| 4.3 | V PDL MS 3 | `pdl3`: delay law (7.3) |
| 4.4 | V PDL MS 4 | `pdl4`: delay law (7.3) |
| 4.5 | V PDL MS 5 | `pdl5`: delay law (7.3) |
| 4.6 | V PDL MS 6 | `pdl6`: delay law (7.3) |
| 5.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 5.2 | V PAN 2 | `panL2`: min(31, 32 − ⌊b/8⌋)/32; `panR2`: ⌊b/8⌋/32 |
| 5.3 | V PAN 3 | `panL3`: min(31, 32 − ⌊b/8⌋)/32; `panR3`: ⌊b/8⌋/32 |
| 5.4 | V PAN 4 | `panL4`: min(31, 32 − ⌊b/8⌋)/32; `panR4`: ⌊b/8⌋/32 |
| 5.5 | V PAN 5 | `panL5`: min(31, 32 − ⌊b/8⌋)/32; `panR5`: ⌊b/8⌋/32 |
| 5.6 | V PAN 6 | `panL6`: min(31, 32 − ⌊b/8⌋)/32; `panR6`: ⌊b/8⌋/32 |

##### Rhythmic Chords (set A, network 5.2)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | V3 FDBK - % | `fbm`: −⌊b/8⌋/32 |
| 0.4 | V6 FDBK + % | `fbp`: ⌊b/8⌋/32 |
| 0.5 | HC L | `hcl_y`: min(31, 32 − ⌊b/8⌋)/32; `hcl_x`: ⌊b/8⌋/32 |
| 0.6 | HC R | `hcr_y`: min(31, 32 − ⌊b/8⌋)/32; `hcr_x`: ⌊b/8⌋/32 |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V PITCH 1 | `pit1`: delay law (7.3) |
| 2.2 | V PITCH 2 | `pit2`: delay law (7.3) |
| 2.3 | V PITCH 3 | `pit3`: delay law (7.3) |
| 2.4 | V PITCH 4 | `pit4`: delay law (7.3) |
| 2.5 | V PITCH 5 | `pit5`: delay law (7.3) |
| 2.6 | V PITCH 6 | `pit6`: delay law (7.3) |
| 3.1 | V RESN % 1 | `res1`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.2 | V RESN % 2 | `res2`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.3 | V RESN % 3 | `res3`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.4 | V RESN % 4 | `res4`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.5 | V RESN % 5 | `res5`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 3.6 | V RESN % 6 | `res6`: clamp(⌊(b − 128)/4⌋, −31, 31)/32 |
| 4.1 | V DLY 1 | `pdl1`: delay law (7.3) |
| 4.2 | V DLY 2 | `pdl2`: delay law (7.3) |
| 4.3 | V DLY 3 | `pdl3`: delay law (7.3) |
| 4.4 | V DLY 4 | `pdl4`: delay law (7.3) |
| 4.5 | V DLY 5 | `pdl5`: delay law (7.3) |
| 4.6 | V DLY 6 | `pdl6`: delay law (7.3) |
| 5.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 5.2 | V PAN 2 | `panL2`: min(31, 32 − ⌊b/8⌋)/32; `panR2`: ⌊b/8⌋/32 |
| 5.3 | V PAN 3 | `panL3`: min(31, 32 − ⌊b/8⌋)/32; `panR3`: ⌊b/8⌋/32 |
| 5.4 | V PAN 4 | `panL4`: min(31, 32 − ⌊b/8⌋)/32; `panR4`: ⌊b/8⌋/32 |
| 5.5 | V PAN 5 | `panL5`: min(31, 32 − ⌊b/8⌋)/32; `panR5`: ⌊b/8⌋/32 |
| 5.6 | V PAN 6 | `panL6`: min(31, 32 − ⌊b/8⌋)/32; `panR6`: ⌊b/8⌋/32 |

##### Multiband Delay (set A, network 5.3)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | DIFFUSION | `dif5`: slope 5 (7.4); `dif4`: slope 4 (7.4); `dif3`: slope 3 (7.4); 0 = bypass (5.3) |
| 0.4 | V1 FDBK % | `fb1`: ⌊b/8⌋/32 |
| 0.5 | V2 FDBK % | `fb2`: ⌊b/8⌋/32 |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V DLY MS 1 | `dly1`: delay law (7.3) |
| 2.2 | V DLY MS 2 | `dly2`: delay law (7.3) |
| 2.3 | V DLY MS 3 | `dly3`: delay law (7.3) |
| 2.4 | V DLY MS 4 | `dly4`: delay law (7.3) |
| 2.5 | V DLY MS 5 | `dly5`: delay law (7.3) |
| 2.6 | V DLY MS 6 | `dly6`: delay law (7.3) |
| 3.1 | V LC 1 | `vlc1_x`: −⌊b/8⌋/32; `vlc1_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.2 | V LC 2 | `vlc2_x`: −⌊b/8⌋/32; `vlc2_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.3 | V LC 3 | `vlc3_x`: −⌊b/8⌋/32; `vlc3_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.4 | V LC 4 | `vlc4_x`: −⌊b/8⌋/32; `vlc4_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.5 | V LC 5 | `vlc5_x`: −⌊b/8⌋/32; `vlc5_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.6 | V LC 6 | `vlc6_x`: −⌊b/8⌋/32; `vlc6_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.1 | V HC 1 | `vhc1_x`: ⌊b/8⌋/32; `vhc1_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.2 | V HC 2 | `vhc2_x`: ⌊b/8⌋/32; `vhc2_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.3 | V HC 3 | `vhc3_x`: ⌊b/8⌋/32; `vhc3_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.4 | V HC 4 | `vhc4_x`: ⌊b/8⌋/32; `vhc4_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.5 | V HC 5 | `vhc5_x`: ⌊b/8⌋/32; `vhc5_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.6 | V HC 6 | `vhc6_x`: ⌊b/8⌋/32; `vhc6_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 5.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 5.2 | V PAN 2 | `panL2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR2`: ⌊b/32⌋/8 |
| 5.3 | V PAN 3 | `panL3`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR3`: ⌊b/32⌋/8 |
| 5.4 | V PAN 4 | `panL4`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR4`: ⌊b/32⌋/8 |
| 5.5 | V PAN 5 | `panL5`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR5`: ⌊b/32⌋/8 |
| 5.6 | V PAN 6 | `panL6`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR6`: ⌊b/32⌋/8 |

##### Multiband Rhythm (set A, network 5.3)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | DIFFUSION | `dif5`: slope 5 (7.4); `dif4`: slope 4 (7.4); `dif3`: slope 3 (7.4); 0 = bypass (5.3) |
| 0.4 | V1 FDBK % | `fb1`: ⌊b/8⌋/32 |
| 0.5 | V2 FDBK % | `fb2`: ⌊b/8⌋/32 |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V DLY 1 | `dly1`: delay law (7.3) |
| 2.2 | V DLY 2 | `dly2`: delay law (7.3) |
| 2.3 | V DLY 3 | `dly3`: delay law (7.3) |
| 2.4 | V DLY 4 | `dly4`: delay law (7.3) |
| 2.5 | V DLY 5 | `dly5`: delay law (7.3) |
| 2.6 | V DLY 6 | `dly6`: delay law (7.3) |
| 3.1 | V LC 1 | `vlc1_x`: −⌊b/8⌋/32; `vlc1_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.2 | V LC 2 | `vlc2_x`: −⌊b/8⌋/32; `vlc2_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.3 | V LC 3 | `vlc3_x`: −⌊b/8⌋/32; `vlc3_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.4 | V LC 4 | `vlc4_x`: −⌊b/8⌋/32; `vlc4_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.5 | V LC 5 | `vlc5_x`: −⌊b/8⌋/32; `vlc5_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 3.6 | V LC 6 | `vlc6_x`: −⌊b/8⌋/32; `vlc6_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.1 | V HC 1 | `vhc1_x`: ⌊b/8⌋/32; `vhc1_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.2 | V HC 2 | `vhc2_x`: ⌊b/8⌋/32; `vhc2_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.3 | V HC 3 | `vhc3_x`: ⌊b/8⌋/32; `vhc3_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.4 | V HC 4 | `vhc4_x`: ⌊b/8⌋/32; `vhc4_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.5 | V HC 5 | `vhc5_x`: ⌊b/8⌋/32; `vhc5_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.6 | V HC 6 | `vhc6_x`: ⌊b/8⌋/32; `vhc6_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 5.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 5.2 | V PAN 2 | `panL2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR2`: ⌊b/32⌋/8 |
| 5.3 | V PAN 3 | `panL3`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR3`: ⌊b/32⌋/8 |
| 5.4 | V PAN 4 | `panL4`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR4`: ⌊b/32⌋/8 |
| 5.5 | V PAN 5 | `panL5`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR5`: ⌊b/32⌋/8 |
| 5.6 | V PAN 6 | `panL6`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR6`: ⌊b/32⌋/8 |

##### Multiband Delay (set B, network 5.4)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | DIFFUSION | `dif5`: slope 5 (7.4); `dif4`: slope 4 (7.4); `dif3`: slope 3 (7.4); 0 = bypass (5.4) |
| 0.4 | V1 FDBK % | `fb1`: ⌊b/8⌋/32 |
| 0.5 | V2 FDBK % | `fb2`: ⌊b/8⌋/32 |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V DLY MS 1 | `dly1`: delay law (7.3) |
| 2.2 | V DLY MS 2 | `dly2`: delay law (7.3) |
| 2.3 | V DLY MS 3 | `dly3`: delay law (7.3) |
| 2.4 | V DLY MS 4 | `dly4`: delay law (7.3) |
| 2.5 | V DLY MS 5 | `dly5`: delay law (7.3) |
| 2.6 | V DLY MS 6 | `dly6`: delay law (7.3) |
| 3.1 | V LC 1 | `vlc1_y`: (32 − ⌊b/8⌋)/32; `vlc1_x`: −⌊b/8⌋/32 |
| 3.2 | V LC 2 | `vlc2_y`: (32 − ⌊b/8⌋)/32; `vlc2_x`: −⌊b/8⌋/32 |
| 3.3 | V LC 3 | `vlc3_y`: (32 − ⌊b/8⌋)/32; `vlc3_x`: −⌊b/8⌋/32 |
| 3.4 | V LC 4 | `vlc4_y`: (32 − ⌊b/8⌋)/32; `vlc4_x`: −⌊b/32⌋/8 |
| 3.5 | V LC 5 | `vlc5_y`: (32 − ⌊b/8⌋)/32; `vlc5_x`: −⌊b/32⌋/8 |
| 3.6 | V LC 6 | `vlc6_y`: (32 − ⌊b/8⌋)/32; `vlc6_x`: −⌊b/32⌋/8 |
| 4.1 | V HC 1 | `vhc1_y`: min(31, 32 − ⌊b/8⌋)/32; `vhc1_x`: ⌊b/8⌋/32 |
| 4.2 | V HC 2 | `vhc2_y`: min(31, 32 − ⌊b/8⌋)/32; `vhc2_x`: ⌊b/8⌋/32 |
| 4.3 | V HC 3 | `vhc3_y`: min(31, 32 − ⌊b/8⌋)/32; `vhc3_x`: ⌊b/8⌋/32 |
| 4.4 | V HC 4 | `vhc4_x`: ⌊b/8⌋/32; `vhc4_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.5 | V HC 5 | `vhc5_x`: ⌊b/8⌋/32; `vhc5_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.6 | V HC 6 | `vhc6_x`: ⌊b/8⌋/32; `vhc6_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 5.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 5.2 | V PAN 2 | `panL2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR2`: ⌊b/32⌋/8 |
| 5.3 | V PAN 3 | `panL3`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR3`: ⌊b/32⌋/8 |
| 5.4 | V PAN 4 | `panL4`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR4`: ⌊b/32⌋/8 |
| 5.5 | V PAN 5 | `panL5`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR5`: ⌊b/32⌋/8 |
| 5.6 | V PAN 6 | `panL6`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR6`: ⌊b/32⌋/8 |

##### Multiband Rhythm (set B, network 5.4)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | DIFFUSION | `dif5`: slope 5 (7.4); `dif4`: slope 4 (7.4); `dif3`: slope 3 (7.4); 0 = bypass (5.4) |
| 0.4 | V1 FDBK % | `fb1`: ⌊b/8⌋/32 |
| 0.5 | V2 FDBK % | `fb2`: ⌊b/8⌋/32 |
| 1.1 | V LVL 1 | `lvl1`: ⌊b/8⌋/32 |
| 1.2 | V LVL 2 | `lvl2`: ⌊b/8⌋/32 |
| 1.3 | V LVL 3 | `lvl3`: ⌊b/8⌋/32 |
| 1.4 | V LVL 4 | `lvl4`: ⌊b/8⌋/32 |
| 1.5 | V LVL 5 | `lvl5`: ⌊b/8⌋/32 |
| 1.6 | V LVL 6 | `lvl6`: ⌊b/8⌋/32 |
| 2.1 | V DLY 1 | `dly1`: delay law (7.3) |
| 2.2 | V DLY 2 | `dly2`: delay law (7.3) |
| 2.3 | V DLY 3 | `dly3`: delay law (7.3) |
| 2.4 | V DLY 4 | `dly4`: delay law (7.3) |
| 2.5 | V DLY 5 | `dly5`: delay law (7.3) |
| 2.6 | V DLY 6 | `dly6`: delay law (7.3) |
| 3.1 | V LC 1 | `vlc1_y`: (32 − ⌊b/8⌋)/32; `vlc1_x`: −⌊b/8⌋/32 |
| 3.2 | V LC 2 | `vlc2_y`: (32 − ⌊b/8⌋)/32; `vlc2_x`: −⌊b/8⌋/32 |
| 3.3 | V LC 3 | `vlc3_y`: (32 − ⌊b/8⌋)/32; `vlc3_x`: −⌊b/8⌋/32 |
| 3.4 | V LC 4 | `vlc4_y`: (32 − ⌊b/8⌋)/32; `vlc4_x`: −⌊b/32⌋/8 |
| 3.5 | V LC 5 | `vlc5_y`: (32 − ⌊b/8⌋)/32; `vlc5_x`: −⌊b/32⌋/8 |
| 3.6 | V LC 6 | `vlc6_y`: (32 − ⌊b/8⌋)/32; `vlc6_x`: −⌊b/32⌋/8 |
| 4.1 | V HC 1 | `vhc1_y`: min(31, 32 − ⌊b/8⌋)/32; `vhc1_x`: ⌊b/8⌋/32 |
| 4.2 | V HC 2 | `vhc2_y`: min(31, 32 − ⌊b/8⌋)/32; `vhc2_x`: ⌊b/8⌋/32 |
| 4.3 | V HC 3 | `vhc3_y`: min(31, 32 − ⌊b/8⌋)/32; `vhc3_x`: ⌊b/8⌋/32 |
| 4.4 | V HC 4 | `vhc4_x`: ⌊b/8⌋/32; `vhc4_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.5 | V HC 5 | `vhc5_x`: ⌊b/8⌋/32; `vhc5_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 4.6 | V HC 6 | `vhc6_x`: ⌊b/8⌋/32; `vhc6_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 5.1 | V PAN 1 | `panL1`: min(31, 32 − ⌊b/8⌋)/32; `panR1`: ⌊b/8⌋/32 |
| 5.2 | V PAN 2 | `panL2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR2`: ⌊b/32⌋/8 |
| 5.3 | V PAN 3 | `panL3`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR3`: ⌊b/32⌋/8 |
| 5.4 | V PAN 4 | `panL4`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR4`: ⌊b/32⌋/8 |
| 5.5 | V PAN 5 | `panL5`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR5`: ⌊b/32⌋/8 |
| 5.6 | V PAN 6 | `panL6`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8; `panR6`: ⌊b/32⌋/8 |

##### Infinite Chamber (set A, network 5.5)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | SIZE M | tank delays `t1`… and the largest predelay / reflection count (7.5) |
| 0.4 | REV TIME S | `inp`: 20/32 (0 when b ≥ 253: freeze); `g`: ⌊b/8⌋/32 (1 when b ≥ 253); `ap5`: in-loop allpass, slope 5 (7.6); `shelf`: shelf (7.6); `ap3`: in-loop allpass, slope 3 (7.6) |
| 0.5 | PDELAY MS | `pd`: delay law (7.3) |
| 0.6 | HC | `hc_y`: min(31, 32 − ⌊b/8⌋)/32; `hc_x`: ⌊b/8⌋/32 |
| 1.0 | DIFFUSION | `dif6`: slope 6, negative (7.4); `dif5`: slope 5, negative (7.4) |
| 1.1 | ATTACK | `att0`: ⌊min(A0, 31)/4⌋/8 (7.4) |
| 1.2 | DEFINITION | `ap5`: in-loop allpass, slope 5 (7.6); `ap3`: in-loop allpass, slope 3 (7.6) |
| 2.1 | RFL 1 | `rfl1`: ⌊b/32⌋/8 |
| 2.2 | RFL 2 | `rfl2`: −⌊b/32⌋/8 |
| 2.3 | RFL 3 | `rfl3`: ⌊b/32⌋/8 |
| 2.4 | RFL 4 | `rfl4`: ⌊b/32⌋/8 |
| 2.5 | RFL 5 | `rfl5`: −⌊b/32⌋/8 |
| 2.6 | RFL 6 | `rfl6`: ⌊b/32⌋/8 |
| 3.1 | RFL MS 1 | `rd1`: delay law (7.3) |
| 3.2 | RFL MS 2 | `rd2`: delay law (7.3) |
| 3.3 | RFL MS 3 | `rd3`: delay law (7.3) |
| 3.4 | RFL MS 4 | `rd4`: delay law (7.3) |
| 3.5 | RFL MS 5 | `rd5`: delay law (7.3) |
| 3.6 | RFL MS 6 | `rd6`: delay law (7.3) |

##### Rich Chamber (set A, network 5.5)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | SIZE M | tank delays `t1`… and the largest predelay / reflection count (7.5) |
| 0.4 | GATE | run-time control (8) |
| 0.5 | PDELAY MS | `pd`: delay law (7.3) |
| 0.6 | HC | `hc_y`: min(31, 32 − ⌊b/8⌋)/32; `hc_x`: ⌊b/8⌋/32 |
| 0.7 | DECAY OPT | run-time control (8) |
| 1.0 | RT LOW S | `shelf`: shelf (7.6) |
| 1.1 | RT MID S | `g`: ⌊b/8⌋/32; `ap5`: in-loop allpass, slope 5 (7.6); `shelf`: shelf (7.6); `ap3`: in-loop allpass, slope 3 (7.6) |
| 1.2 | XOVER | `xo_x`: ⌊b/8⌋/32; `xo_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 1.3 | RT HC | `rthc_x`: ⌊b/8⌋/32; `rthc_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 1.4 | RTL STOP S | run-time control (8) |
| 1.5 | RTM STOP S | run-time control (8) |
| 2.0 | DIFFUSION | `dif6`: slope 6, negative (7.4); `dif5`: slope 5, negative (7.4) |
| 2.1 | ATTACK | `att0`: ⌊min(A0, 31)/4⌋/8 (7.4) |
| 2.2 | DEFINITION | `ap5`: in-loop allpass, slope 5 (7.6); `ap3`: in-loop allpass, slope 3 (7.6) |
| 3.1 | RFL 1 | `rfl1`: ⌊b/32⌋/8 |
| 3.2 | RFL 2 | `rfl2`: −⌊b/32⌋/8 |
| 3.3 | RFL 3 | `rfl3`: ⌊b/32⌋/8 |
| 3.4 | RFL 4 | `rfl4`: ⌊b/32⌋/8 |
| 3.5 | RFL 5 | `rfl5`: −⌊b/32⌋/8 |
| 3.6 | RFL 6 | `rfl6`: ⌊b/32⌋/8 |
| 4.1 | RFL MS 1 | `rd1`: delay law (7.3) |
| 4.2 | RFL MS 2 | `rd2`: delay law (7.3) |
| 4.3 | RFL MS 3 | `rd3`: delay law (7.3) |
| 4.4 | RFL MS 4 | `rd4`: delay law (7.3) |
| 4.5 | RFL MS 5 | `rd5`: delay law (7.3) |
| 4.6 | RFL MS 6 | `rd6`: delay law (7.3) |

##### Inverse Room (set A, network 5.6)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | DURATION | tank delays `t1`… and the largest predelay / reflection count (7.5) |
| 0.4 | PDELAY MS | `pd`: delay law (7.3) |
| 0.5 | HC | `hc_y`: min(31, 32 − ⌊b/8⌋)/32; `hc_x`: ⌊b/8⌋/32 |
| 1.0 | LO SLOPE % | `shelf`: shelf (7.6) |
| 1.1 | MD SLOPE % | `g2`: ⌊5b/64⌋/32; `ap5`: in-loop allpass, slope 5 (7.6); `g`: ⌊b/4⌋/32 (up to 63/32); `shelf`: shelf (7.6); `ap3`: in-loop allpass, slope 3 (7.6); `otap`: 5/8 if b > 128, else 3/8 |
| 1.2 | XOVER | `xo_x`: ⌊b/8⌋/32; `xo_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 1.3 | RT HC | `rthc_x`: ⌊b/8⌋/32; `rthc_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 2.0 | DIFFUSION | `dif6`: slope 6, negative (7.4); `dif5`: slope 5, negative (7.4) |
| 2.1 | ATTACK | `att0`: ⌊min(A0, 31)/4⌋/8 (7.4) |
| 2.2 | DEFINITION | `ap5`: in-loop allpass, slope 5 (7.6); `ap3`: in-loop allpass, slope 3 (7.6) |
| 3.1 | RFL 1 | `rfl1`: ⌊b/32⌋/8 |
| 3.2 | RFL 2 | `rfl2`: −⌊b/32⌋/8 |
| 3.3 | RFL 3 | `rfl3`: ⌊b/32⌋/8 |
| 3.4 | RFL 4 | `rfl4`: ⌊b/32⌋/8 |
| 3.5 | RFL 5 | `rfl5`: −⌊b/32⌋/8 |
| 3.6 | RFL 6 | `rfl6`: ⌊b/32⌋/8 |
| 4.1 | RFL MS 1 | `rd1`: delay law (7.3) |
| 4.2 | RFL MS 2 | `rd2`: delay law (7.3) |
| 4.3 | RFL MS 3 | `rd3`: delay law (7.3) |
| 4.4 | RFL MS 4 | `rd4`: delay law (7.3) |
| 4.5 | RFL MS 5 | `rd5`: delay law (7.3) |
| 4.6 | RFL MS 6 | `rd6`: delay law (7.3) |

##### Rich Plate (set A, network 5.7)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | SIZE M | tank delays `t1`… and the largest predelay / reflection count (7.5) |
| 0.4 | GATE | run-time control (8) |
| 0.5 | PDELAY MS | `pd`: delay law (7.3) |
| 0.6 | HC | `hc_y`: min(31, 32 − ⌊b/8⌋)/32; `hc_x`: ⌊b/8⌋/32 |
| 0.7 | DECAY OPT | run-time control (8) |
| 1.0 | RT LOW S | `shelf`: shelf (7.6) |
| 1.1 | RT MID S | `g`: ⌊b/8⌋/32; `ap5`: in-loop allpass, slope 5 (7.6); `shelf`: shelf (7.6) |
| 1.2 | XOVER | `xo_x`: ⌊b/8⌋/32; `xo_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 1.3 | RT HC | `rthc_x`: ⌊b/8⌋/32; `rthc_y`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 1.4 | RTL STOP S | run-time control (8) |
| 1.5 | RTM STOP S | run-time control (8) |
| 2.0 | DIFFUSION | `dif6`: slope 6, negative (7.4); `dif5`: slope 5, negative (7.4); `dif4`: slope 4, negative (7.4) |
| 2.1 | ATTACK | `att0`: ⌊min(A0, 31)/4⌋/8 (7.4) |
| 2.2 | DEFINITION | `ap5`: in-loop allpass, slope 5 (7.6) |
| 3.1 | RFL 1 | `rfl1`: −⌊b/32⌋/8 |
| 3.2 | RFL 2 | `rfl2`: −⌊b/32⌋/8 |
| 3.3 | RFL 3 | `rfl3`: ⌊b/32⌋/8 |
| 3.4 | RFL 4 | `rfl4`: −⌊b/32⌋/8 |
| 3.5 | RFL 5 | `rfl5`: −⌊b/32⌋/8 |
| 3.6 | RFL 6 | `rfl6`: ⌊b/32⌋/8 |
| 4.1 | RFL MS 1 | `rd1`: delay law (7.3) |
| 4.2 | RFL MS 2 | `rd2`: delay law (7.3) |
| 4.3 | RFL MS 3 | `rd3`: delay law (7.3) |
| 4.4 | RFL MS 4 | `rd4`: delay law (7.3) |
| 4.5 | RFL MS 5 | `rd5`: delay law (7.3) |
| 4.6 | RFL MS 6 | `rd6`: delay law (7.3) |

##### Concert Hall (set A, network 5.8)

| Pos | Parameter | Network values: law |
|---|---|---|
| 0.3 | SIZE M | tank delays `t1`… and the largest predelay / reflection count (7.5) |
| 0.4 | GATE | run-time control (8) |
| 0.5 | PDELAY MS | `pd`: delay law (7.3) |
| 0.6 | HC | `hc_x`: ⌊b/8⌋/32; `hc_y`: min(31, 32 − ⌊b/8⌋)/32 |
| 0.7 | DECAY OPT | run-time control (8) |
| 0.8 | CHORUSING | delay modulation (9) |
| 1.0 | RT LOW S | `shelf`: shelf (7.6) |
| 1.1 | RT MID S | `ap5`: in-loop allpass, slope 5 (7.6); `g`: ⌊b/8⌋/32; `shelf`: shelf (7.6) |
| 1.2 | XOVER | `xo_y`: min(31, 32 − ⌊b/8⌋)/32; `xo_x`: ⌊b/8⌋/32; `xo_x2`: ⌊b/32⌋/8 |
| 1.3 | RT HC | `rthc_x`: −⌊b/8⌋/32; `rthc_y`: 1 + (32 − ⌊b/8⌋)/32; 1 when b < 8; `rthc_y2`: min(7, ⌊(32 − ⌊b/8⌋)/4⌋)/8 |
| 1.4 | RTL STOP S | run-time control (8) |
| 1.5 | RTM STOP S | run-time control (8) |
| 2.0 | DIFFUSION | `dif6`: slope 6 (7.4); `dif5`: slope 5 (7.4) |
| 2.1 | ATTACK | `att3`: A3/32 (7.4); `att0e`: ⌊min(A0, 31)/4⌋/8 (7.4); `att1e`: ⌊min(A1, 31)/4⌋/8 (7.4); `att1`: −A1/32 (7.4) |
| 2.2 | DEFINITION | `def`: min(8, ⌊5e/8⌋)/32, e = 63 − ⌊b/4⌋; `ap5`: in-loop allpass, slope 5 (7.6) |
| 3.1 | RFL 1 | `rfl1`: ⌊b/32⌋/8 |
| 3.2 | RFL 2 | `rfl2`: ⌊b/32⌋/8 |
| 3.3 | RFL 3 | `rfl3`: ⌊b/32⌋/8 |
| 3.4 | RFL 4 | `rfl4`: ⌊b/32⌋/8 |
| 4.1 | RFL MS 1 | `rd1`: delay law (7.3) |
| 4.2 | RFL MS 2 | `rd2`: delay law (7.3) |
| 4.3 | RFL MS 3 | `rd3`: delay law (7.3) |
| 4.4 | RFL MS 4 | `rd4`: delay law (7.3) |


## 8. Run-time control: level detector, GATE, DECAY OPT

The reverb algorithms (Chamber, Plate, Hall, Infinite) change their reverberation-time values while audio runs, driven
by the input level. Networks with a level detector
have the constants `detector` (e, c and the RT update time, 8.5) in the data file; the Inverse Room has none.

### 8.1 Timing and level input

* A **fast tick** runs every 64 samples (1.89 ms) and a **slow tick** every 609 samples (18 ms, the GATE display
  unit), both counted as in 8.5.
* **Level** λ: an 8-bit reading of the input's peak follower (instant attack, ~44 ms release, linear in amplitude,
  full scale = 254), taken every 32 samples.
* **Log level** of λ: with p = the position of λ's highest set bit (0…7) and q = the next lower bit,

      Λ(λ) = (16·p + 8·q + 135) mod 256,     Λ(0) = 23

  so 16 units = 6 dB, 255 at full scale, 247 at half scale (for λ = 1, q = 1 in the fast tick and 0 in the slow tick).

### 8.2 State

| Variable | Meaning |
|---|---|
| pk | largest λ since the last slow tick (fast tick) |
| prev | λ at the previous fast tick that was not skipped |
| avg | slow average of the log level |
| held | held peak |
| tail | tail model, 16 bits; its high byte ⌊tail/256⌋ is in log-level units |
| hist[0..10] | the tail's high byte at the last 11 slow ticks |
| state | flags: RT MID moving, RT LOW moving, STOP targets |
| hold | hold counter, loaded from the GATE hold time |
| curL, curM | current RT LOW / RT MID control values: every RT-dependent value (7.6) is computed from these |
| cnt8 | counter for step 8 of the slow tick, 8…1 |
| trig, n, P, cnt | DECAY OPT trigger, step count, period, period counter |
| Q | tail rate, recomputed with the RT values (below) |
| frozen | the RT MID parameter's control value is ≥ 253 (set at program load): Infinite Chamber's REV TIME at INF |

The **RT-dependent values** are those of section 7.6: the network values of the RT MID parameter (RT MID, REV TIME or
MD SLOPE) for the control value curM, as far as they are listed in its `rt_symbols` (the mid gains `g`, and `inp`
for the Infinite Chamber), the shelf from curL and curM, and the in-loop allpasses from curM, DEFINITION and n. To
**rewrite** them is to recompute them and put them into the network.

Q = round(2·K[⌊curM/8⌋]·α/256) (round half up), α = min(255, ⌊e·f1/16⌋), with K = the table `rt_rate`
(6, 6, 8, 9, 11, 12, 13, 14, 15, 17, 18, 20, 22, 24, 26, 28, 30, 34, 38, 42, 46, 52, 57, 65, 75, 85, 100, 120, 160, 220,
350, 700), f1 the SIZE factor (7.5) and e = the network's constant (Chamber 14, Plate 17, Hall 16). The tail then falls
at about the reverb's own rate (RT60 ≈ 72 ms · Q). The DECAY OPT period is P0 = min(255, max(1, ⌊f1'·c/256⌋)) with
c = the network's DECAY OPT constant (Chamber 22, Plate 64, Hall 22) and f1' = f1 (4·f1 when frozen). **Every RT recompute** (any change of curL or curM, and
the first one at program load) rewrites the RT-dependent values with the current n and then sets n := 1.

### 8.3 Fast tick (every 1.89 ms)

Skipped when frozen, and when n = 0 and no state flag is set. Otherwise pk := max(pk, λ), and if λ rose since the
previous fast tick that was not skipped, with Λ = Λ(λ):

1. If n > 0 and Λ ≥ ⌊tail/256⌋: tail := 256·(Λ − ⌊tail/256⌋) (the **difference**; the slow tick, 8.4 step 2,
   stores Λ itself), trig := 0, P := P0, and n goes to 0 in steps of 2, rewriting the in-loop allpasses at each step
   (7.6). All steps happen within this tick, so the network sees n = 0 at once.
2. If a state flag is set and Λ ≥ avg and (Λ > 200 or Λ − avg ≥ 39): held := Λ, hold := the GATE hold time, and if
   curM < the RT MID parameter's value: curL, curM := the RT LOW, RT MID values, recompute, clear the state.

### 8.4 Slow tick (every 18 ms)

1. Λ := Λ(max(pk, λ)); pk := 0. Λt := 16 if frozen, else Λ.
2. If Λt ≥ ⌊tail/256⌋: tail := 256·Λt, trig := 0; if n > 0: P := P0 and n goes to 0 in steps of 2 with rewrites,
   all within this tick (as in 8.3).
3. avg := (avg + ⌊Λ/8⌋ − ⌊avg/8⌋) mod 256.
4. **Attack**: Λ ≥ avg and (Λ > 200 or Λ − avg ≥ 39). Then held := Λ; if stopped (STOP flag set): both RTs move back
   to the running values (flags := RT MID moving, RT LOW moving), hold := the GATE hold time.
   **No attack**: held := max(held, Λ); if held − Λ ≥ 5 and GATE is on and not stopped: flags := RT MID moving,
   RT LOW moving, STOP (move to the STOP values after the hold).
5. **DECAY OPT trigger** (DECAY OPT on): with δ = ⌊tail/256⌋ − Λt: if δ ≥ 22 and trig = 0: trig := 1, and if
   ⌊tail/256⌋ − hist[0] ≥ 24 (the tail rose 9 dB within 11 ticks, a transient): P := 15. Then, whether DECAY OPT
   is on or not, hist shifts by one and hist[10] := ⌊tail/256⌋.
6. **RT movement** — repeat while an RT is moving:
   * RT MID (if its flag is set): if stopping and hold > 0: hold := hold − 1 and leave the loop for this tick (go to
     step 7). Target = RTM STOP if stopping, else RT MID. With d = 8·⌊curM/8⌋: if target ≥ d, curM := target
     (arrived); else curM := d − 8, arrived when target ≥ curM. Arrived: clear the RT MID flag.
   * RT LOW (if its flag is set): the same with curL, RTL STOP / RT LOW, clearing the RT LOW flag. The hold test is
     the same too, but it can only take effect when the RT MID flag is already clear: hold counts down once per slow
     tick, whichever RT reaches the test first.
   * Recompute all RT-dependent values (and Q, P0) from curL, curM (8.2).

   The loop runs **within one slow tick** until both RTs have arrived (or the hold leaves it): a fall in steps of 8
   happens in a single tick, with a recompute (and n := 1) after each step. A rise is a single step. Each recompute
   takes time (8.5), so the network sees a fall as a ramp of one step per recompute: B 5.2 GATED PLATE falls from
   RT 240 to 0 in 30 steps over 151 ms. During that time the detector does nothing else.
7. **DECAY OPT counter**: if not frozen and Q ≥ 120: P := 20. cnt := cnt − 1; when it reaches 0: cnt := P; then if
   trig = 0 and n > 0: n := n − 1 and rewrite; if trig = 1 and n < 12 (n < 20 when frozen): n := n + 1 and rewrite.
8. cnt8 := cnt8 − 1; when it reaches 0: cnt8 := 8 and, unless frozen, tail := max(0, tail − ⌊65536/Q⌋),
   held := max(0, held − 3).

A slow tick that leaves step 6 early (hold) still runs steps 7 and 8.

Start values at program load: every variable 0 except cnt = 1, cnt8 = 8, curL, curM = the RT LOW, RT MID control
values; then the first recompute (8.2: it writes the RT-dependent values with n = 0, then sets n := 1), then P := P0.
Editing RT LOW or RT MID sets curL / curM to the new value directly and clears the state. GATE's hold is v + 128 slow
ticks. Three factory programs have the gate on: A 4.6 OPEN GATE (hold 6 ticks = 108 ms), B 4.3 GATED CHAMBE
(4 ticks = 72 ms) and B 5.2 GATED PLATE (2 ticks = 36 ms).

### 8.5 Level input, tick timing and RT update time of a simulation

The detector runs on a peak follower of the 16-bit input samples x16 and calls 8.3 and 8.4 every 1.89 ms and 18 ms.

**RT update time.** Each RT recompute inside a tick (8.3 step 2, 8.4 step 6; not the one at program load) takes the
unit's control a fixed time Tr, and its values reach the network Tw after the recompute starts. Recomputes of one
tick follow each other: the k-th (k = 0, 1, …) arrives at k·Tr + Tw after the tick. The DECAY OPT rewrites take no
time and keep their order: a rewrite after k recomputes arrives at k·Tr. A tick with K recomputes keeps
the control **busy** for K·Tr: no ticks and no delay-modulation updates (9.3) run in that time, and the tick
counting resumes where it stopped.

* **Fast and slow tick on the same sample.** The slow tick runs after the fast tick and continues its sequence: its
  first recompute starts when the fast tick's last one ends, and the busy time is the sum of both.
* **Parameter changes during the busy time** (an edit, a patch source moving, a program change) are applied when the
  busy time ends, after every update of the tick has arrived; a ramp is never interrupted. An RT LOW or RT MID change
  then sets curL / curM directly (8.4).

| Network | Tr (`rt_update_samples`) | Tw (`rt_update_arrive`) | fall of 30 steps |
|---|---|---|---|
| Chamber (and Infinite) | 182 samples (5.38 ms) | 114 samples (3.37 ms) | 162 ms |
| Plate | 171 samples (5.04 ms) | 106 samples (3.13 ms) | 151 ms |
| Hall | 99 samples (2.93 ms) | 46 samples (1.35 ms) | 88 ms |

In detail, counting samples from the program load (k = 1, 2, …):

* per sample: p := max(|x16|/32768, p·e^(−1/(0.044·fs))) (p starts at 0), and λ := min(254, ⌊254·p⌋);
* after sample k, if k is not within the busy time of an earlier tick (k ≤ k0 + K·Tr for a tick after sample k0):
  count the sample; the fast tick when the count is a multiple of 64, then the slow tick when it is a multiple of 609
  (round(0.018·fs)), both with this λ. Samples within the busy time are not counted (the peak follower still runs);
* a rewrite of a tick after sample k0 with arrival a is **due** at k0 + a;
* the network is computed in blocks of 8 samples: before a block that starts after sample j (j = 0, 8, 16, …), every
  rewrite due at or before j is put into the network, in order; the ticks of a block run after it. With no recompute in
  a tick, its values therefore take effect at the start of the next block of 8.


## 9. Delay modulation (Chorus voices, Hall chorusing)

The Chorus network (six voices) and the Hall network (two taps, one per tank half) move interpolated delay taps in a
**bounded random walk** in steps of 1/32 sample. No other network modulates.

### 9.1 Interpolated tap

Modulator j reads two taps of one line, A = sL[mAj] and B = sL[mBj], at delays one sample apart, and forms (exact,
as listed in 5.1 and 5.8)

    D = B − 1/2·A − 1/2·A          y = A + kj·D,   kj = mj ∈ {0, 1/32, …, 31/32}

and **y = B exactly when mj = 32/32** (the listings: `interp`). The delays are mAj = c0 + a and mBj = c0 + b with positions a, b (0…255) and an
offset c0: Chorus c0 = 0 (positions 0…255, up to 7.5 ms); Hall: positions 0…127 for the first tap and 128…255 for the
second, c0 = 0 and −127 (delays 1…128; the SIZE table's `modulator_offset` holds them for every SIZE).

### 9.2 Walk

State per modulator j: the positions a, b (start values in the data file: a = 1, b = 2 for Chorus and the Hall's first
tap, 129, 130 for its second) and a fraction state S (an 8-bit value: bit 7 is the half, the low 6 bits the fraction;
start values 6…11 for the Chorus voices, 0 for the Hall). Every change of S sets mj: f = S mod 64; mj = 32/32 if
f = 32, else (f mod 32)/32, and the tap delays mAj, mBj follow a and b (9.1). Until the first change mj keeps its load
value (0) and the delays theirs (c0 + a, c0 + b with the start positions). Global state: a direction byte r, three
update counters (64-update block, direction-byte block, step period), the step period B, the step size or scale D,
the number of active modulators n and the mode (T = constant speed, S = slower near the ends).

* CHORUS control value c (Chorus network): n = c mod 16 voices (0…6), mode T if c ≥ 128, else mode S. Modulators
  j = 1…n are active; the others never move and keep their load values. With n = 0 (CHORUS OFF) no step is ever made.
  The Hall has n = 2 and mode S.

* CHORUSING control value c: v = ⌊c/8⌋. v = 0: off (the walk and its counters stand still). v = 1…15: one step every B = 17 − v updates, D = 1.
  v = 16…31: B = 1, D = v − 15.
* Every 64 updates: each modulator's step size Lj = D (mode T: Chorus with CHORUS mode T) or
  1 + ⌊(64 + ⌊min(b, 255 − b)/2⌋)·2D/256⌋ (mode S; always for the Hall), for the active modulators. Every 4th time
  (256 updates) the next direction byte r is taken from a fixed 2 048-byte sequence (data file:
  `modulation.sequence_A`, set B `sequence_B`), cyclically (index mod 2 048). The sequence is that of the program's
  set: a set B program uses `sequence_B` also when its algorithm is listed under set A. At program load r =
  sequence[16], and the 64-update counter and the direction-byte counter are 1, so the very first update computes
  the step sizes and takes sequence[17]. Each update first counts the 64-update block (and, at its end, the
  direction-byte block), then the step period.
* The **step-period counter** is an 8-bit counter that counts down once per update and, when it reaches 0, makes a
  step and reloads B. It starts at **0**, so the first update wraps it to 255 and the **first step comes at update
  256**; after that a step comes every B updates.
* Every B updates, for each active modulator j = 1…n (n = the CHORUS voice count; Hall 2): rotate a copy of r right
  by one bit per modulator and take its lowest bit as the direction, **1 = up, 0 = down** (so modulator j uses bit j
of r). Then, with
  L = Lj (repeat from the start after a leapfrog):
  * **up**, S ≥ 128: S' = S + L; if S' ≤ 160: S := S' and done; else leapfrog A to b + 1.
  * **up**, S = 0: leapfrog B to b + 2.  **up**, 0 < S < 128: S := max(S − L, 0) and done.
  * **down**, S ≥ 128: S' = (S − L) mod 256; if S' ≥ 128: S := S' and done; else leapfrog B to b − 2.
  * **down**, S < 128: S' = S + L; if S' ≤ 32: S := S' and done; else leapfrog A to b − 1.
  * **Leapfrog** of a tap to position p: if p is outside 0…255, or (Hall) p is in the other half than b, the modulator
    stays and bit j of r flips (it turns back until the next direction byte). Otherwise the tap moves to p (B also sets
    b := p), S := S with bit 7 flipped, and the step repeats with the same direction from the new state.

Effective speed: a modulator moves 1/m sample per step, m = ⌊32/L⌋ (not L/32: a step that crosses an end applies L
again after the leapfrog). The set B sequence differs; the law does not.

### 9.3 Real-time rate

The walk advances once per **update**; the updates run back to back, and their duration depends on the work done. In
units of 1/96 sample (96 units = one sample period):

| Update | Duration |
|---|---|
| CHORUSING off | 665 + 746 |
| no step due | 665 + 844 |
| a step | 665 + 262 (+ 5·(D − 1) in mode S) + Σ over the active modulators (592.5, + 504 if it leapfrogged) |

Of every sample period, the share f = 0.131 (Chorus) or 0.144 (Hall) is not available to the updates. A modulator then
moves at (1 − f)·96·fs / (m·T_cycle) samples per second, with T_cycle the duration of B updates. The updates stop
while the level detector is busy with an RT update (8.5).

**Scheduling.** A time budget u (starting at 0, in units of 1/96 sample) is kept. After each block of 8 samples
8·96·(1 − f) is added for the samples outside the detector's busy time and the per-tap ramps (7.3), and while u > 0 one update runs and its
duration from the table above is subtracted. Tap and coefficient changes then apply from the next block. CHORUSING and CHORUS
changes set B, D, n and the mode at once; the positions, S and the counters keep running.

## 10. Input, output and mix

### 10.1 Input

The single input passes a gain stage (front-panel INPUT level; +4 dBu or −20 dBV mode), a 15.25 kHz 9th-order
anti-alias low-pass (−6 dB passband loss, compensated by the following gain) and is sampled with 16 bits: gain,
low-pass at 15.25 kHz, hard clip at 16-bit full scale (nothing clips earlier unless the input gain is turned below
about −30 dB), and sampling at fs. The level detector (8.1) reads a peak follower of the same signal. Polarity: not
inverted.

### 10.2 Output

Each output sample is reconstructed flat to within +0.3 dB up to 15 kHz and filtered by a 15.25 kHz 9th-order
low-pass. The right channel is 0.24 sample later than the left. Polarity: not inverted.

The wet signal is **AC-coupled** after the low-pass (47 µF into the 20 kΩ input of the wet gain stage): a first-order
high-pass at 0.17 Hz on each wet output, y = x − x[1] + (1 − 2π·0.17/fs)·y[1] (the dry path has one at 0.23 Hz). It
removes the DC offset that the arithmetic leaves in decayed tails (up to a few tens of LSB). The network outputs of the
data and of section 4 are before it.

### 10.3 MIX and FX ADJ

The wet signal (both outputs of the network) and the dry signal (the input, before its anti-alias filter) each pass a
gain set by a code 0…255: 0 dB at code 0, −0.39 dB per code, off at 255. They are then summed. With m = the effective
MIX (0…100 %) and L = the effective FX ADJ index (0…102, displayed L − 90 dB):

    wet code = min(255, MIX[m] + ⌊(102 − L)·10/4⌋)
    dry code = min(255, MIX[100 − m] + 30)

In a simulation, with the network outputs yL, yR and the input sample x16 of the same sample (all on the 16-bit
scale): out = g_wet·y + g_dry·x16 per channel, g = 10^(−0.39·code/20), and g = 0 at code 255. The effective MIX is
limited to 0…100, and L = FX ADJ (in dB) + 90, limited to 0…102.

MIX[ ] is a 101-entry constant-power table (data file `tables.mix`; 255 at 0 %, 8 at 50 %, 0 at 100 %). FX ADJ +12 dB
(L = 102) adds nothing; nominal 0 dB puts the wet gain 30 codes (11.7 dB) down, like the dry one. The analog gain from
the network output to the unit's output is the same for wet and dry within 0.2 dB, so at 0 dB FX ADJ a unity program
and the dry path have equal level. During a program change the wet gain is off and the dry one at code 30. The gains
change smoothly: each gain passes a first-order low-pass with a time constant of 6 ms; the codes themselves change in
one step.

### 10.4 Running a program

A whole program combines the sections above:

1. **Network values.** From the stored values and patches, the effective values (6.2), then the network values: start
   from the algorithm's `base` values, and for each parameter in the order of `params` take the entry of its
   effective value: its `set` values overwrite the network values and its `control` values are collected (with the
   algorithm's `fixed_control`). Then apply the laws that combine parameters: the rhythm delays (6.5, with the RATE
   tempo), and for networks with SIZE the SIZE table row of the `size` control value: its tank delays, the predelay
   and reflection taps from their counts (7.3, limited to C), and the RT-dependent values
   from the `rt_low` and `rt_mid` control values with n = 0 (7.6). The modulated coefficients start at `k0`, the
   modulated taps at c0 + a0 and c0 + b0 (9.1). The result equals `network_values` for every factory program
   (section 12).
2. **Network.** With DIFFUSION control value 0, the network's `bypass` replacements apply (Chorus, Multiband). Every
   stored value starts at 0 (5.9).
3. **Run-time control.** The delay modulation (9) for networks with `modulators`; the level detector (8) for networks
   with `detector`; the patches (6.2) whenever a source changes (during the detector's busy time: when it ends, 8.5).
   Delay changes while running follow 7.3 (per-tap ramp, group ramp, program load or direct switch).
4. **Per sample:** the network (4), then the mix (10.3). Every 8 samples: first the
   detector rewrites that are due (8.5), then the network and mix of the 8 samples, then the detector ticks (8.5),
   then the modulation updates (9.3) for the samples of the block outside the detector's busy time.

# Part III — Algorithms and programs

Part III describes what each network does, at the level of signal blocks, and lists the factory programs. The
listings of section 5 are the exact form; the parameter maps of 7.9 tie every parameter to its values.

## 11. The algorithms

Eleven algorithms run on eight networks (set B has ten algorithms: no Inverse Room). "Rhythm" variants share their
network with the plain variant; only the voice-delay law changes (6.5). "Voice" means one of the six delayed copies of
the effect algorithms. Signal names refer to the listings of section 5.

### 11.1 Chorus + Echo, Chorus + Rhythm (network 5.1)

* Input: two three-stage allpass diffusers (DIFFUSION, slopes 6, 5, 3), one per echo line; DIFFUSION 0 bypasses
  them.
* Two echo lines with feedback: each line's input is its diffuser output plus V FDBK times the outputs of its three
  voices (±7/8), through the HC one-pole, so the high-cut acts on the echo input and on every repeat.
* Six voices. Each voice reads its echo line at V DLY MS (up to 14 649 samples = 432 ms) into a short chorus line whose
  interpolated tap the delay modulation moves (CHORUSING, CHORUS: number of voices and mode).
* Output: per voice level (V LVL) and pan (V PAN: left 1 − p, right p) into the two output sums.
* Chorus + Rhythm sets the voice delays in 24ths of a beat at RATE BPM (6.5).

### 11.2 Resonant Chords, Rhythmic Chords (network 5.2)

* The input (×17/32) is written into a predelay line together with two feedback taps of that line: V3 FDBK −
  at voice 3's predelay and V6 FDBK + at voice 6's, so the line itself recirculates.
* Six resonators, each a comb filter on its own line: the predelayed input plus the resonator's output from V PITCH
  samples ago (loop length 12…976 samples; PCH MST transposes all) times V RESN (±31/32; negative = odd harmonics),
  then a one-pole low-pass in the loop with HC L (voices 1–3) or HC R (voices 4–6).
* Each resonator takes its own predelay: V PDL MS in Resonant Chords (0–773 ms as displayed), V DLY in 24ths of a beat in
  Rhythmic Chords (7.3).
* Output: per voice level and pan into the two sums.

### 11.3 Multiband Delay, Multiband Rhythm (networks 5.3, 5.4)

* Input sum with two feedback paths (from voices 1 and 2), a three-stage diffuser (DIFFUSION; 0 bypasses it), one
  delay line; six voice taps (V DLY MS up to 30 326 samples = 896 ms; Multiband Rhythm: 24ths of a beat).
* Per voice a high-cut (V HC) and a low-cut (V LC) section, then level and pan.
* **Set B** uses its own network (5.4): the same voices and parameters, a different arrangement of the voice filters,
  and the V LC control law b = 8·(v + 15) (set A: 8 coarse settings). Everything else, including the display texts, is
  the same.

### 11.4 Rich Chamber, Infinite Chamber (network 5.5)

* A figure-of-eight tank of two halves, each fed by its own input diffuser (DIFFUSION, slopes 6, 5). Each half has
  three in-loop allpasses (from RT MID and DEFINITION, lowered by DECAY OPT), one RT HC one-pole and three mid gains;
  half A also has the crossover low-pass and the RT LOW shelf.
* Output: 15 fixed taps of the tank per side (±1/2, 3/8), three early reflections per side (RFL, RFL MS) from the input
  line, the ATTACK tap, and an HC one-pole per side.
* SIZE scales the tank delays (7.5). GATE / RT STOP and DECAY OPT act at run time (8).
* **Infinite Chamber** is the same network with REV TIME as the only reverberation time (RT LOW fixed at 254). REV TIME
  = INF sets the mid gains to 1 and closes the input (`inp` = 0): the tank is frozen, and so is the detector (8).

### 11.5 Inverse Room (network 5.6, set A)

The Chamber's structure with the loop opened (5.6): two chains without recirculation. DURATION takes SIZE's place,
and LO SLOPE / MD SLOPE take RT LOW / RT MID's. MD SLOPE above 0 sets the stage gains above 1 (up to 63/32) and the
output taps to 5/8, which gives the rising ("inverse") envelope; the laws are in 7.6.

### 11.6 Rich Plate (network 5.7)

A single loop through both halves with three-stage input diffusers per side (DIFFUSION, slopes 6, 5, 4), five mid
gains and five in-loop allpasses (slope 5) per round trip, two RT HC one-poles, the crossover and the RT LOW shelf. The
left input enters at the start of half A, the right one in the middle of the loop. Outputs as in the Chamber.

### 11.7 Concert Hall (network 5.8)

* An input high-cut, then two cross-coupled tank halves. Each half has DIFFUSION allpasses, nested allpass chains
  (DEFINITION: k = min(8, ⌊5e/8⌋)/32, and in-loop allpasses) with one modulated delay tap (CHORUSING, a random walk over
  128 samples), one mid gain with its own crossover and RT LOW shelf (so RT LOW follows the display closely), and the RT
  HC stage (a fixed gain in the left half, a one-pole in the right).
* The predelayed input enters both halves at the mid-gain sums. Output: ATTACK taps and two early reflections per side
  from the input high-cut line (RFL, RFL MS).

## 12. Factory programs

Set A has 42 factory programs (rows 0–6 of the front-panel matrix), set B had 43 (rows 0–6). The data file holds all
42 set A programs and the 42 set B programs that differ from them: B 0.6 SWARBLE is A 0.2 TUNNEL without TUNNEL's three
mod-wheel patches, so only TUNNEL is included. The set B Multiband programs (1.0–1.8, 6.2) run the set B Multiband
network. Rows 7–9 of both sets are utilities and are left out.

For each program the data file gives the stored values, the patches and every network value at rest (section 13). The
key settings below are the unit's display texts of the effective values at rest (patches with all sources at rest,
SOFT KNOB at its stored position).

| Set | Pos | Name | Algorithm | Key settings (as displayed) | Patches (source→parameter, scale s') |
|---|---|---|---|---|---|
| A | 0.0 | MOD WOBBLE | Chorus + Echo | Chorusing 69; Chorus VC T; Diffusion 17; HC 15.0 KHZ | MOD WHEEL→2.0 +128, MOD WHEEL→3.0 -19, MOD WHEEL→2.2 +56, MOD WHEEL→2.5 +62, MOD WHEEL→1.2 -24, MOD WHEEL→1.5 -29 |
| A | 0.1 | ECHORUS | Chorus + Echo | Chorusing 65; Chorus VC T; Diffusion 19; HC 15.0 KHZ | LAST NOTE→4.4 +128, LAST NOTE→4.4 +83, LAST NOTE→4.5 -128, LAST NOTE→4.5 -83, MOD WHEEL→2.4 -121, MOD WHEEL→2.5 -119, MOD WHEEL→3.4 -18, MOD WHEEL→3.5 -20 |
| A | 0.2 | TUNNEL | Chorus + Echo | Chorusing 58; Chorus VC S; Diffusion 70; HC 15.0 KHZ | MOD WHEEL→2.1 +70, MOD WHEEL→2.2 +125, MOD WHEEL→2.6 +61 |
| A | 0.3 | POWER PHLANG | Chorus + Echo | Chorusing 71; Chorus VC T; Diffusion 0; HC 15.0 KHZ | – |
| A | 0.4 | 6 VOICE COMB | Chorus + Echo | Chorusing 62; Chorus VC T; Diffusion 46; HC 15.0 KHZ | – |
| A | 0.5 | FOR STRINGS | Chorus + Echo | Chorusing 53; Chorus VC T; Diffusion 99; HC 8.19 KHZ | AFTER TCH→0.3 +17 |
| A | 0.6 | UNLIN | Chorus + Echo | Chorusing 66; Chorus VC T; Diffusion 92; HC 15.0 KHZ | LAST NOTE→2.0 +79, LAST NOTE→3.0 +31 |
| A | 0.7 | FLANGE O ECH | Chorus + Echo | Chorusing 67; Chorus VC S; Diffusion 0; HC 15.0 KHZ | MOD WHEEL→2.1 +112, MOD WHEEL→3.1 +47, MOD WHEEL→3.6 -20 |
| A | 0.8 | AUTO CHORUS | Chorus + Rhythm | Rate 64; Chorusing 68; Chorus VC S; Diffusion 0 | MIDI CLK→2.0 +128 |
| A | 0.9 | BONANZA  BPM | Chorus + Rhythm | Rate 114; Chorusing 67; Chorus VC S; Diffusion 0 | – |
| A | 1.0 | PING PONG MO | Multiband Delay | Diffusion 33; V1 Fdbk 23; V2 Fdbk 0 | MOD WHEEL→2.0 -128 |
| A | 1.1 | SIX ACROSS | Multiband Delay | Diffusion 20; V1 Fdbk 0; V2 Fdbk 0 | SUSTAIN→0.4 +30 |
| A | 1.2 | FILTER 4 EFX | Multiband Delay | Diffusion 48; V1 Fdbk 0; V2 Fdbk 0 | MOD WHEEL→4.0 +7, MOD WHEEL→2.0 +128, MOD WHEEL→2.0 +32, PORT SW→0.4 +20 |
| A | 1.3 | MIDI MOD PAN | Multiband Rhythm | Rate 64; Diffusion 0; V1 Fdbk 0; V2 Fdbk 0 | MOD WHEEL→5.1 +101, MOD WHEEL→5.2 -101, MIDI CLK→2.0 +128 |
| A | 1.4 | AUTO SINGLE | Multiband Rhythm | Rate 64; Diffusion 0; V1 Fdbk 0; V2 Fdbk 0 | MIDI CLK→2.0 +128 |
| A | 1.5 | AUTO TUMBLE | Multiband Rhythm | Rate 64; Diffusion 0; V1 Fdbk 35; V2 Fdbk 0 | MIDI CLK→2.0 +128 |
| A | 1.6 | AUTO BOUNCE | Multiband Rhythm | Rate 64; Diffusion 0; V1 Fdbk 0; V2 Fdbk 19 | SOFT KNOB→5.1 -101, SOFT KNOB→5.2 +101, MOD WHEEL→5.1 -101, MOD WHEEL→5.2 +100, MIDI CLK→2.0 +128 |
| A | 2.0 | MAJOR MOD | Resonant Chords | V Pitch 1 D!1; V Pitch 2 D!1; V Pitch 3 D!1; HC L 10.0 KHZ | PCH WHEEL→2.3 +3, PCH WHEEL→2.2 +4, PCH WHEEL→2.5 -4, MOD WHEEL→4.0 -101, LAST NOTE→2.0 +128 |
| A | 2.1 | MAJOR MODAL | Resonant Chords | V Pitch 1 D!1; V Pitch 2 D!1; V Pitch 3 D!1; HC L 10.0 KHZ | LAST NOTE→2.0 +128 |
| A | 2.2 | AUTO SUSPENS | Rhythmic Chords | Rate 64; V Pitch 1 D!1; V Pitch 2 D!1; V Pitch 3 D!1 | MIDI CLK→2.0 +128, MIDI CLK→4.0 +128, MIDI CLK→0.5 -70, MIDI CLK→0.6 -78 |
| A | 3.0 | SUSTAIN HALL | Concert Hall | Size 36.2; RT Low 3.4 S; RT Mid 2.2 S; XOVER 350 HZ; RT HC 6.27 KHZ; Pdelay 24; Chorusing 51; Gate OFF | SOFT KNOB→1.0 +32, SOFT KNOB→1.1 +32, SUSTAIN→1.0 +10, SUSTAIN→1.2 +6, SUSTAIN→0.8 +10 |
| A | 3.1 | CONCERT WAVE | Concert Hall | Size 38.3; RT Low 4.7 S; RT Mid .45 S; XOVER 15.0 KHZ; RT HC 6.27 KHZ; Pdelay 24; Chorusing 64; Gate OFF | AFTER TCH→0.8 +25, LAST VEL→3.0 +56 |
| A | 3.2 | SOFT SPACE | Concert Hall | Size 34.7; RT Low .99 S; RT Mid .81 S; XOVER 3.73 KHZ; RT HC 2.81 KHZ; Pdelay 18; Chorusing 49; Gate OFF | SOFT KNOB→1.0 +128, SOFT KNOB→1.1 +64, MOD WHEEL→0.8 +38 |
| A | 3.3 | 5 OCLOCK HAL | Concert Hall | Size 28.4; RT Low 14 S; RT Mid .45 S; XOVER 530 HZ; RT HC 7.47 KHZ; Pdelay 34; Chorusing 50; Gate OFF | – |
| A | 3.4 | SOFT ECHOES | Concert Hall | Size 36.2; RT Low 1.6 S; RT Mid .72 S; XOVER 1.55 KHZ; RT HC 2.53 KHZ; Pdelay 152; Chorusing 58; Gate OFF | SOFT KNOB→1.0 +64, SOFT KNOB→1.1 +64, SOFT KNOB→2.0 -128, SOFT KNOB→2.2 +128, SOFT KNOB→2.1 +64, SOFT KNOB→1.3 +8 |
| A | 4.0 | SOFT AMBIENC | Rich Chamber | Size 20.5; RT Low 1.6 S; RT Mid .36 S; XOVER 4.85 KHZ; RT HC 6.27 KHZ; Pdelay 4; Gate OFF; Decay Opt ON | SOFT KNOB→1.0 +18, SOFT KNOB→1.1 +40, SOFT KNOB→1.3 +32 |
| A | 4.1 | LOCKER ROOM | Rich Chamber | Size 17.0; RT Low .84 S; RT Mid 1.2 S; XOVER 530 HZ; RT HC 2.81 KHZ; Pdelay 26; Gate OFF; Decay Opt ON | – |
| A | 4.2 | SNARE CHAMBE | Rich Chamber | Size 24.8; RT Low .42 S; RT Mid .25 S; XOVER 10.0 KHZ; RT HC 8.19 KHZ; Pdelay 0; Gate OFF; Decay Opt ON | – |
| A | 4.3 | KICK  CHAMBE | Rich Chamber | Size 17.0; RT Low 20 S; RT Mid 1.1 S; XOVER 350 HZ; RT HC 920 HZ; Pdelay 0; Gate OFF; Decay Opt ON | – |
| A | 4.4 | MEDIUM ROOM | Rich Chamber | Size 14.9; RT Low 1.8 S; RT Mid 1.2 S; XOVER 3.10 KHZ; RT HC 4.45 KHZ; Pdelay 0; Gate OFF; Decay Opt ON | LAST VEL→3.0 +25 |
| A | 4.5 | VOX CHAMBER | Rich Chamber | Size 29.8; RT Low .31 S; RT Mid 20 S; XOVER 15.0 KHZ; RT HC 4.45 KHZ; Pdelay 10; Gate OFF; Decay Opt ON | SOFT KNOB→1.0 +6, SOFT KNOB→1.1 +58, SOFT KNOB→1.2 +74 |
| A | 4.6 | OPEN GATE | Rich Chamber | Size 17.7; RT Low 1.1 S; RT Mid 1.1 S; XOVER 1.33 KHZ; RT HC 8.19 KHZ; Pdelay 44; Gate 108 MS; Decay Opt ON | – |
| A | 4.7 | INFINITE A T | Infinite Chamber | Size 29.8; Rev Time INF; Pdelay 0; HC 8.19 KHZ | AFTER TCH→0.4 -1, MOD WHEEL→0.4 -10 |
| A | 5.0 | VOX PLATE | Rich Plate | Size 26.2; RT Low 2.9 S; RT Mid 2.3 S; XOVER 1.55 KHZ; RT HC 8.19 KHZ; Pdelay 6; Gate OFF; Decay Opt ON | SOFT KNOB→1.0 +128, SOFT KNOB→1.1 +128 |
| A | 5.1 | PD PLATE | Rich Plate | Size 19.1; RT Low 4.4 S; RT Mid 1.2 S; XOVER 4.85 KHZ; RT HC 8.19 KHZ; Pdelay 60; Gate OFF; Decay Opt ON | SOFT KNOB→1.0 +64, SOFT KNOB→1.1 +128 |
| A | 5.2 | BRASS PLATE | Rich Plate | Size 31.9; RT Low 2.3 S; RT Mid 1.1 S; XOVER 3.41 KHZ; RT HC 7.47 KHZ; Pdelay 16; Gate OFF; Decay Opt ON | SOFT KNOB→1.0 +128, SOFT KNOB→1.1 +128 |
| A | 6.0 | INVERSE ROOM | Inverse Room | Duration 385; Lo Slope -36; Md Slope + 8; Pdelay 0; HC 15.0 KHZ | – |
| A | 6.1 | INVERSE 2 | Inverse Room | Duration 347; Lo Slope + 0; Md Slope + 8; Pdelay 0; HC 15.0 KHZ | – |
| A | 6.2 | HEAD BANGER | Inverse Room | Duration 562; Lo Slope +28; Md Slope -28; Pdelay 0; HC 15.0 KHZ | MIDI CLK→0.3 -49, SOFT KNOB→1.0 -22, SOFT KNOB→1.1 +37, MOD WHEEL→1.0 -5, MOD WHEEL→1.1 +9 |
| A | 6.3 | SKI JUMP | Inverse Room | Duration 536; Lo Slope +36; Md Slope +52; Pdelay 52; HC 15.0 KHZ | MOD WHEEL→1.0 -10, MOD WHEEL→1.1 -17 |
| A | 6.4 | ATOM SMASHER | Inverse Room | Duration 233; Lo Slope +44; Md Slope +40; Pdelay 32; HC 15.0 KHZ | – |
| A | 6.5 | GATED ROOM | Inverse Room | Duration 233; Lo Slope + 0; Md Slope - 4; Pdelay 0; HC 15.0 KHZ | SOFT KNOB→1.0 +40, SOFT KNOB→1.1 +64, SOFT KNOB→1.2 -41 |
| B | 0.0 | CHORUS | Chorus + Echo | Chorusing 64; Chorus VC T; Diffusion 0; HC 15.0 KHZ | – |
| B | 0.1 | CHORUS ECHOE | Chorus + Echo | Chorusing 50; Chorus VC T; Diffusion 71; HC 15.0 KHZ | – |
| B | 0.2 | ECHO FLANGE | Chorus + Echo | Chorusing 47; Chorus VC S; Diffusion 28; HC 15.0 KHZ | – |
| B | 0.3 | STEREO FLANG | Chorus + Echo | Chorusing 62; Chorus VC T; Diffusion 0; HC 15.0 KHZ | – |
| B | 0.4 | DOUBLE SLAP | Chorus + Echo | Chorusing 55; Chorus VC S; Diffusion 30; HC 15.0 KHZ | – |
| B | 0.5 | SPIM ECHOES | Chorus + Echo | Chorusing 58; Chorus VC S; Diffusion 30; HC 15.0 KHZ | – |
| B | 0.7 | PSYCHO ECHOE | Chorus + Echo | Chorusing 62; Chorus VC T; Diffusion 90; HC 15.0 KHZ | – |
| B | 0.8 | ECHOES BPM | Chorus + Rhythm | Rate 100; Chorusing 45; Chorus VC S; Diffusion 0 | – |
| B | 0.9 | CORSENECO BP | Chorus + Rhythm | Rate 100; Chorusing 60; Chorus VC S; Diffusion 0 | – |
| B | 1.0 | SINGLE DELAY | Multiband Delay (set B network) | Diffusion 0; V1 Fdbk 29; V2 Fdbk 26 | – |
| B | 1.1 | DOUBLE DELAY | Multiband Delay (set B network) | Diffusion 0; V1 Fdbk 20; V2 Fdbk 20 | – |
| B | 1.2 | PAN DELAYS | Multiband Delay (set B network) | Diffusion 0; V1 Fdbk 31; V2 Fdbk 0 | – |
| B | 1.3 | CIRCULAR DLY | Multiband Delay (set B network) | Diffusion 42; V1 Fdbk 30; V2 Fdbk 0 | – |
| B | 1.4 | 4 VOICE DELA | Multiband Delay (set B network) | Diffusion 10; V1 Fdbk 33; V2 Fdbk 0 | – |
| B | 1.5 | QUATRO DELAY | Multiband Delay (set B network) | Diffusion 15; V1 Fdbk 22; V2 Fdbk 7 | – |
| B | 1.6 | FILTERED DLY | Multiband Delay (set B network) | Diffusion 20; V1 Fdbk 0; V2 Fdbk 0 | – |
| B | 1.7 | SHUFFLE BPM | Multiband Rhythm (set B network) | Rate 100; Diffusion 0; V1 Fdbk 0; V2 Fdbk 30 | – |
| B | 1.8 | BOUNCING BPM | Multiband Rhythm (set B network) | Rate 100; Diffusion 0; V1 Fdbk 45; V2 Fdbk 15 | – |
| B | 2.0 | MAJOR CHORD | Resonant Chords | V Pitch 1 F 1; V Pitch 2 C 2; V Pitch 3 F 2; HC L 10.0 KHZ | – |
| B | 2.1 | MINOR CHORD | Resonant Chords | V Pitch 1 F 1; V Pitch 2 C 2; V Pitch 3 F 2; HC L 10.0 KHZ | – |
| B | 2.2 | 7TH SHARP 11 | Resonant Chords | V Pitch 1 A 1; V Pitch 2 A 2; V Pitch 3 D!3; HC L 10.0 KHZ | – |
| B | 2.3 | DOM 13TH | Resonant Chords | V Pitch 1 F 1; V Pitch 2 F 2; V Pitch 3 E!3; HC L 10.0 KHZ | PCH WHEEL→2.2 -4, PCH WHEEL→2.4 +2, PCH WHEEL→2.5 +4 |
| B | 2.4 | RYM IN C BPM | Rhythmic Chords | Rate 100; V Pitch 1 C 2; V Pitch 2 E 2; V Pitch 3 G 2 | – |
| B | 2.5 | RYM C MIN BP | Rhythmic Chords | Rate 100; V Pitch 1 C 2; V Pitch 2 E!2; V Pitch 3 D!1 | – |
| B | 3.0 | CONCERT HALL | Concert Hall | Size 36.2; RT Low 6.8 S; RT Mid 2.7 S; XOVER 350 HZ; RT HC 6.27 KHZ; Pdelay 24; Chorusing 50; Gate OFF | – |
| B | 3.1 | LONG HALL | Concert Hall | Size 38.3; RT Low 9.0 S; RT Mid 5.1 S; XOVER 2.02 KHZ; RT HC 7.47 KHZ; Pdelay 16; Chorusing 50; Gate OFF | – |
| B | 3.2 | GYMNASIUM | Concert Hall | Size 22.7; RT Low 5.1 S; RT Mid 14 S; XOVER 1.12 KHZ; RT HC 3.73 KHZ; Pdelay 84; Chorusing 56; Gate OFF | – |
| B | 4.0 | RICH CHAMBER | Rich Chamber | Size 17.7; RT Low 6.2 S; RT Mid 1.8 S; XOVER 1.55 KHZ; RT HC 5.75 KHZ; Pdelay 0; Gate OFF; Decay Opt ON | – |
| B | 4.1 | SMALL ROOM | Rich Chamber | Size 12.0; RT Low 1.3 S; RT Mid 1.1 S; XOVER 1.12 KHZ; RT HC 7.47 KHZ; Pdelay 12; Gate OFF; Decay Opt ON | – |
| B | 4.2 | TILED ROOM | Rich Chamber | Size 8.5; RT Low 1.8 S; RT Mid 1.5 S; XOVER 3.41 KHZ; RT HC 9.02 KHZ; Pdelay 4; Gate OFF; Decay Opt ON | – |
| B | 4.3 | GATED CHAMBE | Rich Chamber | Size 14.2; RT Low 6.2 S; RT Mid 6.2 S; XOVER 1.55 KHZ; RT HC 12.3 KHZ; Pdelay 26; Gate 72 MS; Decay Opt ON | – |
| B | 4.4 | INF REVERB | Infinite Chamber | Size 32.6; Rev Time 29 S; Pdelay 0; HC 11.1 KHZ | – |
| B | 5.0 | RICH PLATE | Rich Plate | Size 17.7; RT Low 5.3 S; RT Mid 3.3 S; XOVER 720 HZ; RT HC 11.1 KHZ; Pdelay 0; Gate OFF; Decay Opt ON | – |
| B | 5.1 | SMALL PLATE | Rich Plate | Size 13.4; RT Low 5.3 S; RT Mid 4.4 S; XOVER 720 HZ; RT HC 12.3 KHZ; Pdelay 8; Gate OFF; Decay Opt ON | – |
| B | 5.2 | GATED PLATE | Rich Plate | Size 9.9; RT Low 15 S; RT Mid 15 S; XOVER 530 HZ; RT HC 15.0 KHZ; Pdelay 24; Gate 36 MS; Decay Opt ON | – |
| B | 6.0 | MIDI ECHO BP | Chorus + Rhythm | Rate 100; Chorusing 55; Chorus VC T; Diffusion 12 | PORT SW→2.1 -3, PORT SW→3.1 -28, MOD WHEEL→3.6 -45, MOD WHEEL→3.2 -30, DATA ENTR→0.0 -91 |
| B | 6.1 | CASCADE BPM | Rhythmic Chords | Rate 100; V Pitch 1 C 2; V Pitch 2 C 3; V Pitch 3 C 3 | DATA ENTR→0.0 -91, MOD WHEEL→0.4 +50, PCH WHEEL→2.5 +4, PCH WHEEL→2.6 +4, PORT SW→4.1 +16, PORT SW→4.2 +8, PORT SW→4.4 -8, PORT SW→4.5 -16 |
| B | 6.2 | FILTR PAN BP | Multiband Rhythm (set B network) | Rate 150; Diffusion 0; V1 Fdbk 0; V2 Fdbk 0 | DATA ENTR→0.0 -91, MOD WHEEL→0.4 +50, MOD WHEEL→2.1 +4, LAST NOTE→5.1 -128, LAST NOTE→5.2 +76, LAST NOTE→5.3 +25, LAST NOTE→5.4 -26, LAST NOTE→5.5 -76, LAST NOTE→5.6 +128 |
| B | 6.3 | MIDI CHRD BP | Rhythmic Chords | Rate 100; V Pitch 1 D!1; V Pitch 2 D!1; V Pitch 3 D!1 | DATA ENTR→0.0 -91, MOD WHEEL→0.4 +43, PORT SW→4.1 -8, PORT SW→4.2 +4, PORT SW→4.3 -10, PORT SW→4.5 +24, PORT SW→4.6 -12, PCH WHEEL→2.5 +4, PCH WHEEL→2.3 +4 |
| B | 6.4 | MIDI SLAP BP | Chorus + Rhythm | Rate 100; Chorusing 55; Chorus VC S; Diffusion 0 | DATA ENTR→0.0 -91, PORT SW→2.1 +15, PORT SW→2.2 +7, PORT SW→2.4 +11, PORT SW→2.5 +15, MOD WHEEL→3.3 +50, MOD WHEEL→3.6 -50 |
| B | 6.5 | MIDI CT HALL | Concert Hall | Size 34.7; RT Low 2.5 S; RT Mid 2.7 S; XOVER 720 HZ; RT HC 6.27 KHZ; Pdelay 16; Chorusing 41; Gate OFF | MOD WHEEL→1.0 +15, MOD WHEEL→1.1 +15, MOD WHEEL→0.0 +86, AFTER TCH→0.8 +25 |
| B | 6.6 | MIDI INF RVB | Infinite Chamber | Size 31.2; Rev Time 1.4 S; Pdelay 0; HC 11.1 KHZ | DATA ENTR→0.0 -91, MOD WHEEL→0.4 +16, SOSTENUTO→0.4 +32 |

# Part IV — Data and sample rate

## 13. Data file and tools

### 13.1 `reverb-programs.json`

| Key | Content |
|---|---|
| `meta` | fs, the two program sets, date |
| `networks` | per network (`chorus`, `chords`, `multiband`, `multiband_b`, `chamber`, `inverse`, `plate`, `hall`): `signals` (in order; each with `name`, `start`, `terms` [`c`, `of`], `stored`, and the special rules `interp`, `start_at_unity`), `outputs`, `coefficients` (symbol → `resolution` 8 or 32), `delays` (delay symbols), `bypass` (DIFFUSION 0 replacements), `rt` (shelf stages, in-loop slopes), `detector` (e, c, `rt_update_samples` Tr, `rt_update_arrive` Tw: 8.5), `delay_ramp` (7.3: per delay symbol the ramped products `signal`, `term` (index in `terms` or "start"), `c`, `resolution`, `unity`; `group` with `first`, `pass` and the counters' `rest`), `size` (β as `b`, cap and `table` per SIZE value s: `f1`, `delays`, `tap_offset`, `max_count`, `modulator_offset`), `modulators` (symbols, start positions a0, b0, start state S0, start coefficient k0, offset), `modulation` (walk constants). Encoding: 13.2 |
| `algorithms` | per algorithm and set: `network`, `base_program` (the factory program the value tables were made on), `base` (all network values of that program), `fixed_control` (control values no parameter sets), `params` |
| `algorithms[*].params` | `pos`, `name`, `lo`, `hi`, `role` (rt_low, rt_mid, size, gate, … for the laws of sections 7–9), `values`: for every v from `lo` to `hi`: `text` (display), `b` and / or `count` (control value), `control` (the control values it sets, by name: 13.2), `set` (the network values it sets, when only this parameter changes); `taps` (the delay symbols a count sets), `delay_law`, `rhythm`, `rt_symbols` (13.2) |
| `programs` | per factory program: `set`, `pos`, `name`, `algorithm` (+ `algorithm_set`), `values` (stored value per position), `patches` (`source`, `dest`, `scale`), `network_values` (every coefficient and delay at rest; the modulated coefficients and taps at their start values, 9.2), `control` (the control values at rest, 13.2) |
| `modulation` | the 2 048-byte direction sequences `sequence_A`, `sequence_B` (hex) and the start index |
| `tables` | `percent`, `mix`, `tempo_samples_per_beat`, `rt_rate`, `attack_hall`, `attack_chamber_plate`, `delay_ramp` (7.3: `step` 2, `switch` 3, `part_gap` 220 samples) |

Network values are integers: coefficients in units of their resolution (1/8 or 1/32), delays in samples. A program at
rest is fully defined by its network and `network_values` (plus the modulator start values of `networks[*].modulators`).
Parameter positions are strings "row.column"; program `values` map them to stored values.

### 13.2 Encoding of the networks and control values

**Signals.** `signals` lists the signals in computing order. Each has a `name` (`s1`, …), a `start`, a list `terms`
and optionally `stored: true`; `outputs` names the L and R output signals.

* An **operand** is `"x"` (the input), a signal name (this sample's value of that signal), or a tap object
  `{"tap": "sj", "d": d}` with d an integer or a delay symbol, and optionally `"add": a`, an integer added to the
  delay (used by the bypass replacements: s1[dly1 − 1]).
* `start` is an operand or a product `{"c": c, "of": operand}`; each term is a product `{"c": c, "of": operand}` that
  is added (3.3). A coefficient c is a symbol of `coefficients`, a negated symbol `"-sym"`, or a fixed value written
  as a fraction or integer (`"31/32"`, `"-1/2"`, `"1"`).
* `interp: {"k", "A", "B"}`: the signal is the tap B when the coefficient k equals 32 units (9.1).
* `start_at_unity: "sj"`: when the start coefficient is ≥ 1, the start is the signal sj plus (coefficient − 1)
  times the start operand (5.4).
* `bypass: {"when": "diffusion == 0", "replace": [{"from": tap, "to": tap}, …]}`: with DIFFUSION control value 0,
  every operand equal to `from` reads `to` instead (7.3).
* `rt`: `stages` (mid-gain stages per shelf, N of 7.6) and `inloop` (in-loop allpass symbol → slope S).
* `size.table[s]`: `f1`, `delays` (tank delay symbol → samples), `tap_offset` (predelay / reflection symbol → the
  offset added to its count), `max_count` (C, 7.3), `modulator_offset` (Hall: c0 per modulator).
* `modulators[j]`: the symbols `k`, `A`, `B` of the coefficient and the two taps; `a0`, `b0`, `S0`, `k0`; `offset`
  (Chorus: c0). `modulation`: `direction_mode` 0 (the direction bits are taken by rotating r, 9.2), `blocks` 4 (64-update
  blocks per direction byte), `keep_half` (true for the Hall: a tap may not leave its half).

**Control values** (`control` of a parameter value, `fixed_control` of an algorithm), by name: `size` (s of 7.5),
`rt_low`, `rt_mid`, `rtl_stop`, `rtm_stop` (RT control values), `gate` (on / off), `gate_hold` (the hold time in slow
ticks), `decay_opt` (on / off), `definition`, `diffusion`, `chorusing`, `chorus` (section 9.2). A value not set by any
parameter is 0 (off).

**Parameter fields.** `role` names the parameters the combined laws of 10.4 need (`rt_low`, `rt_mid`, `size`,
`rate`, …). `taps` lists the delay symbols that the parameter's `count` sets (7.3); `delay_law` gives its offset
(`offset`), the high-byte limit h (`max_high`) or the 128-sample unit of the Chords predelays (`unit`). `rhythm`
marks a voice delay in 24ths of a beat (6.5): `unit` (1, or 128 for Rhythmic Chords), `offset`, `max_high`, and for
Chorus + Rhythm `max_beats_count` (14 847). `rt_symbols` lists the RT MID parameter's network values that the
run-time control rewrites (8.2).

### 13.3 Tools (Python 3.6+, standard library only)

| File | Use |
|---|---|
| `reverb_build.py` | `Builder`: network values from stored values, patches and source values (6–7, 10.4 step 1); `rt_update` for the run-time RT values. `python reverb_build.py check` rebuilds all 84 factory programs (network and control values) |

The network, the delay modulation, the level detector and the mix are specified in sections 3–10 and the data file
only; the package contains no simulator.

## 14. Sample rate

All delays, coefficients and the delay modulation are defined at fs = 33 854.17 Hz. At another rate the networks run
at 33 854.17 Hz and the input and output are resampled (the analog stages band-limit to 15.25 kHz).
