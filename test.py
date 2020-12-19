# -*- coding: utf-8 -*-

from io import BytesIO
from sys import stdout

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

def _assertIsInstance(v, cls):
    if not isinstance(v, cls):
        raise AssertionError(
            f'Value ({repr(value)}) is not of type ({repr(cls)})'
        )

_assertIsInt = lambda v: _assertIsInstance(v, int)
_assertIsFloat = lambda v: _assertIsInstance(v, float)


###############################################################################
# Parsing helper
###############################################################################

def parse(b):
    parser = Parser(BytesIO(b))
    result = []
    for x in parser.parse():
        if isinstance(x, tuple):
            result.append((x[0], ''.join(x[1])))
        else:
            result.append(x)
    return result

###############################################################################
# Test simple scalar values
###############################################################################

def test_string():
    _assertEqual(parse(b'"test"'), [('STRING', 'test')])

def test_nonascii_string():
    _assertEqual(parse('"κόσμε"'.encode('utf-8')), [('STRING', 'κόσμε')])

def test_single_digit():
    _assertEqual(parse(b'0'), [('NUMBER', '0')])

def test_double_digit():
    _assertEqual(parse(b'13'), [('NUMBER', '13')])

def test_negative_digit():
    _assertEqual(parse(b'-3'), [('NUMBER', '-3')])

def test_float():
    _assertEqual(parse(b'3.1415'), [('NUMBER', '3.1415')])

def test_negative_float():
    _assertEqual(parse(b'-3.1415'), [('NUMBER', '-3.1415')])

def test_null():
    _assertEqual(parse(b'null'), ['NULL'])

def test_true():
    _assertEqual(parse(b'true'), ['TRUE'])

def test_false():
    _assertEqual(parse(b'false'), ['FALSE'])


###############################################################################
# Test invalid scalar values
###############################################################################

def test_number_containing_multiple_numeric_chars():
    _assertRaises(UnexpectedCharacter, parse, b'-3.14.-1-5')


###############################################################################
# Test empty containers
###############################################################################

def test_empty_array():
    _assertEqual(parse(b'[]'), ['ARRAY_OPEN', 'ARRAY_CLOSE'])

def test_empty_object():
    _assertEqual(parse(b'{}'), ['OBJECT_OPEN', 'OBJECT_CLOSE'])


###############################################################################
# Test Arrays
###############################################################################

def test_single_element_array():
    _assertEqual(
        parse(b'[1]'),
        ['ARRAY_OPEN', ('ARRAY_VALUE_NUMBER', '1'), 'ARRAY_CLOSE']
    )

def test_single_element_array_with_trailing_comma():
    _assertEqual(
        parse(b'[1]'),
        ['ARRAY_OPEN', ('ARRAY_VALUE_NUMBER', '1'), 'ARRAY_CLOSE']
    )

###############################################################################
# Test Objects
###############################################################################

def test_single_item_object():
    _assertEqual(
        parse(b'{"a": 0}'),
        [
            'OBJECT_OPEN',
            ('OBJECT_KEY', 'a'),
            ('OBJECT_VALUE_NUMBER', '0'),
            'OBJECT_CLOSE'
        ]
    )

def test_single_item_object_with_trailing_comma():
    _assertEqual(
        parse(b'{"a": 0,}'),
        [
            'OBJECT_OPEN',
            ('OBJECT_KEY', 'a'),
            ('OBJECT_VALUE_NUMBER', '0'),
            'OBJECT_CLOSE'
        ]
    )

###############################################################################
# Test value conversions
###############################################################################

def test_string_conversion():
    _assertEqual(
        Parser.convert(None, 'STRING', ('t', 'e', 's', 't')),
        'test'
    )

def test_single_digit_conversion():
    v = Parser.convert(None, 'NUMBER', ('0',))
    _assertIsInt(v)
    _assertEqual(v, 0)

def test_double_digit_conversion():
    v = Parser.convert(None, 'NUMBER', ('13',))
    _assertIsInt(v)
    _assertEqual(v, 13)

def test_negative_digit_conversion():
    v = Parser.convert(None, 'NUMBER', ('-3',))
    _assertIsInt(v)
    _assertEqual(v, -3)

def test_float_conversion():
    v = Parser.convert(None, 'NUMBER', ('3.1415',))
    _assertIsFloat(v)
    _assertEqual(v, 3.1415)

def test_negative_float_conversion():
    v = Parser.convert(None, 'NUMBER', ('-3.1415',))
    _assertIsFloat(v)
    _assertEqual(v, -3.1415)

def test_null_conversion():
    _assertEqual(Parser.convert(None, 'NULL', None), None)

def test_true_conversion():
    _assertEqual(Parser.convert(None, 'TRUE', None), True)

def test_false_conversion():
    _assertEqual(Parser.convert(None, 'FALSE', None), False)


###############################################################################
# Test yield paths
###############################################################################

def test_yield_paths():
    fh = open('test_data/api_weather_gov_points.json', 'rb')
    parser = Parser(fh)
    path = [
        'properties',
        'relativeLocation',
        'geometry',
        'coordinates',
        1
    ]
    _assertEqual(list(parser.yield_paths((path,))), [(path, 41.50324)])


###############################################################################
# Test things you know are broken
###############################################################################

def test_object_key_containing_double_quote():
    raise Skip
    parse(b'{"a_\\"good\\"_key": 0}')

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
