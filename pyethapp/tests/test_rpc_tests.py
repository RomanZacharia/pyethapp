import os
import pytest
from subprocess import Popen, PIPE
import time
import re

#def test_externally(test_app, tmpdir):


def prepare_rpc_tests(tmpdir):
    rpc_tests = tmpdir.mkdir('testdata')

    assert Popen(['git', 'clone', 'https://github.com/ethereum/rpc-tests'], cwd=str(rpc_tests)).wait() == 0
    tests_dir = rpc_tests.join('rpc-tests')
    assert Popen(['git', 'submodule', 'update', '--init', '--recursive'], cwd=str(tests_dir)).wait() == 0
    assert Popen(['npm', 'install'], cwd=str(tests_dir)).wait() == 0
    return tests_dir


@pytest.fixture()
def test_setup(request, tmpdir):
    """
    start the test_app with `subprocess.Popen`, so we can kill it properly.
    :param request:
    :param tmpdir:
    :return:
    """
    rpc_tests_dir = prepare_rpc_tests(tmpdir)

    test_data = rpc_tests_dir.join('lib/tests/BlockchainTests/bcRPC_API_Test.json')
    test_app = Popen([
        'pyethapp',
        '-d', str(tmpdir),
        '-l:info,eth.chainservice:debug,jsonrpc:debug',
        '-c jsonrpc.listen_port=8081',
        '-c p2p.max_peers=0',
        '-c p2p.min_peers=0',
        'blocktest',
        str(test_data),
        'RPC_API_Test'
    ])
    def fin():
        test_app.terminate()
    request.addfinalizer(fin)

    return (test_app, rpc_tests_dir)

@pytest.mark.skipif(os.getenv('TRAVIS') != None, reason="don't start external test on travis")
def test_eth(test_setup):
    # Some of the errors of the external rpc-tests are ignored as:
    #  1) the Whisper protocol is not implemented and its tests fail;
    #  2) the eth_accounts method should be skipped;
    #  3) the eth_getFilterLogs fails due to the invalid test data;

    ignored_errors = [
        'eth_accounts PYTHON should return an array with accounts:',
        'eth_getFilterLogs PYTHON should return a list of logs, when asking without defining an address and using toBlock "latest":',
        'eth_getFilterLogs PYTHON should return a list of logs, when asking without defining an address and using toBlock "pending":',
        'eth_getFilterLogs PYTHON should return a list of logs, when filtering with defining an address and using toBlock "latest":',
        'eth_getFilterLogs PYTHON should return a list of logs, when filtering with defining an address and using toBlock "pending":',
        'eth_getFilterLogs PYTHON should return a list of logs, when filtering by topic "0x0000000000000000000000000000000000000000000000000000000000000001":',
        'eth_getFilterLogs PYTHON should return a list of anonymous logs, when filtering by topic "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff":',
        'eth_getFilterLogs PYTHON should return a list of logs, when filtering by topic "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff":',
        # The following error is fixed in the PR rpc-tests#9
        # 'eth_getTransactionByBlockNumberAndIndex PYTHON should return transactions for the pending block when using "pending" and sending transactions before:',
        'eth_uninstallFilter PYTHON should return a boolean when uninstalling a block filter:']

    (test_app, rpc_tests_dir) = test_setup
    time.sleep(60)
    tests = Popen(['make', 'test.eth'], stdout=PIPE, cwd=str(rpc_tests_dir))
    output = tests.communicate()[0]
    rpc_errors = re.finditer(r'  (\d+)\)(.+)\n', output)
    success = True
    err_string = ''
    for e in rpc_errors:
        if e.groups()[1].strip() in ignored_errors:
            err_string += '\nSkipping: ' + e.groups()[1]
        else:
            err_string += '\nERROR: ' + e.groups()[1]
            success = False
    assert success, err_string
    #FIXME: generate a report in a pytest compatible format
