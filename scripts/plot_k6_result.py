"""
Visualize k6 test results.
Reads k6_summary.json written by handleSummary() in each k6 test script.

Usage (via Docker):
    docker compose run --rm -e K6_TEST=nginx plotter
    docker compose run --rm -e K6_TEST=backend plotter
    docker compose run --rm -e K6_TEST=breakpoint plotter
    docker compose run --rm -e K6_TEST=oversell plotter
"""

import os
import sys
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

SUMMARY_JSON = Path(__file__).resolve().parent.parent / 'k6_summary.json'
TEST_TYPE    = os.environ.get('K6_TEST', 'nginx')

# ── Metric extraction ─────────────────────────────────────────────────

def load_metrics():
    if not SUMMARY_JSON.exists():
        sys.exit(f'Error: {SUMMARY_JSON.name} not found — run k6 first.')
    print(f'Reading metrics from {SUMMARY_JSON.name}')
    data = json.loads(SUMMARY_JSON.read_text())
    m    = data['metrics']

    total_reqs   = int(m['http_reqs']['values']['count'])
    total_rps    = m['http_reqs']['values']['rate']
    duration_sec = round(total_reqs / total_rps)
    vus_max      = int(m['vus']['values']['max'])

    success  = int(m['purchase_success_rate']['values'].get('passes', 0))
    sold_out = int(m.get('purchase_sold_out_rate', {}).get('values', {}).get('passes', 0))
    rate_lim = int(m.get('rate_limited_responses', {}).get('values', {}).get('count', 0))

    # HTTP-level failures (non-2xx / timeout)
    http_fail_rate = m['http_req_failed']['values']['rate']
    http_failed    = round(total_reqs * http_fail_rate)

    dur_key = 'http_req_duration{expected_response:true}'
    dur = m.get(dur_key, m['http_req_duration'])['values']

    # Teardown checks (oversell test) — k6 returns a list of check objects
    checks_raw = data.get('root_group', {}).get('checks', [])
    if isinstance(checks_raw, list):
        checks = {c['name']: c for c in checks_raw}
    else:
        checks = checks_raw

    return {
        'duration_sec':     duration_sec,
        'vus_max':          vus_max,
        'total_reqs':       total_reqs,
        'total_rps':        total_rps,
        'success':          success,
        'sold_out':         sold_out,
        'rate_limited':     rate_lim,
        'rate_limited_rps': m.get('rate_limited_responses', {}).get('values', {}).get('rate', 0),
        'http_failed':      http_failed,
        'avg_ms':           round(dur['avg'], 2),
        'p90_ms':           round(dur['p(90)'], 2),
        'p95_ms':           round(dur['p(95)'], 2),
        'checks':           checks,
    }


# ── Shared helpers ────────────────────────────────────────────────────

def base_fig():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5),
                             gridspec_kw={'width_ratios': [1, 1.4]})
    fig.patch.set_facecolor('white')
    return fig, axes


def stats_panel(ax, rows):
    ax.axis('off')
    ax.set_facecolor('white')
    y = 0.93
    for label, value, color in rows:
        ax.text(0.04, y, label, transform=ax.transAxes,
                color='#555555', fontsize=10, va='top')
        ax.text(0.55, y, value, transform=ax.transAxes,
                color=color, fontsize=10, va='top', fontweight='bold')
        y -= 0.11
    for yi in [0.98, 0.02]:
        ax.axhline(yi, color='#dddddd', linewidth=0.8)


def save(fig, name):
    output = Path(__file__).resolve().parent.parent / name
    fig.tight_layout()
    fig.savefig(output, dpi=150, bbox_inches='tight', facecolor='white')
    print(f'Saved: {output.name}')


# ── nginx ─────────────────────────────────────────────────────────────

