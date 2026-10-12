"""Render the actual human-authored demonstration graph for the project README."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
manifest = [json.loads(line) for line in (ROOT / 'corpus/manifest.jsonl').read_text().splitlines() if line.strip()]
annotations = json.loads((ROOT / 'decisions/examples.json').read_text())
positions = {}
fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
fig.patch.set_facecolor('#111b24')
ax.set_facecolor('#111b24')
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis('off')
ax.text(0.6, 8.3, 'AUREVION  /  KNOWLEDGE GRAPH', color='#f0ece2', fontsize=23, fontweight='bold')
ax.text(0.6, 7.8, 'An inspectable path from research to product decisions', color='#91a3af', fontsize=15)
ax.text(0.6, 7.2, 'RESEARCH SOURCES', color='#7eb8cf', fontsize=11, fontweight='bold')
ax.text(6.1, 7.2, 'DRAFT INTERPRETATIONS', color='#f5b45a', fontsize=11, fontweight='bold')
ax.text(11.8, 7.2, 'PROPOSED DECISIONS', color='#f08350', fontsize=11, fontweight='bold')

paper_labels = ['Protein and exercise\nPosition stand · 2017', 'Protein timing\nMeta-analysis · 2013', 'Diets and body composition\nPosition stand · 2017', 'Training frequency\nMeta-analysis · 2018', 'Training adherence\nSpecific cohort · 2015']
claim_labels = ['Timing + total intake\nInterpret together', 'Frequency + weekly volume\nPreserve the condition', 'Adherence + population\nPreserve the context']
decision_labels = ['Nutrition explanations\nExpose evidence and limits', 'Training schedule\nExplain tradeoffs']

def node(identifier, x, y, label, color, width=3.8):
    positions[identifier] = (x, y, width)
    ax.add_patch(FancyBboxPatch((x, y - 0.36), width, 0.78, boxstyle='round,pad=0.10,rounding_size=0.12',
                               linewidth=1.0, edgecolor=color, facecolor='#192630', zorder=3))
    ax.text(x + 0.18, y + 0.03, label, va='center', color='#edf0eb', fontsize=11, linespacing=1.6, zorder=4)

for i, (paper, label) in enumerate(zip(manifest, paper_labels)):
    node(paper['id'], 0.6, 6.35 - i * 1.1, label, '#7eb8cf', 3.9)
for i, (claim, label) in enumerate(zip(annotations['claims'], claim_labels)):
    node(claim['id'], 6.1, 5.7 - i * 1.65, label, '#f5b45a', 4.0)
for i, (decision, label) in enumerate(zip(annotations['decisions'], decision_labels)):
    node(decision['id'], 11.8, 4.9 - i * 2.0, label, '#f08350', 3.55)

for claim in annotations['claims']:
    for source in claim['source_ids']:
        a, b = positions[source], positions[claim['id']]
        ax.add_patch(FancyArrowPatch((a[0]+a[2]+0.12, a[1]+0.03), (b[0]-0.12, b[1]+0.03),
                                     arrowstyle='-|>', mutation_scale=13, linewidth=1.4, color='#536b7b', zorder=2,
                                     connectionstyle='arc3,rad=0.06'))
for decision in annotations['decisions']:
    for claim in decision['claim_ids']:
        a, b = positions[claim], positions[decision['id']]
        ax.add_patch(FancyArrowPatch((a[0]+a[2]+0.12, a[1]+0.03), (b[0]-0.12, b[1]+0.03),
                                     arrowstyle='-|>', mutation_scale=13, linewidth=1.4, color='#9c7455', zorder=2,
                                     connectionstyle='arc3,rad=-0.04'))
ax.text(0.6, 0.77, 'HUMAN-AUTHORED DEMO  ·  Scientific links require review  ·  Live GraphRAG inference pending',
        color='#f5b45a', fontsize=11)
ax.text(0.6, 0.32, 'Five attributed CC-BY papers. Historical pipeline test corpus. No performance or clinical claims.',
        color='#91a3af', fontsize=10)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
(ROOT / 'assets').mkdir(exist_ok=True)
for extension in ['png', 'svg']:
    fig.savefig(ROOT / f'assets/evidence-graph.{extension}', facecolor=fig.get_facecolor())
svg = ROOT / 'assets/evidence-graph.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
plt.close(fig)
print('Rendered assets/evidence-graph.png and .svg from the demo records.')
