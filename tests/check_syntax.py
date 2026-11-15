"""Fast check that runs anywhere: the page's script parses and the event facts are present."""
import pathlib, re, subprocess, sys, tempfile
html = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').read_text()
js = html[html.index("'use strict'"):html.rindex('</script>')]
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
    f.write(js)
ok = subprocess.run(['node', '--check', f.name]).returncode == 0
facts = ["dates: 'Feb 5 to 7, 2027'", "where: 'Rice University, Houston'", "size: 'About 200 students'"]
missing = [x for x in facts if x not in html]
dashes = re.findall('[–—]', html)
print('script parses' if ok else 'SCRIPT DOES NOT PARSE')
print('facts present' if not missing else f'missing facts: {missing}')
print('no long dashes' if not dashes else f'{len(dashes)} long dashes found')
sys.exit(0 if ok and not missing and not dashes else 1)
