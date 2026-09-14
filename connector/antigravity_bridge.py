#!/usr/bin/env python3
"""Local macOS Antigravity 2.0 desktop agentapi adapter. No external dependencies."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


class BridgeError(Exception):
    pass


def run(args, env=None, timeout=15):
    try:
        return subprocess.run(args, env=env, text=True, capture_output=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise BridgeError('TIMEOUT: delivery may be unknown; do not retry a mutation automatically.') from None
    except OSError:
        raise BridgeError('Cannot launch local command; check installation and execution permissions.') from None


def redact(text, secrets=()):
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[REDACTED]')
    return re.sub(r'(?i)((?:csrf[_-]?token|host_bridge_token|authorization)\s*[=:]\s*)[^\s,}]+',
                  r'\1[REDACTED]', text)


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def address(value):
    if not re.fullmatch(r'(127\.0\.0\.1|localhost|\[::1\]):[0-9]{1,5}', value):
        raise BridgeError('Only an explicit loopback host:port is supported.')
    if not 1 <= int(value.rsplit(':', 1)[1]) <= 65535:
        raise BridgeError('Invalid port.')
    return value


def discover(pid=None):
    p = run(['/bin/ps', '-axo', 'pid=,comm='])
    if p.returncode:
        raise BridgeError('Process inspection denied/unavailable. Request permission; do not bypass it.')
    found = []
    for line in p.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[1].endswith('/Antigravity.app/Contents/Resources/bin/language_server'):
            found.append(int(parts[0]))
    if pid is not None:
        if pid not in found:
            raise BridgeError('Selected PID is not a discovered Antigravity desktop language server.')
        return pid
    if len(found) != 1:
        raise BridgeError('Expected one desktop server; select --pid from: ' + str(found))
    return found[0]


def credentials(pid):
    p = run(['/bin/ps', '-p', str(pid), '-o', 'args='])
    if p.returncode:
        raise BridgeError('Cannot read selected process credentials.')
    words = shlex.split(p.stdout)
    token = None
    for i, word in enumerate(words):
        if word == '--csrf_token' and i + 1 < len(words):
            token = words[i + 1]
        elif word.startswith('--csrf_token='):
            token = word.split('=', 1)[1]
    if not token:
        raise BridgeError('No CSRF credential on the selected server; cannot authenticate.')
    return token


def ports(pid):
    p = run(['/usr/sbin/lsof', '-nP', '-a', '-p', str(pid), '-iTCP', '-sTCP:LISTEN'])
    if p.returncode:
        raise BridgeError('Cannot inspect selected server listeners.')
    result = sorted(set(re.findall(r'127\.0\.0\.1:[0-9]+', p.stdout)))
    if not result:
        raise BridgeError('No IPv4 loopback listeners found; supply --address explicitly.')
    return result


def cli_path(value):
    path = Path(value).expanduser()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise BridgeError('Desktop agentapi is missing or not executable; specify --agentapi.')
    p = run([str(path), '--help'])
    required = ('new-conversation', 'send-message', 'get-conversation-metadata')
    if p.returncode or not all(name in p.stdout for name in required):
        raise BridgeError('Installed agentapi help is incompatible; stop and inspect this version.')
    return str(path)


def build_action(args):
    if args.command == 'metadata':
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', args.conversation_id):
            raise BridgeError('Invalid conversation ID.')
        return ['get-conversation-metadata', args.conversation_id]
    if args.command == 'new' and not args.project_id:
        raise BridgeError('new requires the actual --project-id; do not invent one.')
    try:
        prompt = Path(args.prompt_file).read_text(encoding='utf-8')
    except OSError:
        raise BridgeError('Cannot read prompt file.') from None
    if not prompt.strip() or len(prompt.encode('utf-8')) > 60000:
        raise BridgeError('Prompt must be nonempty and at most 60 KB.')
    if args.command == 'new':
        action = ['new-conversation']
        if args.model:
            action.append('--model=' + args.model)
    else:
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', args.conversation_id):
            raise BridgeError('Invalid conversation ID.')
        action = ['send-message']
    if args.title:
        action.append('--title=' + args.title)
    if args.command == 'send':
        action.append(args.conversation_id)
    # Avoid allowing a leading option-looking prompt through the native parser.
    action.append('User task:\n' + prompt)
    return action


def parse(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--agentapi', default=str(Path.home() / '.gemini/antigravity/bin/agentapi'))
    p.add_argument('--pid', type=int)
    p.add_argument('--address', help='Loopback host:port; token supplied via env or selected process')
    p.add_argument('--timeout', type=int, default=30)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='Local CLI/process check only; no conversation request')
    m = sub.add_parser('metadata', help='Read metadata of an explicitly selected conversation')
    m.add_argument('conversation_id')
    for name in ('new', 'send'):
        s = sub.add_parser(name)
        s.add_argument('--prompt-file', required=True)
        s.add_argument('--title')
        s.add_argument('--execute', action='store_true', help='Dispatch exactly once (default dry run)')
        if name == 'new':
            s.add_argument('--project-id', default=os.getenv('ANTIGRAVITY_PROJECT_ID'))
            s.add_argument('--model', choices=['flash_lite', 'flash', 'pro'])
        else:
            s.add_argument('conversation_id')
    return p.parse_args(argv)


def main(argv=None):
    a = parse(argv)
    if not 1 <= a.timeout <= 60:
        raise BridgeError('Timeout must be 1–60 seconds.')
    if a.address:
        address(a.address)
    if a.command in ('new', 'send'):
        action = build_action(a)
        if not a.execute:
            emit({'mode': 'dry_run', 'action': a.command, 'will_send': False,
                  'prompt_bytes': len(action[-1].encode('utf-8')),
                  'project_id_supplied': bool(getattr(a, 'project_id', None))})
            return 0
    cli = cli_path(a.agentapi)
    if a.command == 'doctor':
        pid = discover(a.pid)
        emit({'agentapi': cli, 'pid': pid, 'candidate_addresses': ports(pid),
              'connected': False, 'note': 'CLI help verified only. No conversation accessed.'})
        return 0
    token = os.getenv('ANTIGRAVITY_CSRF_TOKEN') if a.address else None
    if a.address and token:
        candidates = [address(a.address)]
    else:
        pid = discover(a.pid)
        token = credentials(pid)
        candidates = [address(a.address)] if a.address else ports(pid)
    # Never probe multiple ports with a write, even if one looks like the RPC port.
    if len(candidates) != 1 and a.command != 'metadata':
        raise BridgeError('Multiple ports: use metadata on your own conversation to verify --address before dispatch.')
    action = build_action(a)
    for target in candidates:
        env = os.environ.copy()
        env['ANTIGRAVITY_LS_ADDRESS'] = target
        env['ANTIGRAVITY_CSRF_TOKEN'] = token
        # Do not accidentally inherit a different project for new-conversation.
        if a.command == 'new':
            env['ANTIGRAVITY_PROJECT_ID'] = a.project_id
        p = run([cli] + action, env=env, timeout=a.timeout)
        try:
            payload = json.loads(p.stdout)
        except (json.JSONDecodeError, TypeError):
            if a.command == 'metadata':
                continue
            raise BridgeError('Unparseable reply: delivery UNKNOWN. Inspect Antigravity before retrying.')
        error = payload.get('error') if isinstance(payload, dict) else 'Unexpected response format'
        if p.returncode or error:
            if a.command == 'metadata' and target != candidates[-1]:
                continue
            detail = redact(str(error or 'Native CLI failed'), (token,))
            raise BridgeError(detail + ' No automatic retry performed.')
        # Metadata may contain user information; return only minimal connection info by default.
        if a.command == 'metadata':
            emit({'ok': True, 'address': target, 'conversation_id': a.conversation_id,
                  'note': 'Metadata call succeeded; this is not task completion evidence.'})
        else:
            emit({'ok': True, 'address': target,
                  'result': json.loads(redact(json.dumps(payload), (token,))),
                  'note': 'Native CLI returned without an error. Inspect result for receipt/ID; task completion and UI visibility are not verified.'})
        return 0
    raise BridgeError('No verified RPC response. Check address, credentials and permissions.')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BridgeError as exc:
        emit({'ok': False, 'error': str(exc)})
        sys.exit(2)