def plot_nginx(d):
    fig, (ax_pie, ax_line) = base_fig()

    # Pie
    _, _, autotexts = ax_pie.pie(
        [d['rate_limited'], d['success']],
        labels=[
            f"Rate Limited (429)\n{d['rate_limited']:,}  ({d['rate_limited']/d['total_reqs']*100:.1f}%)",
            f"Successful\n{d['success']:,}  ({d['success']/d['total_reqs']*100:.2f}%)",
        ],
        colors=['#e74c3c', '#2ecc71'],
        explode=(0.03, 0.08),
        autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2},
        textprops={'fontsize': 10},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight('bold')
    ax_pie.set_title('Request Distribution', fontsize=13, fontweight='bold', pad=15)

    # Two lines
    t = np.linspace(0, d['duration_sec'], 600)
    ax_line.plot(t, np.full_like(t, d['rate_limited_rps']),
                 color='#e74c3c', linewidth=2,
                 label=f"Rate Limited (429)  (~{d['rate_limited_rps']:.0f} req/s)")
    ax_line.plot(t, np.full_like(t, d['success'] / d['duration_sec']),
                 color='#2ecc71', linewidth=2,
                 label=f"Successful  (~{d['success'] / d['duration_sec']:.1f} req/s)")
    ax_line.set_xlim(0, d['duration_sec'])
    ax_line.set_ylim(0, d['rate_limited_rps'] * 1.2)
    ax_line.set_xlabel('Time (s)', fontsize=10)
    ax_line.set_ylabel('Requests / s', fontsize=10)
    ax_line.set_title('Request Rate over Time', fontsize=13, fontweight='bold')
    ax_line.legend(fontsize=9, loc='center right')
    ax_line.grid(True, linestyle='--', alpha=0.4)
    ax_line.set_facecolor('#f9f9f9')

    footer = (
        f"{d['vus_max']} VUs  |  {d['duration_sec']}s  |  "
        f"Total: {d['total_reqs']:,} reqs  |  "
        f"Backend latency — avg: {d['avg_ms']} ms  p90: {d['p90_ms']} ms  p95: {d['p95_ms']} ms"
    )
    fig.text(0.5, -0.02, footer, ha='center', fontsize=9, color='#555555')
    fig.suptitle('k6 Load Test  —  Nginx Rate Limiting  (limit_req rate=10r/s  burst=20)',
                 fontsize=14, fontweight='bold', y=1.03)
    save(fig, 'k6_nginx_result.png')


# ── backend ───────────────────────────────────────────────────────────

def plot_backend(d):
    fig, (ax_pie, ax_stats) = base_fig()
    other = d['total_reqs'] - d['success'] - d['sold_out']

    # Pie
    sizes  = [d['success'], d['sold_out'], max(other, 0)]
    labels = [
        f"Success\n{d['success']:,}",
        f"Sold Out\n{d['sold_out']:,}",
        f"HTTP Failed\n{max(other,0):,}",
    ]
    colors = ['#2ecc71', '#f39c12', '#e74c3c']
    # Drop slices that are 0
    non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
    sizes, labels, colors = zip(*non_zero)

    _, _, autotexts = ax_pie.pie(
        sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2},
        textprops={'fontsize': 10},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight('bold')
    ax_pie.set_title('Purchase Outcomes', fontsize=13, fontweight='bold', pad=15)

    # Stats
    ax_stats.set_title('Key Metrics', fontsize=13, fontweight='bold', pad=10)
    rows = [
        ('Peak VUs',           f"{d['vus_max']:,}",                    '#2c3e50'),
        ('Duration',           f"{d['duration_sec']} s",               '#2c3e50'),
        ('Total Requests',     f"{d['total_reqs']:,}",                  '#2c3e50'),
        ('Throughput',         f"{d['total_rps']:.0f} req/s",          '#2c3e50'),
        ('Successful',         f"{d['success']:,}",                     '#27ae60'),
        ('Sold Out',           f"{d['sold_out']:,}",                    '#e67e22'),
        ('HTTP Failed',        f"{max(other,0):,}",                     '#c0392b'),
        ('Latency avg',        f"{d['avg_ms']} ms",                     '#2c3e50'),
        ('Latency P90',        f"{d['p90_ms']} ms",                     '#2c3e50'),
        ('Latency P95',        f"{d['p95_ms']} ms",                     '#2c3e50'),
    ]
    stats_panel(ax_stats, rows)

    fig.suptitle('k6 Load Test  —  Backend Burst Capacity',
                 fontsize=14, fontweight='bold', y=1.03)
    save(fig, 'k6_backend_result.png')


# ── breakpoint ────────────────────────────────────────────────────────

