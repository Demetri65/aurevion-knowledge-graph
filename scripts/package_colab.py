from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
destination = root / 'dist/aurevion-knowledge-graph-colab.zip'
destination.parent.mkdir(exist_ok=True)
included = ['notebooks', 'src', 'configs', 'corpus', 'decisions', 'evaluations', 'docs', 'scripts', 'assets', 'tests']
with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ['README.md', 'LICENSE', 'pyproject.toml', 'requirements.txt', '.gitignore']:
        archive.write(root / name, arcname=f'aurevion-knowledge-graph/{name}')
    for directory in included:
        for path in sorted((root / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                archive.write(path, arcname=f'aurevion-knowledge-graph/{path.relative_to(root)}')
print(f'Colab source bundle: {destination} ({destination.stat().st_size:,} bytes)')
