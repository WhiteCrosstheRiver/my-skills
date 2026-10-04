"""Local ZCode discovery and isolated, encrypted account reuse. No dependencies."""
import json
import os
import re
import shutil
import subprocess
import hashlib
from pathlib import Path


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def discover():
    override = os.environ.get('ZCODE_CU_ENTRYPOINT')
    roots = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'ZCode/resources',
             Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'Programs/ZCode/resources']
    for entry in ([Path(override)] if override else []) + [r / 'glm/zcode.cjs' for r in roots]:
        if entry.is_file():
            root = entry.parent.parent
            provider = root / 'config/provider/zcode-builtin.json'
            if not provider.is_file():
                provider = entry.parent / 'provider/zcode-builtin.json'
            if not provider.is_file():
                raise RuntimeError('Installed bundle has no shipped provider configuration')
            node = shutil.which('node')
            if not node:
                raise RuntimeError('Node is not installed or not on PATH')
            return {'node': node, 'entrypoint': str(entry), 'provider': str(provider),
                    'packages': str(entry.parent / 'packages')}
    raise RuntimeError('ZCode bundle not found; set ZCODE_CU_ENTRYPOINT to zcode.cjs')


def chrome_path():
    override = os.environ.get('ZCODE_CU_BROWSER_EXECUTABLE')
    candidates = [override,
                  str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe'),
                  str(Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe')]
    return next((p for p in candidates if p and Path(p).is_file()), None)


def private_runtime(info, model=None):
    """Copy ciphertext only. Never decrypt/export the Desktop account key."""
    root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'zcode-cu-runtime'
    root.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        # A private account-bearing directory, outside the repository/run artifacts.
        user = os.environ.get('USERDOMAIN', '') + '\\' + os.environ.get('USERNAME', '')
        p = subprocess.run(['icacls', str(root), '/inheritance:r', '/grant:r', user + ':(OI)(CI)F'],
                           capture_output=True, timeout=15)
        if p.returncode:
            raise RuntimeError('Could not restrict the private runtime directory ACL')
    else:
        root.chmod(0o700)
    creds = load(Path.home() / '.zcode/v2/credentials.json')
    settings = load(Path.home() / '.zcode/v2/setting.json')
    family = settings.get('providerFamilyDomain', 'bigmodel')
    provider_id = f'account:{family}-individual-coding-plan'
    prefix = f'account-provider:coding-plan:{provider_id}:account:'
    keys = [k for k in creds if k.startswith(prefix) and k.endswith(':api-key')]
    if len(keys) != 1:
        raise RuntimeError('A unique existing Individual Coding Plan credential is required')
    key = keys[0]
    if not creds[key].startswith('enc:v1:'):
        raise RuntimeError('Refusing to duplicate an unencrypted credential')
    identity = key[len(prefix):-len(':api-key')]
    # Native CLI accepts an identity marker plus the encrypted existing key.
    # Identity is not an API secret and is never printed.
    dump(root / '.zcode/v2/credentials.json', {
        key: creds[key], f'account-provider:{provider_id}:identity': identity})
    native = load(Path.home() / '.zcode/v2/provider_config.json')
    catalog = load(info['provider'])['config']['providerConfigRules']['providerRules']
    supported = next((r['config']['builtinModelIds'] for r in catalog if r['providerId'] == provider_id), [])
    default = native.get('config', {}).get('defaultModelSelection', {})
    selected = model or (default.get('modelId') if default.get('providerId') == provider_id else None) or next(iter(supported), None)
    if selected not in supported:
        raise RuntimeError('Requested model is not in the shipped Coding Plan catalog')
    if selected != next(iter(supported), None):
        raise RuntimeError('ZCode 0.16.9 headless ignores alternate configured selections; per-dispatch alternate models require a supported account-provisioned app-server')
    # Session-local file is returned separately by delegate; shared default stays untouched.
    packages = Path(info['packages'])
    launcher = root / 'launcher'; launcher.mkdir(exist_ok=True)
    package_link = launcher / 'packages'
    if package_link.exists():
        if package_link.resolve() != packages.resolve():
            raise RuntimeError('Private launcher package link points to an unexpected directory')
    elif os.name == 'nt':
        quoted_link = "'" + str(package_link).replace("'", "''") + "'"
        quoted_target = "'" + str(packages).replace("'", "''") + "'"
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                        'New-Item -ItemType Junction -Path ' + quoted_link + ' -Target ' + quoted_target + ' | Out-Null'],
                       check=True, capture_output=True, timeout=15)
    else:
        package_link.symlink_to(packages, target_is_directory=True)
    keep = {'node-repl-host', 'browser-use', 'computer-use'}
    suppressed = []
    for manifest in packages.glob('*/.zcode-plugin/plugin.json'):
        name = load(manifest).get('name')
        if name and name not in keep: suppressed.append(name + '@zcode-plugins-official')
    config = {'plugins': {'dirs': [], 'suppressedBuiltins': suppressed},
              'memory': {'enabled': False}}
    dump(root / '.zcode/cli/config.json', config)
    env = dict(os.environ, ZCODE_DATA_BASE_DIR=str(root), ZCODE_STORAGE_DIR=str(root / '.zcode'),
               ZCODE_BUILTIN_PROVIDER_CONFIG_FILE=info['provider'])
    # Do not invent broker tokens or enable development bypasses.
    env.pop('ZCODE_CUA_DEV_MODE', None)
    return env, provider_id, selected


def make_personal(path, provider_id, model):
    dump(path, {'schemaVersion': 1, 'config': {
        'providerConfigRules': {'providerRules': []},
        'modelConfigRules': {'providerModelRules': [], 'manualProviderModelRules': []},
        'defaultModelSelection': {'providerId': provider_id, 'modelId': model}}})


def prepare_launcher(info, env):
    """Use the unchanged shipped CLI with its missing pinned dependency alongside it."""
    root = Path(env['ZCODE_DATA_BASE_DIR']) / 'launcher'
    root.mkdir(parents=True, exist_ok=True)
    entry = root / 'zcode.cjs'
    source = Path(info['entrypoint'])
    if not entry.exists() or hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(entry.read_bytes()).digest():
        shutil.copyfile(source, entry)
    package = root / 'node_modules/playwright-core/package.json'
    required = load(Path(info['packages']) / 'browser-use-plugin/package.json')['devDependencies']['playwright-core']
    if not package.is_file() or load(package)['version'] != required:
        raise RuntimeError('Missing pinned playwright-core ' + required + '; run scripts/setup_runtime.py')
    return str(entry)


def parse_object(text):
    """Accept exact JSON or one JSON fenced block; never execute returned content."""
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I)
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError('Expected a JSON object')
    return obj


def parse_report(text):
    try: return parse_object(text)
    except (ValueError, json.JSONDecodeError): pass
    # A prose prefix plus one terminal Markdown JSON fence is common in blockers.
    # Strip only the final fence, never text following the object.
    text = re.sub(r'\s*```\s*$', '', text.strip())
    # Salvage one final JSON object after plain prose; reject competing objects.
    decoder = json.JSONDecoder(); candidates = []
    for match in re.finditer(r'\{', text):
        try:
            obj, end = decoder.raw_decode(text[match.start():])
            if isinstance(obj, dict) and 'run_id' in obj:
                candidates.append((obj, match.start()+end))
        except ValueError: pass
    if len(candidates) != 1 or text[candidates[0][1]:].strip():
        raise ValueError('Expected one unambiguous final report JSON object')
    return candidates[0][0]
