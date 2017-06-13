# encoding: utf-8

from dump2polarion.dumper_cli import get_args


def test_get_args():
    args = get_args(['-i', 'dummy', '-t', 'testrun_id'])
    assert args.input_file == 'dummy'
    assert args.output_file is None
    assert args.testrun_id == 'testrun_id'
    assert args.config_file is None
    assert args.no_submit is False
    assert args.user is None
    assert args.password is None
    assert args.force is False
    assert args.log_level is None
