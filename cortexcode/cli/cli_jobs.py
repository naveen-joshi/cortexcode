"""Background job tracking for indexing operations."""

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console


JOBS_FILE = Path.home() / ".cortexcode" / "jobs.json"


class JobTracker:
    """Track background indexing jobs."""
    
    def __init__(self):
        self.jobs: dict[str, dict] = {}
        self.load()
    
    def load(self):
        """Load jobs from disk."""
        if JOBS_FILE.exists():
            try:
                self.jobs = json.loads(JOBS_FILE.read_text())
            except:
                self.jobs = {}
    
    def save(self):
        """Save jobs to disk."""
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        JOBS_FILE.write_text(json.dumps(self.jobs, indent=2))
    
    def create(self, job_type: str, path: str, description: str = "") -> str:
        """Create a new job."""
        job_id = f"{job_type}_{int(time.time())}"
        self.jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "path": path,
            "description": description,
            "status": "running",
            "created": time.time(),
            "updated": time.time(),
            "progress": 0,
            "total": 100,
            "message": "Starting...",
        }
        self.save()
        return job_id
    
    def update(self, job_id: str, progress: int = None, total: int = None, message: str = None, status: str = None):
        """Update a job."""
        if job_id in self.jobs:
            if progress is not None:
                self.jobs[job_id]["progress"] = progress
            if total is not None:
                self.jobs[job_id]["total"] = total
            if message is not None:
                self.jobs[job_id]["message"] = message
            if status is not None:
                self.jobs[job_id]["status"] = status
            self.jobs[job_id]["updated"] = time.time()
            self.save()
    
    def complete(self, job_id: str, message: str = "Done"):
        """Mark a job as complete."""
        self.update(job_id, status="completed", message=message, progress=100)
    
    def fail(self, job_id: str, message: str = "Failed"):
        """Mark a job as failed."""
        self.update(job_id, status="failed", message=message)
    
    def get(self, job_id: str) -> dict | None:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def list(self, status: str = None) -> list[dict]:
        """List all jobs, optionally filtered by status."""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j["status"] == status]
        return sorted(jobs, key=lambda x: x["updated"], reverse=True)
    
    def clear(self, completed: bool = True):
        """Clear completed or all jobs."""
        if completed:
            self.jobs = {k: v for k, v in self.jobs.items() if v["status"] == "running"}
        else:
            self.jobs = {}
        self.save()


def handle_jobs_list(console: Console, status: str = None) -> None:
    """List all background jobs."""
    tracker = JobTracker()
    jobs = tracker.list(status)
    
    if not jobs:
        console.print("[dim]No jobs found[/dim]")
        return
    
    console.print(f"\n[bold]Background Jobs:[/bold]\n")
    for job in jobs:
        status_icon = {"running": "🔄", "completed": "✓", "failed": "✗"}[job["status"]]
        status_color = {"running": "cyan", "completed": "green", "failed": "red"}[job["status"]]
        
        progress = job.get("progress", 0)
        total = job.get("total", 100)
        pct = int(progress / total * 100) if total > 0 else 0
        
        console.print(f"  {status_icon} [{status_color}]{job['id']}[/{status_color}]")
        console.print(f"      {job['type']}: {job.get('path', 'N/A')}")
        console.print(f"      Status: {job['status']} ({pct}%) - {job.get('message', '')}")
        console.print()


def handle_jobs_clear(console: Console, all: bool = False) -> None:
    """Clear completed jobs."""
    tracker = JobTracker()
    tracker.clear(completed=not all)
    console.print("[green]✓[/green] Jobs cleared")


def handle_jobs_watch(console: Console, job_id: str) -> None:
    """Watch a job's progress."""
    tracker = JobTracker()
    
    while True:
        job = tracker.get(job_id)
        if not job:
            console.print(f"[red]Job not found: {job_id}[/red]")
            return
        
        progress = job.get("progress", 0)
        total = job.get("total", 100)
        pct = int(progress / total * 100) if total > 0 else 0
        
        console.print(f"\r[{job['status']}] {job['message']} ({pct}%)", end="")
        
        if job["status"] != "running":
            console.print()
            break
        
        time.sleep(1)
