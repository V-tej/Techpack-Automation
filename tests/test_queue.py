import pytest
import time
import json
import dashboard

@pytest.fixture
def client():
    dashboard.app.config['TESTING'] = True
    with dashboard.app.test_client() as client:
        yield client

def test_sequential_queue(client, monkeypatch):
    processed_jobs = []
    
    def mock_run_pipeline(job_id, pdf_path, brand, style):
        dashboard.jobs[job_id]["status"] = "processing"
        processed_jobs.append(job_id)
        time.sleep(0.3)  # Simulate processing time
        dashboard.jobs[job_id]["status"] = "done"

    monkeypatch.setattr(dashboard, "run_pipeline", mock_run_pipeline)

    # Empty the queue and jobs
    while not dashboard.job_queue.empty():
        try:
            dashboard.job_queue.get_nowait()
            dashboard.job_queue.task_done()
        except:
            pass
    dashboard.jobs.clear()

    # Add three dummy tasks directly to the queue
    job1_id = "job_test_1"
    job2_id = "job_test_2"
    job3_id = "job_test_3"

    dashboard.jobs[job1_id] = {"id": job1_id, "status": "queued", "logs": [], "result": None}
    dashboard.jobs[job2_id] = {"id": job2_id, "status": "queued", "logs": [], "result": None}
    dashboard.jobs[job3_id] = {"id": job3_id, "status": "queued", "logs": [], "result": None}

    dashboard.job_queue.put((job1_id, "dummy_path_1", "TEST_BRAND", "STYLE_1"))
    dashboard.job_queue.put((job2_id, "dummy_path_2", "TEST_BRAND", "STYLE_2"))
    dashboard.job_queue.put((job3_id, "dummy_path_3", "TEST_BRAND", "STYLE_3"))

    # Give the background thread a tiny moment to start processing the first job
    time.sleep(0.05)

    # Check the queue API endpoint while it's processing
    response = client.get(f"/api/queue?job_id={job2_id}")
    data = json.loads(response.data)
    assert data["active_job"] == job1_id
    assert data["queue_length"] == 2
    assert data["position"] == 1  # job2 is the first in queue (position 1)

    response = client.get(f"/api/queue?job_id={job3_id}")
    data = json.loads(response.data)
    assert data["position"] == 2  # job3 is the second in queue (position 2)

    # Wait for the worker to finish all jobs
    dashboard.job_queue.join()

    # Verify they were processed sequentially and in order
    assert processed_jobs == [job1_id, job2_id, job3_id]
    assert dashboard.jobs[job1_id]["status"] == "done"
    assert dashboard.jobs[job2_id]["status"] == "done"
    assert dashboard.jobs[job3_id]["status"] == "done"