def plot_breakpoint(d):
    fig, (ax_pie, ax_stats) = base_fig()
    passed   = d['success']
    failed   = d['http_failed']
    sold_out = d['sold_out']

    sizes  = [passed, sold_out, failed]
    labels = [f"Success\n{passed:,}", f"Sold Out\n{sold_out:,}", f"HTTP Failed\n{failed:,}"]
    colors = ['#2ecc71', '#f39c12', '#e74c3c']
    non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
    sizes, labels, colors = zip(*non_zero)

    _, _, autotexts = ax_pie.pie(
        sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2},
        textprops={'fontsize': 10},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight('bold')
    ax_pie.set_title('Request Outcomes at Breakpoint', fontsize=13, fontweight='bold', pad=15)

    fail_rate = failed / d['total_reqs'] * 100 if d['total_reqs'] else 0
    ax_stats.set_title('Key Metrics', fontsize=13, fontweight='bold', pad=10)
    rows = [
        ('Peak VUs',        f"{d['vus_max']:,}",               '#2c3e50'),
        ('Duration',        f"{d['duration_sec']} s",           '#2c3e50'),
        ('Total Requests',  f"{d['total_reqs']:,}",             '#2c3e50'),
        ('Throughput',      f"{d['total_rps']:.0f} req/s",     '#2c3e50'),
        ('Success',         f"{passed:,}",                      '#27ae60'),
        ('Sold Out',        f"{sold_out:,}",                    '#e67e22'),
        ('HTTP Failed',     f"{failed:,}  ({fail_rate:.1f}%)",  '#c0392b'),
        ('Latency avg',     f"{d['avg_ms']} ms",                '#2c3e50'),
        ('Latency P90',     f"{d['p90_ms']} ms",                '#2c3e50'),
        ('Latency P95',     f"{d['p95_ms']} ms",                '#2c3e50'),
    ]
    stats_panel(ax_stats, rows)

    fig.suptitle('k6 Load Test  —  Backend Ramp to Breakpoint',
                 fontsize=14, fontweight='bold', y=1.03)
    save(fig, 'k6_breakpoint_result.png')


# ── oversell ──────────────────────────────────────────────────────────

def plot_oversell(d):
    fig, (ax_pie, ax_checks) = base_fig()

    # Pie: success (tickets bought) vs sold_out
    _, _, autotexts = ax_pie.pie(
        [d['success'], d['sold_out']],
        labels=[
            f"Purchased\n{d['success']:,}",
            f"Sold Out\n{d['sold_out']:,}",
        ],
        colors=['#2ecc71', '#95a5a6'],
        autopct='%1.1f%%', startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2},
        textprops={'fontsize': 10},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight('bold')
    ax_pie.set_title('Purchase Outcomes', fontsize=13, fontweight='bold', pad=15)

    # Check results panel
    ax_checks.axis('off')
    ax_checks.set_facecolor('white')
    ax_checks.set_title('Oversell Prevention Checks', fontsize=13, fontweight='bold', pad=10)

    check_map = {
        'no oversell (remaining_stock >= 0)':   'No Oversell  (stock >= 0)',
        'no under-sell (remaining_stock == 0)': 'Full Sell-Through  (stock == 0)',
    }
    y = 0.82
    for k6_name, display in check_map.items():
        info = d['checks'].get(k6_name, {})
        passed = info.get('passes', 0)
        failed = info.get('fails', 0)
        ok     = failed == 0 and passed > 0
        icon   = '✓' if ok else '✗'
        color  = '#27ae60' if ok else '#c0392b'
        ax_checks.text(0.08, y, icon, transform=ax_checks.transAxes,
                       color=color, fontsize=28, va='center', fontweight='bold')
        ax_checks.text(0.22, y, display, transform=ax_checks.transAxes,
                       color='#2c3e50', fontsize=11, va='center')
        y -= 0.28

    # Summary numbers
    ax_checks.text(0.08, 0.22,
                   f"VUs: {d['vus_max']:,}  |  Total: {d['total_reqs']:,} reqs  |  "
                   f"Purchased: {d['success']:,}",
                   transform=ax_checks.transAxes,
                   color='#555555', fontsize=9, va='top')

    for yi in [0.98, 0.02]:
        ax_checks.axhline(yi, color='#dddddd', linewidth=0.8)

    fig.suptitle('k6 Load Test  —  Oversell Prevention',
                 fontsize=14, fontweight='bold', y=1.03)
    save(fig, 'k6_oversell_result.png')


# ── Entry point ───────────────────────────────────────────────────────

PLOTS = {
    'nginx':      plot_nginx,
    'backend':    plot_backend,
    'breakpoint': plot_breakpoint,
    'oversell':   plot_oversell,
}

if __name__ == '__main__':
    if TEST_TYPE not in PLOTS:
        sys.exit(f'Unknown K6_TEST={TEST_TYPE!r}. Use: {", ".join(PLOTS)}')
    PLOTS[TEST_TYPE](load_metrics())
