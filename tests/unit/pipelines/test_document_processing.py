import os
import time
import requests
import pytest

@pytest.fixture(scope="module")
def api_base_url():
    return "http://localhost:8000/api"

@pytest.fixture(scope="module")
def test_file_path():
    # Use the provided file path as a fixture
    return "/Users/domwis/VSCode/SKIB/SKIB-AI/data/raw_docs/2_AGS Trouble shooting 가이드_v1.1.pdf"

@pytest.fixture(scope="module")
def document_data():
    return {
        'project_id': '1',
        'document_id': '123',
        'name': 'test.pdf'
    }

def test_file_upload(api_base_url, test_file_path, document_data):
    with open(test_file_path, "rb") as f:
        files = {'file': (os.path.basename(test_file_path), f, 'application/pdf')}
        response = requests.post(
            f"{api_base_url}/document",
            files=files,
            params=document_data  # <-- Use params, not data
        )
    print(response.text)  # Optional: for debugging
    assert response.status_code == 200
    assert "파일 처리 완료" in response.json().get("message", "").lower()

def test_processing_status_immediate(api_base_url, document_data):
    response = requests.get(f"{api_base_url}/document/summary/{document_data['document_id']}")
    assert response.status_code in (200, 202, 404)  # Acceptable: ready, processing, or not found

def test_processing_status_after_delay(api_base_url, document_data):
    time.sleep(5)
    response = requests.get(f"{api_base_url}/document/summary/{document_data['document_id']}")
    if response.status_code == 200:
        assert "summary" in response.json()
    else:
        assert response.status_code in (202, 404)

def test_invalid_document_id(api_base_url):
    response = requests.get(f"{api_base_url}/document/summary/invalid_id")
    assert response.status_code == 404

def test_upload_missing_file(api_base_url, document_data):
    response = requests.post(f"{api_base_url}/document", data=document_data)
    assert response.status_code in (400, 422)

def test_document_summary_success(api_base_url, document_data, test_file_path):
    # Step 1: Upload the document
    with open(test_file_path, "rb") as f:
        files = {'file': (os.path.basename(test_file_path), f, 'application/pdf')}
        upload_response = requests.post(
            f"{api_base_url}/document",
            files=files,
            params=document_data
        )
    assert upload_response.status_code == 200

    # Step 2: Poll the summary endpoint until processing is complete or timeout
    max_wait = 30  # seconds
    interval = 2   # seconds
    waited = 0
    summary_url = f"{api_base_url}/document/summary/{document_data['document_id']}"
    while waited < max_wait:
        response = requests.get(summary_url)
        if response.status_code == 200:
            data = response.json()
            assert "summary" in data
            assert isinstance(data["summary"], str)
            assert "keywords" in data
            assert isinstance(data["keywords"], list)
            break
        elif response.status_code == 202:
            time.sleep(interval)
            waited += interval
        else:
            assert False, f"Unexpected status code: {response.status_code} ({response.text})"
    else:
        assert False, "Document processing did not complete in time"