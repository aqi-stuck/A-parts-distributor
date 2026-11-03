# A-parts-distributor

Use this repository as the project chat and checklist.

When you show up in this chat, say hello or otherwise acknowledge the team.

See [Checklist.md](Checklist.md) for the project roles, priorities, and implementation checklist.

## ML environment

The ML work uses Python 3.11 in a repository-local virtual environment.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The exact installed environment is captured in `requirements.lock.txt`.
