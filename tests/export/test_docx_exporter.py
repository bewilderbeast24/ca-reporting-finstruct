import pytest
from unittest.mock import patch, MagicMock
from export.docx_exporter import _fill, export_docx

def test_fill_basic_replacement():
    template = "Company: {{COMPANY_NAME}}, FY End: {{FY_END_YEAR}}"
    em = {
        "entity_name": "Test Corp",
        "financial_year": "2024-25"
    }
    result = _fill(template, em)
    assert "Company: Test Corp" in result
    assert "FY End: 2025" in result

def test_fill_opinion_paragraphs():
    template = "{{OPINION_PARA}}"
    
    # Test Unmodified
    em = {"opinion_type": "Unmodified", "financial_year": "2024-25"}
    result = _fill(template, em)
    assert "true and fair view" in result

    # Test Qualified
    em["opinion_type"] = "Qualified"
    result = _fill(template, em)
    assert "except for the effects of the matters described" in result

    # Test Adverse
    em["opinion_type"] = "Adverse"
    result = _fill(template, em)
    assert "because of the significance of the matters" in result

    # Test Disclaimer
    em["opinion_type"] = "Disclaimer"
    result = _fill(template, em)
    assert "We do not express an opinion" in result

def test_fill_missing_keys():
    template = "Company: {{COMPANY_NAME}}, Auditor: {{AUDITOR_FIRM}}"
    em = {}
    result = _fill(template, em)
    assert "Company: [Company]" in result
    assert "Auditor: [Auditor Firm]" in result

@patch('export.docx_exporter.Document')
def test_export_docx_default_templates(mock_document_class, tmp_path):
    mock_doc = MagicMock()
    mock_document_class.return_value = mock_doc
    
    output_path = tmp_path / "test_report.docx"
    em = {
        "entity_name": "Test Corp",
        "financial_year": "2024-25"
    }
    
    export_docx(em, output_path)
    
    mock_document_class.assert_called_once()
    assert mock_doc.add_heading.call_count >= 2
    mock_doc.save.assert_called_once_with(output_path)

@patch('export.docx_exporter.Document')
def test_export_docx_custom_templates(mock_document_class, tmp_path):
    mock_doc = MagicMock()
    mock_document_class.return_value = mock_doc
    
    output_path = tmp_path / "test_report.docx"
    em = {}
    
    dr_text = "DIRECTORS' REPORT\nCustom DR line"
    ar_text = "INDEPENDENT AUDITOR'S REPORT\nCustom AR line"
    
    export_docx(em, output_path, directors_report_text=dr_text, audit_report_text=ar_text)
    
    mock_doc.add_heading.assert_any_call("DIRECTORS' REPORT", level=1)
    mock_doc.add_heading.assert_any_call("INDEPENDENT AUDITOR'S REPORT", level=1)
    
    mock_doc.add_paragraph.assert_called()
    mock_doc.save.assert_called_once_with(output_path)
