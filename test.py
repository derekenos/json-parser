# -*- coding: utf-8 -*-

from io import BytesIO

from testy import (
    Skip,
    assertEqual,
    assertRaises,
    assertIsInt,
    assertIsFloat,
    cli,
)

from __init__ import (
    Parser,
    UnexpectedCharacter,
)


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
    assertEqual(parse(b'"test"'), [('STRING', 'test')])

def test_nonascii_string():
    assertEqual(parse('"κόσμε"'.encode('utf-8')), [('STRING', 'κόσμε')])

def test_single_digit():
    assertEqual(parse(b'0'), [('NUMBER', '0')])

def test_double_digit():
    assertEqual(parse(b'13'), [('NUMBER', '13')])

def test_negative_digit():
    assertEqual(parse(b'-3'), [('NUMBER', '-3')])

def test_float():
    assertEqual(parse(b'3.1415'), [('NUMBER', '3.1415')])

def test_negative_float():
    assertEqual(parse(b'-3.1415'), [('NUMBER', '-3.1415')])

def test_null():
    assertEqual(parse(b'null'), ['NULL'])

def test_true():
    assertEqual(parse(b'true'), ['TRUE'])

def test_false():
    assertEqual(parse(b'false'), ['FALSE'])


###############################################################################
# Test invalid scalar values
###############################################################################

def test_number_containing_multiple_numeric_chars():
    assertRaises(UnexpectedCharacter, parse, b'-3.14.-1-5')


###############################################################################
# Test empty containers
###############################################################################

def test_empty_array():
    assertEqual(parse(b'[]'), ['ARRAY_OPEN', 'ARRAY_CLOSE'])

def test_empty_object():
    assertEqual(parse(b'{}'), ['OBJECT_OPEN', 'OBJECT_CLOSE'])


###############################################################################
# Test Arrays
###############################################################################

def test_single_element_array():
    assertEqual(
        parse(b'[1]'),
        ['ARRAY_OPEN', ('ARRAY_VALUE_NUMBER', '1'), 'ARRAY_CLOSE']
    )

def test_single_element_array_with_trailing_comma():
    assertEqual(
        parse(b'[1]'),
        ['ARRAY_OPEN', ('ARRAY_VALUE_NUMBER', '1'), 'ARRAY_CLOSE']
    )

###############################################################################
# Test Objects
###############################################################################

def test_single_item_object():
    assertEqual(
        parse(b'{"a": 0}'),
        [
            'OBJECT_OPEN',
            ('OBJECT_KEY', 'a'),
            ('OBJECT_VALUE_NUMBER', '0'),
            'OBJECT_CLOSE'
        ]
    )

def test_single_item_object_with_trailing_comma():
    assertEqual(
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
    assertEqual(
        Parser.convert(None, 'STRING', ('t', 'e', 's', 't')),
        'test'
    )

def test_single_digit_conversion():
    v = Parser.convert(None, 'NUMBER', ('0',))
    assertIsInt(v)
    assertEqual(v, 0)

def test_double_digit_conversion():
    v = Parser.convert(None, 'NUMBER', ('13',))
    assertIsInt(v)
    assertEqual(v, 13)

def test_negative_digit_conversion():
    v = Parser.convert(None, 'NUMBER', ('-3',))
    assertIsInt(v)
    assertEqual(v, -3)

def test_float_conversion():
    v = Parser.convert(None, 'NUMBER', ('3.1415',))
    assertIsFloat(v)
    assertEqual(v, 3.1415)

def test_negative_float_conversion():
    v = Parser.convert(None, 'NUMBER', ('-3.1415',))
    assertIsFloat(v)
    assertEqual(v, -3.1415)

def test_null_conversion():
    assertEqual(Parser.convert(None, 'NULL', None), None)

def test_true_conversion():
    assertEqual(Parser.convert(None, 'TRUE', None), True)

def test_false_conversion():
    assertEqual(Parser.convert(None, 'FALSE', None), False)


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
    assertEqual(list(parser.yield_paths((path,))), [(path, 41.50324)])


###############################################################################
# Test things you know are broken
###############################################################################

def test_object_key_containing_double_quote():
    parse(b'{"a_\\"good\\"_key": 0}')

def test_escaped_unicode_chars():
    raise Skip
    assertEqual(
        parse(b'"1 \\u0032 \\u0033 4 \\u0035"'),
        [('STRING', '1 2 3 4 5')]
    )

def test_string_containing_control_code():
    # Check that characters 0x00 - 0x1f are not allowed.
    for x in range(32):
        char = chr(x)
        exc = assertRaises(
            UnexpectedCharacter,
            parse,
            f'"{char}"'.encode("utf-8")
        )
        # Test the exception string to ensure that it was raised for the
        # expected reason.
        assertEqual(str(exc)[-5:], f'got {char}')
    # Check that characters the next character, 0x20, is allowed.
    assertEqual(
        parse(f'"{chr(32)}"'.encode("utf-8")),
        [('STRING', '\x20')]
    )

def test_string_containing_unicode_control_code():
    assertRaises(UnexpectedCharacter, parse, b'"\\u0000"')


###############################################################################

if __name__ == '__main__':
    cli(globals())
