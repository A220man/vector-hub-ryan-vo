"""Exercise the local Compose deployment with a real browser and Keycloak.

Run `python scripts/verify_browser.py create`, restart the backend, then run
`python scripts/verify_browser.py verify`. Uses only the bundled demo realm.
"""
import json
import re
import sys
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = 'http://localhost:5173'
API = BASE + '/api/v1'
RECORD = Path('.runtime-project.json')
mode = sys.argv[1] if len(sys.argv) == 2 else ''
if mode not in {'create', 'verify'}:
    raise SystemExit('Usage: verify_browser.py create|verify')

if mode == 'create':
    subprocess.run(['docker', 'compose', 'exec', '-T', 'backend', 'python', '-c', "from pathlib import Path\nimport subprocess\np=Path('/tmp/vectorhub-qa-origin')\np.mkdir()\nsubprocess.run(['git','init','-b','main',str(p)],check=True)\n(p/'README.md').write_text('Isolated browser acceptance fixture\\n')\nsubprocess.run(['git','-C',str(p),'add','README.md'],check=True)\nsubprocess.run(['git','-C',str(p),'-c','user.name=Acceptance Test','-c','user.email=acceptance@example.invalid','commit','-m','Initialize isolated acceptance fixture'],check=True)\n"], check=True, timeout=30, stdout=subprocess.DEVNULL)

with sync_playwright() as driver:
    browser = driver.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(30000)
    # This fresh context must not inherit any session from the earlier run.
    assert context.request.get(API + '/projects').status == 401
    forbidden = context.request.post(API + '/projects', data={
        'name': 'Must not exist', 'git_url': 'https://example.com/forbidden.git'})
    assert forbidden.status == 401, f'Anonymous write returned {forbidden.status}'
    page.goto(BASE + '/login')
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_url(re.compile(r'http://localhost:8080/realms/vectorhub/.*'))
    page.locator('#username').fill('admin')
    page.locator('#password').fill('admin')
    page.locator('#kc-login').click()
    page.wait_for_url(BASE + '/')
    session = context.request.get(API + '/auth/me')
    assert session.status == 200, f'Actual OIDC callback failed: {session.status}'
    cookies = {row['name']: row for row in context.cookies(BASE)}
    assert cookies.get('vectorhub_session', {}).get('httpOnly') is True
    invalid_csrf = context.request.post(API + '/projects', data={
        'name': 'Must not exist', 'git_url': 'https://example.com/forbidden.git'},
        headers={'X-CSRF-Token': 'intentionally-invalid'})
    assert invalid_csrf.status == 403, f'Invalid CSRF write returned {invalid_csrf.status}'
    if mode == 'create':
        page.goto(BASE + '/projects')
        page.get_by_role('button', name='New Project', exact=True).click()
        fields = page.locator('form input')
        fields.nth(0).fill('Browser acceptance project')
        fields.nth(1).fill('/tmp/vectorhub-qa-origin')
        with page.expect_response(lambda response: response.url == API + '/projects' and response.request.method == 'POST') as response:
            page.get_by_role('button', name='Create', exact=True).click()
        created = response.value
        assert created.status == 201, f'Browser project write returned {created.status}'
        project = created.json()
        expect(page.get_by_role('heading', name=project['name'], exact=True)).to_be_visible()
        with page.expect_response(lambda response: response.url == API + '/projects/' + project['id'] + '/clone' and response.request.method == 'POST') as cloned:
            page.get_by_role('button', name='Prepare repository', exact=True).click()
        assert cloned.value.status == 200
        assert cloned.value.json()['status'] == 'ready', 'Actual git preparation failed'
        page.get_by_role('link', name='Create worktree', exact=True).click()
        expect(page.get_by_role('heading', name='New Worktree', exact=True)).to_be_visible()
        fields = page.locator('form input:not([type="hidden"]):not(:disabled)')
        fields.nth(0).fill('Browser acceptance worktree')
        fields.nth(1).fill('feature/browser-acceptance')
        fields.nth(2).fill('main')
        with page.expect_response(lambda response: response.url == API + '/worktrees/' + project['id'] and response.request.method == 'POST') as worktree_response:
            page.get_by_role('button', name='Create', exact=True).click()
        assert worktree_response.value.status == 201
        worktree = worktree_response.value.json()
        assert worktree['status'] == 'ready', 'Real git worktree creation failed'
        expect(page.get_by_role('link', name=worktree['name'], exact=True)).to_be_visible()
        page.goto(BASE + '/agents')
        page.get_by_role('link', name='New Agent Run', exact=True).click()
        page.locator('form select').nth(0).select_option(worktree['id'])
        page.locator('form select').nth(1).select_option('custom')
        page.locator('form textarea').fill('Browser acceptance lifecycle record')
        with page.expect_response(lambda response: response.url.split('?')[0] == API + '/agent-runs' and response.request.method == 'POST') as run_response:
            page.get_by_role('button', name='Create', exact=True).click()
        assert run_response.value.status == 201
        run = run_response.value.json()
        expect(page.get_by_role('heading', name='custom', exact=True)).to_be_visible()
        # The selected foundation feature records lifecycle; launching a real agent is a later feature.
        for action, expected in [('start', 'running'), ('stop', 'stopped')]:
            with page.expect_response(lambda response: response.url == API + '/agent-runs/' + run['id'] + '/' + action and response.request.method == 'POST') as changed:
                page.get_by_role('button', name=action.title(), exact=True).click()
            assert changed.value.status == 200
            assert changed.value.json()['status'] == expected
            expect(page.get_by_text(expected, exact=True)).to_be_visible()
        RECORD.write_text(json.dumps({'id': project['id'], 'name': project['name'], 'worktree_id': worktree['id'], 'run_id': run['id']}))
    else:
        project = json.loads(RECORD.read_text())
        result = context.request.get(API + '/projects/' + project['id'])
        assert result.status == 200, f'Persisted project fetch returned {result.status}'
        assert result.json()['name'] == project['name']
        page.goto(BASE + '/projects/' + project['id'])
        expect(page.get_by_role('heading', name=project['name'], exact=True)).to_be_visible()
        assert result.json()['status'] == 'ready'
        worktree = context.request.get(API + '/worktrees/' + project['worktree_id'])
        assert worktree.status == 200 and worktree.json()['status'] == 'ready'
        run = context.request.get(API + '/agent-runs/' + project['run_id'])
        assert run.status == 200 and run.json()['status'] == 'stopped'
        page.goto(BASE + '/agents/' + project['run_id'])
        expect(page.get_by_role('heading', name='custom', exact=True)).to_be_visible()
        expect(page.get_by_text('stopped', exact=True)).to_be_visible()
    print(json.dumps({'phase': mode, 'oidc_browser_login': 'passed', 'anonymous_write': 'rejected',
                      'invalid_csrf_write': 'rejected', 'project': project['id'], 'core_workflow': 'passed'}))
    context.close()
    browser.close()
