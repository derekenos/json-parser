
from io import BytesIO
from sys import stdout

import utf8_decoder
from utf8_decoder import (
    InvalidUTF8Encoding,
    UTF8Decoder,
)

###############################################################################
# Testing helpers
###############################################################################

class Skip(Exception): pass
class DidNotRaise(Exception): pass

def _assertEqual(result, expected):
    if result != expected:
        raise AssertionError(
            f'Expected ({repr(expected)}), got ({repr(result)})'
        )

def _assertRaises(exc, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc:
        pass
    else:
        raise DidNotRaise

###############################################################################
# Tests
###############################################################################

def test_stress_test():
    # Test processing the UTF-8 decoder capability and stress test from:
    # https://www.cl.cam.ac.uk/~mgk25/ucs/examples/UTF-8-test.txt
    input_fh = open('test_data/UTF-8-test.txt', 'rb')
    expected_fh = open('test_data/UTF-8-test.txt.expected', 'r', encoding='utf-8')
    decoder = UTF8Decoder(input_fh, errors=utf8_decoder.REPLACE)
    for c in decoder:
        _assertEqual(c, expected_fh.read(1))

def test_i_can_eat_glass():
    # Test processing the "I CAN EAT GLASS" section at:
    # http://kermitproject.org/utf8.html#glass
    original_fh = open('test_data/i_can_eat_glass.txt', 'r', encoding='utf-8')
    decoder_fh = open('test_data/i_can_eat_glass.txt', 'rb')
    decoder = UTF8Decoder(decoder_fh, errors=utf8_decoder.REPLACE)
    for c in decoder:
        _assertEqual(c, original_fh.read(1))

###############################################################################

def run_tests():
    # Run all global functions with a name that starts with "test_".
    fn_cls = type(run_tests)
    for k, v in sorted(globals().items()):
        if k.startswith('test_') and isinstance(v, fn_cls):
            test_name = v.__name__[5:]
            stdout.write('testing {}'.format(test_name))
            stdout.flush()
            try:
                v()
            except AssertionError as e:
                stdout.write(' - FAILED\n')
                raise
            except Skip:
                stdout.write(' - SKIPPED\n')
            else:
                stdout.write(' - ok\n')
            finally:
                stdout.flush()

if __name__ == '__main__':
    run_tests()
