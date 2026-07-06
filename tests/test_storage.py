import os
import json
from unittest.mock import patch, mock_open, MagicMock
from app.storage import save_entry

@patch('app.storage.os.makedirs')
@patch('app.storage.datetime')
@patch('builtins.open', new_callable=mock_open)
def test_save_entry(mock_file, mock_datetime, mock_makedirs):
    # Setup mocks
    mock_now = MagicMock()
    mock_now.strftime.side_effect = lambda fmt: "2026-07" if fmt == "%Y-%m" else "2026-07-06T120000Z"
    mock_now.isoformat.return_value = "2026-07-06T12:00:00+00:00"
    mock_datetime.now.return_value = mock_now
    
    # Test execution
    entry_type = "meal"
    raw_input = "Ich habe einen Apfel gegessen."
    structured_data = {"food": "Apfel"}
    
    filepath = save_entry(entry_type, raw_input, structured_data)
    
    # Assertions
    mock_makedirs.assert_called_once()
    assert mock_makedirs.call_args[0][0].endswith("2026-07")
    
    assert filepath.endswith("2026-07-06T120000Z_meal.json")
    
    # Verify file was written
    mock_file.assert_called_once_with(filepath, "w", encoding="utf-8")
    
    # Verify content
    handle = mock_file()
    # json.dump makes several calls to write
    written_data = "".join([call.args[0] for call in handle.write.call_args_list])
    
    loaded_data = json.loads(written_data)
    assert loaded_data["type"] == "meal"
    assert loaded_data["timestamp"] == "2026-07-06T12:00:00+00:00"
    assert loaded_data["raw_input"] == raw_input
    assert loaded_data["data"] == structured_data
