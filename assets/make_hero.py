"""Generates assets/hero.svg: the thread running through every supported agent."""
import math
import os

AGENTS = [  # order along the thread, colour, label, how hop reaches it
    ('CC', '#E8845C', 'Claude Code', 'native'),
    ('CX', '#F5C451', 'Codex', 'native'),
    ('CR', '#38BDF8', 'Cursor CLI', 'read + handoff'),
    ('AG', '#8AA4FF', 'Antigravity', 'read + handoff'),
    ('GK', '#E2E8F0', 'Grok Build', 'read + handoff'),
    ('DS', '#6366F1', 'DeepSeek', 'read + handoff'),
    ('HM', '#EC4899', 'Hermes', 'read + handoff'),
    ('OC', '#5EEAD4', 'OpenCode', 'native'),
    ('KM', '#34D399', 'Kimi Code', 'native'),
    ('MM', '#FB7185', 'MiniMax Code', 'read + handoff'),
    ('QW', '#A78BFA', 'Qwen Code', 'native'),
    ('AD', '#A855F7', 'Aider', 'read + handoff'),
]
W, H, Y, AMP = 1280, 600, 410, 26
xs = [110 + i * (1060 / (len(AGENTS) - 1)) for i in range(len(AGENTS))]
ys = [Y + AMP * math.sin(i * 1.15) for i in range(len(AGENTS))]


def path():
    pts = [(30, ys[0] + 18)] + list(zip(xs, ys)) + [(1250, ys[-1] - 12)]
    d = f'M{pts[0][0]:.1f} {pts[0][1]:.1f}'
    for i in range(1, len(pts)):
        (x0, y0), (x1, y1) = pts[i - 1], pts[i]
        p = pts[i - 2] if i >= 2 else pts[i - 1]
        n = pts[i + 1] if i + 1 < len(pts) else pts[i]
        c1 = (x0 + (x1 - p[0]) / 6, y0 + (y1 - p[1]) / 6)  # Catmull-Rom to Bézier
        c2 = (x1 - (n[0] - x0) / 6, y1 - (n[1] - y0) / 6)
        d += f' C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {x1:.1f} {y1:.1f}'
    return d


stops = ''.join(f'<stop offset="{i / (len(AGENTS) - 1):.3f}" stop-color="{c}"/>' for i, (_, c, _, _) in enumerate(AGENTS))
nodes = []
for i, ((code, color, label, mode), x, y) in enumerate(zip(AGENTS, xs, ys)):
    dashed = ' stroke-dasharray="3 3"' if mode != 'native' else ''
    nodes.append(f'''
    <circle class="halo" style="animation-delay:{i * 0.36:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="36" fill="{color}"/>
    <circle cx="{x:.1f}" cy="{y:.1f}" r="24" fill="#0F1117" stroke="{color}" stroke-width="2"{dashed}/>
    <text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{color}">{code}</text>
    <text x="{x:.1f}" y="{y + 56:.1f}" text-anchor="middle" class="sans" font-size="15" font-weight="600" fill="#E6E8EE">{label}</text>
    <text x="{x:.1f}" y="{y + 74:.1f}" text-anchor="middle" class="sans" font-size="11.5" fill="#7D8596">{mode}</text>''')

d = path()
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
  <title id="t">SameThread</title>
  <desc id="d">One chat thread running through Claude Code, Codex, Cursor CLI, Antigravity, Grok Build, DeepSeek, Hermes, OpenCode, Kimi, MiniMax, Qwen Code, and Aider.</desc>
  <defs>
    <style>
      .sans {{ font-family: system-ui, -apple-system, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif; }}
      .mono {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; }}
      .flow {{ stroke-dasharray: 1 17; animation: flow 1.4s linear infinite; }}
      .halo {{ opacity: .10; animation: pulse 3.2s ease-in-out infinite both; transform-box: fill-box; transform-origin: center; }}
      @keyframes flow {{ to {{ stroke-dashoffset: -36; }} }}
      @keyframes pulse {{ 0%, 100% {{ opacity: .08; transform: scale(1); }} 50% {{ opacity: .22; transform: scale(1.14); }} }}
      @media (prefers-reduced-motion: reduce) {{ .flow, .halo {{ animation: none; }} }}
    </style>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity=".035"/></pattern>
    <radialGradient id="g1" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#E8845C" stop-opacity=".18"/><stop offset="1" stop-color="#E8845C" stop-opacity="0"/></radialGradient>
    <radialGradient id="g2" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#5EEAD4" stop-opacity=".10"/><stop offset="1" stop-color="#5EEAD4" stop-opacity="0"/></radialGradient>
    <radialGradient id="g3" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#A78BFA" stop-opacity=".18"/><stop offset="1" stop-color="#A78BFA" stop-opacity="0"/></radialGradient>
    <linearGradient id="thread" x1="30" y1="0" x2="1250" y2="0" gradientUnits="userSpaceOnUse">{stops}</linearGradient>
    <linearGradient id="word" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#F0A07F"/><stop offset=".5" stop-color="#7EF0DE"/><stop offset="1" stop-color="#C4B5FD"/></linearGradient>
    <filter id="blur" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
    <filter id="dotglow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="24"/></clipPath>
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="#0A0B10"/>
    <rect width="{W}" height="{H}" fill="url(#grid)"/>
    <circle cx="200" cy="440" r="360" fill="url(#g1)"/>
    <circle cx="660" cy="110" r="440" fill="url(#g2)"/>
    <circle cx="1080" cy="440" r="360" fill="url(#g3)"/>
  </g>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="23.5" fill="none" stroke="#ffffff" stroke-opacity=".08"/>

  <text x="80" y="92" class="sans" font-size="14" font-weight="600" letter-spacing="5" fill="#9AA3B5">SAMETHREAD</text>
  <text x="80" y="160" class="sans" font-size="56" font-weight="700" fill="#F4F5F7" letter-spacing="-1">Hop between coding agents.</text>
  <text x="80" y="226" class="sans" font-size="56" font-weight="700" fill="#F4F5F7" letter-spacing="-1">Stay on the <tspan fill="url(#word)">same thread</tspan>.</text>
  <text x="80" y="276" class="sans" font-size="20" fill="#A3ABBC">One chat history across nine coding agents, right inside each agent's own /resume.</text>

  <path d="{d}" fill="none" stroke="url(#thread)" stroke-width="10" stroke-opacity=".35" filter="url(#blur)"/>
  <path id="line" d="{d}" fill="none" stroke="url(#thread)" stroke-width="2.5" stroke-linecap="round"/>
  <path class="flow" d="{d}" fill="none" stroke="#ffffff" stroke-opacity=".7" stroke-width="2.5" stroke-linecap="round"/>
  <circle r="5" fill="#ffffff" filter="url(#dotglow)">
    <animateMotion dur="10s" repeatCount="indefinite" keyPoints="0;1;0" keyTimes="0;.5;1" calcMode="linear"><mpath href="#line"/></animateMotion>
  </circle>
  <g>{''.join(nodes)}
  </g>
</svg>
'''
with open(os.path.join(os.path.dirname(__file__), 'hero.svg'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(svg)
