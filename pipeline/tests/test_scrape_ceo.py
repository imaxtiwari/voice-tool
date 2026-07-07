import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import requests
from pipeline.scrape_ceo import main, get_url_slug

def test_url_slug_generation():
    assert get_url_slug("https://example.com/some/path/page.html") == "example_com_some"
    assert get_url_slug("https://www.google.com/") == "google_com"
    assert get_url_slug("http://test.org/segment?param=value") == "test_org_segment"

@patch("pipeline.scrape_ceo.requests.get")
def test_scrape_ceo_success(mock_get, tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = (
        "<article>"
        "<p>" + "word " * 210 + "</p>"
        "<nav>Navigation content</nav>"
        "<footer>Footer content</footer>"
        "</article>"
    )
    mock_get.return_value = mock_response
    
    input_list = tmp_path / "ceo_url_list.txt"
    input_list.write_text("https://example.com/success\n")
    
    output_dir = tmp_path / "raw_ceo_docs"
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list)])
        
    expected_file = output_dir / "example_com_success.txt"
    assert expected_file.exists()
    
    content = expected_file.read_text()
    assert "word" in content
    assert "Navigation content" not in content
    assert "Footer content" not in content

@patch("pipeline.scrape_ceo.requests.get")
def test_scrape_ceo_404(mock_get, tmp_path, capsys):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    input_list = tmp_path / "ceo_url_list.txt"
    input_list.write_text("https://example.com/notfound\n")
    
    output_dir = tmp_path / "raw_ceo_docs"
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list)])
        
    expected_file = output_dir / "example_com_notfound.txt"
    assert not expected_file.exists()
    
    captured = capsys.readouterr()
    assert "HTTP status 404" in captured.err

@patch("pipeline.scrape_ceo.requests.get")
def test_scrape_ceo_timeout(mock_get, tmp_path, capsys):
    mock_get.side_effect = requests.Timeout("Connection timed out")
    
    input_list = tmp_path / "ceo_url_list.txt"
    input_list.write_text("https://example.com/timeout\n")
    
    output_dir = tmp_path / "raw_ceo_docs"
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list)])
        
    expected_file = output_dir / "example_com_timeout.txt"
    assert not expected_file.exists()
    
    captured = capsys.readouterr()
    assert "Request failed:" in captured.err

@patch("pipeline.scrape_ceo.requests.get")
def test_scrape_ceo_word_count_drop(mock_get, tmp_path, capsys):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<article><p>" + "word " * 50 + "</p></article>"
    mock_get.return_value = mock_response
    
    input_list = tmp_path / "ceo_url_list.txt"
    input_list.write_text("https://example.com/short\n")
    
    output_dir = tmp_path / "raw_ceo_docs"
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list)])
        
    expected_file = output_dir / "example_com_short.txt"
    assert not expected_file.exists()
    
    captured = capsys.readouterr()
    assert "Word count 50 < 200" in captured.err

@patch("pipeline.scrape_ceo.requests.get")
def test_scrape_ceo_idempotency(mock_get, tmp_path):
    input_list = tmp_path / "ceo_url_list.txt"
    input_list.write_text("https://example.com/existing\n")
    
    output_dir = tmp_path / "raw_ceo_docs"
    os.makedirs(output_dir, exist_ok=True)
    
    existing_file = output_dir / "example_com_existing.txt"
    existing_file.write_text("This text already exists and shouldn't be refetched.")
    
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list)])
        
    mock_get.assert_not_called()
    assert existing_file.read_text() == "This text already exists and shouldn't be refetched."
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<article><p>" + "word " * 220 + "</p></article>"
    mock_get.return_value = mock_response
    
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list), "--force"])
        
    mock_get.assert_called_once()
    assert existing_file.read_text() != "This text already exists and shouldn't be refetched."

def test_scrape_ceo_local_file(tmp_path):
    input_list = tmp_path / "ceo_url_list.txt"
    
    local_txt = tmp_path / "my_local_doc.txt"
    local_txt_content = "This is local text. " * 50
    local_txt.write_text(local_txt_content)
    
    input_list.write_text(f"file://{local_txt}\n")
    
    output_dir = tmp_path / "raw_ceo_docs"
    with patch("pipeline.scrape_ceo.OUTPUT_DIR", str(output_dir)):
        main(["--input", str(input_list)])
        
    expected_file = output_dir / "my_local_doc.txt"
    assert expected_file.exists()
    assert expected_file.read_text() == local_txt_content
