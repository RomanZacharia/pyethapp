from pyethapp.jsonrpc import quantity_decoder
from pyethapp.rpc_client import JSONRPCClient
import pytest
from subprocess import Popen
import time
from pyethapp.jsonrpc import address_encoder
from ethereum import utils

def executable_installed(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def prepare_rpc_tests(tmpdir):
    rpc_tests = tmpdir.mkdir('testdata')

    assert Popen(['git', 'clone', 'https://github.com/ethereum/rpc-tests'], cwd=str(rpc_tests)).wait() == 0
    tests_dir = rpc_tests.join('rpc-tests')
    import os.path
    fpath = str(tests_dir.join('lib/config.js'))
    assert os.path.isfile(fpath)
    assert Popen(['git', 'submodule', 'update', '--init', '--recursive'], cwd=str(tests_dir)).wait() == 0
    assert os.path.isfile(str(tests_dir.join('lib/tests/BlockchainTests/bcRPC_API_Test.json')).decode('unicode-escape'))
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
    assert executable_installed('pyethapp')
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

    time.sleep(60)
    return (test_app, rpc_tests_dir)


def test_find_block():
    restore = JSONRPCClient.call
    JSONRPCClient.call = lambda self, cmd, num, flag: num
    client = JSONRPCClient()
    client.find_block(lambda x: x == '0x5')
    JSONRPCClient.call = restore


def test_default_host():
    default_host = '127.0.0.1'
    client = JSONRPCClient()
    assert client.transport.endpoint == 'http://{}:{}'.format(default_host, client.port)


def test_set_host():
    host = '1.1.1.1'
    default_host = '127.0.0.1'
    client = JSONRPCClient(host)
    assert client.transport.endpoint == 'http://{}:{}'.format(host, client.port)
    assert client.transport.endpoint != 'http://{}:{}'.format(default_host, client.port)

# The fixture takes much time to initialize, so the tests are grouped into one method
def test_client(test_setup):
    (test_app, rpc_tests_dir) = test_setup
    client = JSONRPCClient(port=8081)

    genesis_block_info = client.call('eth_getBlockByNumber', 'earliest', False)
    genesis_gas_limit = quantity_decoder(genesis_block_info['gasLimit'])
    assert client.default_tx_gas == (genesis_gas_limit - 1)

    sender = client.sender
    assert sender == '\xde\x0b)Vi\xa9\xfd\x93\xd5\xf2\x8d\x9e\xc8^@\xf4\xcbi{\xae'

    coinbase = client.coinbase
    assert coinbase == '\xde\x0b)Vi\xa9\xfd\x93\xd5\xf2\x8d\x9e\xc8^@\xf4\xcbi{\xae'

    blocknumber = client.blocknumber()
    assert blocknumber == 32

    nonce = client.nonce(sender)
    assert nonce == 0

    balance1 = client.balance(sender)
    assert balance1 == 5156250000000000000

    gaslimit = client.gaslimit()
    assert gaslimit == 3141592

    lastgasprice = client.lastgasprice()
    assert lastgasprice == 1

    balance2 = client.balance('\xff' * 20)
    assert balance2 == 0
    fid = client.new_filter('pending', 'pending')

    # The following tests require an account with a positive balance
    # accs = client.call('eth_accounts')
    # sender = accs[0]
    # res_est = client.eth_sendTransaction(nonce, sender, address_encoder('\xff' * 20), 1)
    # assert 'result' in res_est.keys()

    # res_call = client.eth_call(utils.encode_hex(a0), '\xff' * 20, 0)
    # assert 'result' in res_call.keys()

    # res_st = client.send_transaction(sender, address_encoder('\xff' * 20), 1)
    # assert 'result' in res_st.keys()

    # solidity_code = "contract test { function multiply(uint a) returns(uint d) {   return a * 7;   } }"

    # import ethereum._solidity
    # s = ethereum._solidity.get_solidity()
    # if s is None:
    #     pytest.xfail("solidity not installed, not tested")
    # else:
    #     abi = s.mk_full_signature(solidity_code)
    #     abic = client.new_abi_contract(abi, sender)
    #     mult = abic.multiply(11111111)
    #     assert mult == 77777777


def test_default_tx_gas_assigned():
    default_gas = 12345
    client = JSONRPCClient(default_tx_gas=default_gas)
    assert client.default_tx_gas == default_gas

