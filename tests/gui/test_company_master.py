import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.company_master import CompanyMasterForm

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_meta.return_value = "COMPANY"
    db.get_all_entity.return_value = {
        "entity_name": "Test Co",
        "financial_year": "2024-25"
    }
    db.get_directors.return_value = []
    return db

def test_company_master_form_init_and_load(tk_root, mock_db):
    form = CompanyMasterForm(tk_root, mock_db)
    assert form._vars["entity_name"].get() == "Test Co"
    assert form._vars["financial_year"].get() == "2024-25"

@patch('gui.company_master.messagebox')
def test_company_master_form_save_validation_error(mock_msgbox, tk_root, mock_db):
    form = CompanyMasterForm(tk_root, mock_db)
    form._vars["entity_name"].set("")  # Required field empty
    form._save()
    mock_msgbox.showerror.assert_called_once()
    assert "Validation Error" in mock_msgbox.showerror.call_args[0][0]

@patch('gui.company_master.messagebox')
def test_company_master_form_save_success(mock_msgbox, tk_root, mock_db):
    form = CompanyMasterForm(tk_root, mock_db)
    form._vars["entity_name"].set("Valid Co")
    form._vars["financial_year"].set("2024-25")
    res = form._save()
    assert res is True
    
    mock_db.save_entity_batch.assert_called_once()
    mock_msgbox.showinfo.assert_called_once()

@patch('gui.company_master.messagebox')
def test_company_master_form_save_and_next(mock_msgbox, tk_root, mock_db):
    proceed_cb = MagicMock()
    form = CompanyMasterForm(tk_root, mock_db, on_proceed=proceed_cb)
    form._vars["entity_name"].set("Valid Co")
    form._vars["financial_year"].set("2024-25")
    form._save_and_next()
    proceed_cb.assert_called_once()

@patch('gui.company_master.messagebox')
def test_company_master_form_dir_remove_no_selection(mock_msgbox, tk_root, mock_db):
    form = CompanyMasterForm(tk_root, mock_db)
    form._dir_remove()
    mock_msgbox.showinfo.assert_called_with("Select", "Select a director to remove.")
