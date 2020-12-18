
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
    fh = open('UTF-8-test.txt', 'rb')
    decoder = UTF8Decoder(fh, errors=utf8_decoder.REPLACE)
    for c in decoder:
        stdout.write(c)


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
