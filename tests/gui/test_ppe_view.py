import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from gui.ppe_view import PPEView

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_ppe.return_value = [
        {"id": 1, "asset_name": "Test Asset", "category": "Computers", "gross_op": 100, "useful_life_yrs": 3}
    ]
    return db

def test_ppe_view_init(tk_root, mock_db):
    view = PPEView(tk_root, mock_db)
    assert len(view._assets) == 1
    assert view._assets[0]["asset_name"] == "Test Asset"

@patch('gui.ppe_view.messagebox')
def test_ppe_view_delete_asset(mock_msgbox, tk_root, mock_db):
    mock_msgbox.askyesno.return_value = True
    view = PPEView(tk_root, mock_db)
    
    # Mocking grid selection
    with patch.object(view._grid, 'get_selected_iid', return_value="1"):
        view._delete_asset()
        mock_db.delete_ppe.assert_called_with(1)

@patch('gui.ppe_view.messagebox')
def test_ppe_view_post_dep(mock_msgbox, tk_root, mock_db):
    db = MagicMock()
    db.get_ppe.return_value = [
        {"id": 1, "asset_name": "Tangible", "category": "Computers", "gross_op": 500, "useful_life_yrs": 10, "dep_charge": 50},
        {"id": 2, "asset_name": "Intangible", "category": "Software", "gross_op": 200, "useful_life_yrs": 10, "dep_charge": 20}
    ]
    db.get_meta.return_value = "COMPANY"
    db.get_adjustments.return_value = []
    
    view = PPEView(tk_root, db)
    
    # Ensure assets are present
    assert len(view._assets) == 2
    view._post_dep()
    
    # 2 for tangible, 2 for intangible
    assert db.add_adjustment.call_count == 4
