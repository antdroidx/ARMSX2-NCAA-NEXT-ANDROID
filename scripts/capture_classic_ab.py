"""Capture existing logcat and a screenshot without clearing logs or changing settings."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--adb', required=True)
p.add_argument('--serial', required=True)
p.add_argument('--variant', choices=['armsx2', 'classic', 'ramprobe'], required=True)
p.add_argument('--scene', required=True)
p.add_argument('--notes', required=True, help='Build, renderer, settings, pack identity, game/save, observed result')
args = p.parse_args()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out = Path(__file__).resolve().parents[1] / 'diagnostics' / (stamp + '-' + args.variant)
out.mkdir(parents=True, exist_ok=False)
adb = [args.adb, '-s', args.serial]
package = {'armsx2': 'com.armsx2.ncaanext', 'classic': 'com.ncaanext.classic3668.diagnostic',
           'ramprobe': 'com.ncaanext.classic3668.ramprobe'}[args.variant]
errors = []
def capture(name, command):
    result = subprocess.run(adb + command, capture_output=True, timeout=60)
    (out / name).write_bytes(result.stdout)
    (out / (name + '.stderr')).write_bytes(result.stderr)
    if result.returncode:
        errors.append({'command': command, 'exit': result.returncode})
capture('device.txt', ['shell', 'getprop'])
capture('package.txt', ['shell', 'dumpsys', 'package', package])
capture('logcat.txt', ['logcat', '-d', '-v', 'threadtime'])
capture('memory.txt', ['shell', 'dumpsys', 'meminfo', package])
remote = '/data/local/tmp/next-classic-ab-' + stamp + '.png'
capture('screenshot-command.txt', ['shell', 'screencap', '-p', remote])
capture('screenshot-pull.txt', ['pull', remote, str(out / 'screen.png')])
capture('screenshot-cleanup.txt', ['shell', 'rm', remote])
(out / 'scene.json').write_text(json.dumps({**vars(args), 'package': package,
    'utc': stamp, 'errors': errors, 'gs_draw_trace_available': False}, indent=2) + '\n')
print(out)
if errors:
    raise SystemExit('Some captures failed; see scene.json and stderr files.')
