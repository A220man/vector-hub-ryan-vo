from app.api.v1 import projects
from app.models.project import Project, ProjectStatus
from app.services.git_service import GitOperationResult

def test_clone_does_not_claim_ready_before_git_succeeds(client, auth_headers, git_repo_path, db_session, monkeypatch):
    response = client.post('/api/v1/projects', headers=auth_headers,
        json={'name': 'Clone state', 'git_url': git_repo_path, 'base_ref': 'main'})
    assert response.status_code == 201
    project_id = response.json()['id']
    observed = []
    def clone(*args):
        db_session.expire_all()
        observed.append(db_session.get(Project, project_id).status)
        return GitOperationResult(success=False, error='Simulated git failure')
    monkeypatch.setattr(projects.git_service, 'clone_project', clone)
    result = client.post('/api/v1/projects/' + project_id + '/clone', headers=auth_headers)
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'error'
    assert result.json()['base_path'] is None
    assert observed and observed[0] != ProjectStatus.ready, 'Unfinished clone was committed as ready before git succeeded'


def test_clone_exception_allows_clean_retry(client, auth_headers, git_repo_path, monkeypatch):
    response = client.post('/api/v1/projects', headers=auth_headers,
        json={'name': 'Retry clone', 'git_url': git_repo_path, 'base_ref': 'main'})
    project_id = response.json()['id']
    real_clone = projects.git_service.clone_project
    def partial_failure(url, path, ref):
        path.mkdir()
        (path / 'partial').write_text('incomplete')
        raise TimeoutError('simulated timeout')
    monkeypatch.setattr(projects.git_service, 'clone_project', partial_failure)
    failed = client.post('/api/v1/projects/' + project_id + '/clone', headers=auth_headers)
    assert failed.status_code == 200, failed.text
    assert failed.json()['status'] == 'error'
    monkeypatch.setattr(projects.git_service, 'clone_project', real_clone)
    retry = client.post('/api/v1/projects/' + project_id + '/clone', headers=auth_headers)
    assert retry.status_code == 200, retry.text
    assert retry.json()['status'] == 'ready', retry.text
    worktree = client.post('/api/v1/worktrees/' + project_id, headers=auth_headers,
        json={'name': 'retry-worktree', 'branch': 'feature/retry', 'start_ref': 'main'})
    assert worktree.status_code == 201, worktree.text


def test_busy_clone_rejects_second_claim(client, auth_headers, git_repo_path, db_session, monkeypatch):
    response = client.post('/api/v1/projects', headers=auth_headers,
        json={'name': 'Busy clone', 'git_url': git_repo_path, 'base_ref': 'main'})
    project_id = response.json()['id']
    project = db_session.get(Project, project_id)
    project.status = ProjectStatus.cloning
    db_session.commit()
    def unexpected(*args):
        raise AssertionError('Git should not run for an already claimed project')
    monkeypatch.setattr(projects.git_service, 'clone_project', unexpected)
    result = client.post('/api/v1/projects/' + project_id + '/clone', headers=auth_headers)
    assert result.status_code == 409, result.text
