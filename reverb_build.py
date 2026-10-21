"""Network values from parameter values: the laws of sections 6 and 7 of algorithms-and-programs.md.
Python 3.6+, standard library only.

    python reverb_build.py check          rebuild every factory program and compare with its stored network values
                                          and control values

    import reverb_build as RB
    data = RB.load_data()
    b = RB.Builder(data)
    values, control, effective = b.build('Rich Chamber', 'A', stored)      # stored: {pos: v}

`values` holds every coefficient (in units of its resolution, 1/8 or 1/32) and every delay (samples) of the
algorithm's network; `control` the control values the run-time control needs (section 8).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def load_data(path=None):
    with open(path or os.path.join(HERE, 'reverb-programs.json'), encoding='utf-8') as f:
        return json.load(f)

# ------------------------------------------------------------------------------------------------ laws (7.6)
def shelf(stages, bl, bm):
    """RT LOW shelf coefficient: eighths when stages >= 2 (Chamber 6, Plate 5), 32nds when stages = 1 (Hall)."""
    a = (bl >> 3) - (bm >> 3); mag = abs(a)
    if stages >= 2:
        c = (bm >> 3) << 3; x = c
        for _ in range(stages - 2): x = (x * c) >> 8
        x = max(x, 64)
        v = min(((mag & 63) << 8) // x, 31) >> 2
    else:
        v = min(mag, 31)
    return -v if a < 0 else v

def inloop(slope, bm, bdef, n=0):
    """In-loop allpass coefficient (32nds) from RT MID, DEFINITION and the DECAY OPT count n."""
    L = (63 - (bdef >> 2)) >> 1
    x = min(bm >> 3, L)
    return max(0, min(16, (slope * x) // 4) - n)

def size_factor(net, s):
    """f1, the SIZE factor of section 5 (16 = smallest)."""
    k = net['size']
    return (16 * min(k['b'] + s, k['cap'])) // k['b']

# ------------------------------------------------------------------------------------------------ builder
class Builder:
    def __init__(self, data):
        self.data = data
        self.algs = {(a['name'], a['set']): a for a in data['algorithms']}
        for a in data['algorithms']:
            for p in a['params']:
                p['_by_v'] = {x['v']: x for x in p['values']}

    def effective_values(self, alg, stored, patches=(), sources=None):
        """Stored values + patches (section 6.2) with the given source values (default: all at rest)."""
        sources = {int(k): v for k, v in (sources or {}).items()}
        bypos = {p['pos']: p for p in alg['params']}
        if 69 not in sources:                                     # SOFT KNOB: its own stored value
            sk = bypos.get('0.2')
            sources[69] = (stored[sk['pos']] - sk['lo']) if sk else 0
        acc = {}
        for pt in patches:
            x = sources.get(pt['source'], 0)
            if not x: continue
            sp = pt['scale'] + 1 if pt['scale'] >= 0 else pt['scale']
            r, c = divmod(pt['dest'], 10)
            dest = bypos.get('%d.%d' % (r, c))
            if dest is None: continue
            targets = [dest]
            if c == 0 and '%d.1' % r in bypos and dest['name'].endswith('MST'):
                targets += [bypos['%d.%d' % (r, j)] for j in range(1, 10) if '%d.%d' % (r, j) in bypos]
            for t in targets:
                acc[t['pos']] = acc.get(t['pos'], 0) + sp * x
        eff = {}
        for p in alg['params']:
            v = stored[p['pos']] + (64 + acc.get(p['pos'], 0)) // 128
            eff[p['pos']] = max(p['lo'], min(p['hi'], v))
        return eff

    def build(self, name, set_, stored, patches=(), sources=None):
        alg = self.algs[(name, set_)]
        net = self.data['networks'][alg['network']]
        eff = self.effective_values(alg, stored, patches, sources)
        vals = dict(alg['base'])
        ctrl = dict(alg['fixed_control'])
        counts = {}
        for p in alg['params']:
            ent = p['_by_v'].get(eff[p['pos']])
            if ent is None: continue
            ctrl.update(ent.get('control', {}))
            vals.update(ent.get('set', {}))
            if 'count' in ent: counts[p['pos']] = ent['count']
        for m in net.get('modulators', []):                       # modulated taps start at their load values
            vals[m['k']] = m['k0']
        self._rhythm(alg, eff, vals)
        if 'size' in net:
            s = ctrl['size']
            row = net['size']['table'][s]
            vals.update(row['delays'])
            for m, c0 in zip(net.get('modulators', []), row.get('modulator_offset', [])):
                vals[m['A']] = c0 + m['a0']; vals[m['B']] = c0 + m['b0']
            for p in alg['params']:
                if 'taps' not in p or p['pos'] not in counts: continue
                cnt = min(counts[p['pos']], row['max_count'])          # 7.3: the largest count inside the memory
                for t in p['taps']:
                    vals[t] = cnt + row['tap_offset'][t]
            self._rt(alg, net, vals, ctrl, ctrl['rt_low'], ctrl['rt_mid'], 0)
        else:
            for m in net.get('modulators', []):
                vals[m['A']] = m['offset'] + m['a0']; vals[m['B']] = m['offset'] + m['b0']
        return vals, ctrl, eff

    def _rt(self, alg, net, vals, ctrl, bl, bm, n):
        rt = net.get('rt')
        if not rt: return
        vals['shelf'] = shelf(rt['stages'], bl, bm)
        for sym, slope in rt['inloop'].items():
            vals[sym] = inloop(slope, bm, ctrl.get('definition', 0), n)

    def rt_update(self, name, set_, vals, ctrl, curL, curM, n):
        """The RT-dependent values (section 8) for the current RT LOW / RT MID control values and DECAY OPT count."""
        alg = self.algs[(name, set_)]
        net = self.data['networks'][alg['network']]
        rtp = next((p for p in alg['params'] if p.get('role') == 'rt_mid'), None)
        if rtp is not None:
            ent = next((x for x in rtp['values'] if x.get('control', {}).get('rt_mid') == curM), None)
            if ent is not None:
                for sym, v in ent.get('set', {}).items():
                    if sym in rtp.get('rt_symbols', ()): vals[sym] = v
        self._rt(alg, net, vals, ctrl, curL, curM, n)
        return vals

    def _rhythm(self, alg, eff, vals):
        """Rhythm voice delays in 24ths of a beat at the RATE tempo (section 6.5)."""
        rate = next((p for p in alg['params'] if p.get('role') == 'rate'), None)
        if rate is None: return
        T = self.data['tables']['tempo_samples_per_beat']
        Tb = T[min(127, max(0, eff[rate['pos']] - rate['lo']))] // 24
        for p in alg['params']:
            r = p.get('rhythm')
            if r is None: continue
            n = eff[p['pos']] - p['lo']
            if r.get('max_beats_count'):                          # Chorus + Rhythm: count <= 14 847
                n = min(n, r['max_beats_count'] // Tb) if Tb else n
            if r['unit'] == 128:                                  # Rhythmic Chords: steps of 128 samples
                cnt = 128 * min(196, 2 * ((n * Tb + 128) // 256))
            else:
                cnt = n * Tb
                if r.get('max_high') is not None and cnt >> 8 > r['max_high']: cnt = 257 * r['max_high']
            for t in p['taps']:
                vals[t] = cnt + r['offset']

# ------------------------------------------------------------------------------------------------ self-check
def check(data):
    b = Builder(data)
    bad = 0
    for fp in data['programs']:
        vals, ctrl, eff = b.build(fp['algorithm'], fp['algorithm_set'], fp['values'], fp['patches'])
        ref = fp['network_values']
        diff = sorted(k for k in ref if vals.get(k) != ref[k])
        cref = fp['control']                                     # the control values the run-time control uses
        diff += sorted('control ' + k for k in set(cref) | set(ctrl) if ctrl.get(k) != cref.get(k))
        if diff:
            bad += 1
            print('%s %s %-13s: %s' % (fp['set'], fp['pos'], fp['name'], ', '.join(
                ('%s %s/%s' % (k, ctrl.get(k[8:]), cref.get(k[8:]))) if k.startswith('control ') else
                ('%s %s/%s' % (k, vals.get(k), ref[k])) for k in diff[:8])))
    print('%d programs rebuilt, %d differ' % (len(data['programs']), bad))
    return bad

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        sys.exit(1 if check(load_data()) else 0)
    print(__doc__)
