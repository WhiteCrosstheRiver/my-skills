"""Install one missing dependency next to a private copy of the shipped CLI."""
import subprocess
import shutil
from pathlib import Path
from runtime import discover, private_runtime, load, dump, prepare_launcher


def main():
    info = discover()
    env, _, _ = private_runtime(info)
    root = Path(env['ZCODE_DATA_BASE_DIR']) / 'launcher'; root.mkdir(parents=True, exist_ok=True)
    required = load(Path(info['packages']) / 'browser-use-plugin/package.json')['devDependencies']['playwright-core']
    dump(root / 'package.json', {'name': 'local-zcode-cu-launcher', 'private': True,
                               'version': '0.1.0', 'dependencies': {'playwright-core': required}})
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not npm: raise RuntimeError('npm is needed to install the missing pinned runtime')
    subprocess.run([npm, 'install', '--prefix', str(root), '--ignore-scripts', '--no-audit', '--no-fund'],
                   check=True, timeout=180)
    print('Private unchanged CLI and playwright-core ' + required + ' ready at ' + prepare_launcher(info, env))


if __name__ == '__main__': main()
