from pathlib import Path
import ast
import nbformat

path = Path(__file__).resolve().parents[1] / 'notebooks/01_graphrag_colab.ipynb'
notebook = nbformat.read(path, as_version=4)
nbformat.validate(notebook)
code_cells = [cell for cell in notebook.cells if cell.cell_type == 'code']
for index, cell in enumerate(code_cells):
    compile(cell.source, f'cell-{index}', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    if cell.outputs or cell.execution_count is not None:
        raise ValueError('The committed source notebook must have no execution outputs.')
assert any('RUN_LIVE = False' in cell.source for cell in code_cells)
assert not any('AIza' in cell.source for cell in code_cells)
print(f'Notebook schema and Python syntax verified: {len(code_cells)} code cells; live disabled; source outputs empty.')
