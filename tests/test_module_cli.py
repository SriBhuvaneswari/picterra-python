import pytest
import subprocess
import os
import argparse
from urllib.parse import urljoin
from unittest.mock import MagicMock, patch, mock_open

from picterra.__main__ import parse_args, APIClient

def test_parser_arg_errors(capsys):
    # SystemExit does not inherit from Exception
    with pytest.raises(BaseException):
        parse_args(['-foobar', '-spam'])
    captured = capsys.readouterr()
    assert 'unrecognized arguments' in captured.err
    assert 'foobar' in captured.err


def test_rasters_list(monkeypatch):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_rasterlist = MagicMock(return_value=['foo', 'bar'])
    mock_rasterlist.called is False
    monkeypatch.setattr(APIClient, 'list_rasters', mock_rasterlist)
    parse_args(['list', 'rasters'])
    mock_rasterlist.called is True


def test_detectors_list(monkeypatch):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_detectorslist = MagicMock(return_value=['foo', 'bar'])
    mock_detectorslist.called is False
    monkeypatch.setattr(APIClient, 'list_detectors', mock_detectorslist)
    parse_args(['list', 'detectors'])
    mock_detectorslist.called is True

def test_prediction(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_run, mock_download = MagicMock(return_value='foobar'), MagicMock()
    monkeypatch.setattr(APIClient, 'run_detector', mock_run)
    monkeypatch.setattr(APIClient, 'download_result_to_file', mock_download)
    with pytest.raises(BaseException):
        parse_args(['detect'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'raster' in captured.err
    assert (mock_run.called or mock_download.called) is False
    with pytest.raises(BaseException):
        parse_args(['detect', 'my_raster_id'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'detector' in captured.err
    assert (mock_run.called or mock_download.called) is False
    parse_args(['detect', 'my_raster_id', 'my_detector_id', 'a_path'])
    assert (mock_run.called and mock_download.called) is True

def test_train(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_train = MagicMock()
    monkeypatch.setattr(APIClient, 'train_detector', mock_train)
    with pytest.raises(BaseException):
        parse_args(['train'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'detector' in captured.err
    assert mock_train.called is False
    parse_args(['train', 'my_detector_id'])
    mock_train.assert_called_with('my_detector_id')


def test_create_detector(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_create_detector, mock_add_raster = MagicMock(return_value='spam'), MagicMock()
    monkeypatch.setattr(APIClient, 'create_detector', mock_create_detector)
    monkeypatch.setattr(APIClient, 'add_raster_to_detector', mock_add_raster)
    assert mock_create_detector.called is False
    assert mock_add_raster.called is False
    parse_args(['create', 'detector'])
    mock_create_detector.assert_called_with(None, 'count', 'polygon', 500)
    assert mock_add_raster.call_count == 0
    mock_create_detector.reset_mock()
    mock_add_raster.reset_mock()
    parse_args([
        'create', 'detector',
        '--output-type', 'bbox', '--detection-type', 'segmentation',
        '--raster', 'foo', '--training-steps', '888',
        '--name', 'foobar'])
    mock_create_detector.assert_called_with('foobar', 'segmentation', 'bbox', 888)
    assert mock_add_raster.call_count == 1
    mock_add_raster.assert_called_with('foo', 'spam')


def test_create_raster(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_create_raster, mock_add_raster = MagicMock(return_value='spam'), MagicMock()
    monkeypatch.setattr(APIClient, 'upload_raster', mock_create_raster)
    monkeypatch.setattr(APIClient, 'add_raster_to_detector', mock_add_raster)
    assert mock_create_raster.called is False
    assert mock_add_raster.called is False
    with pytest.raises(BaseException):
        parse_args(['create', 'raster'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'path' in captured.err
    assert mock_create_raster.called is False
    assert mock_add_raster.called is False
    parse_args(['create', 'raster', 'my_path_to_tiff'])
    mock_create_raster.assert_called_with('my_path_to_tiff', None, None)
    assert mock_add_raster.called is False
    mock_create_raster.reset_mock()
    mock_add_raster.reset_mock()
    parse_args([
        'create', 'raster', 'my_path_to_tiff', '--name', 'beacon', '--folder', 'eggs',
        '--detector', 'a', 'b', 'c'
    ])
    mock_create_raster.assert_called_with('my_path_to_tiff', 'beacon', 'eggs')
    assert mock_add_raster.call_count == 3
    mock_add_raster.assert_called_with('spam', 'c')


def test_create_annotation(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_set_annotations = MagicMock()
    monkeypatch.setattr(APIClient, 'set_annotations', mock_set_annotations)
    assert mock_set_annotations.called is False
    with pytest.raises(BaseException):
        parse_args(['create', 'annotation'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'type' in captured.err
    assert mock_set_annotations.called is False
    with patch("builtins.open", mock_open(read_data='{"a":3}')):
        parse_args([
            'create', 'annotation', 'path/to/open', 'my_raster', 'my_detector',
            'training_area'
        ])
        mock_set_annotations.assert_called_with(
            'my_detector', 'my_raster', 'training_area', {"a":3})


def test_create_detectionarea(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_set_detectionarea = MagicMock()
    monkeypatch.setattr(
        APIClient, 'set_raster_detection_areas_from_file', mock_set_detectionarea)
    assert mock_set_detectionarea.called is False
    with pytest.raises(BaseException):
        parse_args(['create', 'detection_area'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'path' in captured.err
    assert mock_set_detectionarea.called is False
    parse_args([
        'create', 'detection_area', 'path/to/open', 'my_raster'
    ])
    mock_set_detectionarea.assert_called_with('my_raster', 'path/to/open')


def test_delete_raster(monkeypatch, capsys):
    monkeypatch.setattr(APIClient, '__init__', lambda s: None)
    mock_delete = MagicMock()
    monkeypatch.setattr(APIClient, 'delete_raster', mock_delete)
    assert mock_delete.called is False
    with pytest.raises(BaseException):
        parse_args(['delete', 'raster'])
    captured = capsys.readouterr()
    assert 'following arguments are required' in captured.err
    assert 'raster' in captured.err
    assert mock_delete.called is False
    parse_args(['delete', 'raster', 'my_raster'])
    mock_delete.assert_called_with('my_raster')
