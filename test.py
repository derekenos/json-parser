
from io import BytesIO

from jsonite import (
    Parser,
    UnexpectedCharacter,
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
# Parsing helper
###############################################################################

def parse(b):
    parser = Parser(BytesIO(b))
    result = []
    for x in parser.parse():
        if isinstance(x, tuple):
            result.append((x[0], b''.join(x[1])))
        else:
            result.append(x)
    return result

###############################################################################
# Test simple scalar values
###############################################################################

def test_string():
    _assertEqual(parse(b'"test"'), [('STRING', b'test')])

def test_single_digit():
    _assertEqual(parse(b'0'), [('NUMBER', b'0')])

def test_double_digit():
    _assertEqual(parse(b'13'), [('NUMBER', b'13')])

def test_negative_digit():
    _assertEqual(parse(b'-3'), [('NUMBER', b'-3')])

def test_float():
    _assertEqual(parse(b'3.1415'), [('NUMBER', b'3.1415')])

def test_negative_float():
    _assertEqual(parse(b'-3.1415'), [('NUMBER', b'-3.1415')])

def test_null():
    _assertEqual(parse(b'null'), ['NULL'])

###############################################################################
# Test empty containers
###############################################################################

def test_empty_array():
    _assertEqual(parse(b'[]'), ['ARRAY_OPEN', 'ARRAY_CLOSE'])

def test_empty_object():
    _assertEqual(parse(b'{}'), ['OBJECT_OPEN', 'OBJECT_CLOSE'])


###############################################################################
# Test value conversions
###############################################################################

def test_string_conversion():
    _assertEqual(
        Parser.convert(None, 'STRING', (b't', b'e', b's', b't')),
        b'test'
    )

def test_single_digit_conversion():
    _assertEqual(Parser.convert(None, 'NUMBER', (b'0',)), 0)

def test_double_digit_conversion():
    _assertEqual(Parser.convert(None, 'NUMBER', (b'13',)), 13)

def test_negative_digit_conversion():
    _assertEqual(Parser.convert(None, 'NUMBER', (b'-3',)), -3)

def test_float_conversion():
    _assertEqual(Parser.convert(None, 'NUMBER', (b'3.1415',)), 3.1415)

def test_negative_float_conversion():
    _assertEqual(Parser.convert(None, 'NUMBER', (b'-3.1415',)), -3.1415)

def test_null_conversion():
    _assertEqual(Parser.convert(None, 'NULL', None), None)


###############################################################################
# Test things you know are broken
###############################################################################

def test_object_key_containing_double_quote():
    raise Skip
    parse(b'{"a_\\"good\\"_key": 0}')

def test_number_containing_multiple_decimal_points():
    raise Skip
    _assertRaises(UnexpectedCharacter, parse, b'3.14.15')

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
    from sys import stdout
    run_tests()
