# -*- coding: utf-8 -*-

import json
from io import BytesIO

from testy import (
    Skip,
    assertEqual,
    assertIsFloat,
    assertIsInt,
    assertAsyncRaises,
    assertTrue,
    cli,
)

from __init__ import (
    Parser,
    UnexpectedCharacter,
)

###############################################################################
# Parsing helper
###############################################################################

async def parse(b):
    parser = Parser(BytesIO(b))
    result = []
    async for event, value_gen in parser.parse():
        if value_gen is not None:
            result.append((event, b''.join(value_gen)))
        else:
            result.append(event)
    return result

###############################################################################
# Test simple scalar values
###############################################################################

async def test_string():
    assertEqual(await parse(b'"test"'), [('STRING', b'test')])

async def test_nonascii_string():
    assertEqual(
        await parse('"κόσμε"'.encode('utf-8')),
        [('STRING', 'κόσμε'.encode('utf-8'))]
    )

async def test_single_digit():
    assertEqual(await parse(b'0'), [('NUMBER', b'0')])

async def test_double_digit():
    assertEqual(await parse(b'13'), [('NUMBER', b'13')])

async def test_negative_digit():
    assertEqual(await parse(b'-3'), [('NUMBER', b'-3')])

async def test_float():
    assertEqual(await parse(b'3.1415'), [('NUMBER', b'3.1415')])

async def test_negative_float():
    assertEqual(await parse(b'-3.1415'), [('NUMBER', b'-3.1415')])

async def test_null():
    assertEqual(await parse(b'null'), ['NULL'])

async def test_true():
    assertEqual(await parse(b'true'), ['TRUE'])

async def test_false():
    assertEqual(await parse(b'false'), ['FALSE'])


###############################################################################
# Test invalid scalar values
###############################################################################

async def test_number_containing_multiple_numeric_chars():
    await assertAsyncRaises(UnexpectedCharacter, parse, b'-3.14.-1-5')


###############################################################################
# Test empty containers
###############################################################################

async def test_empty_array():
    assertEqual(await parse(b'[]'), ['ARRAY_OPEN', 'ARRAY_CLOSE'])

async def test_empty_object():
    assertEqual(await parse(b'{}'), ['OBJECT_OPEN', 'OBJECT_CLOSE'])


###############################################################################
# Test Arrays
###############################################################################

async def test_single_element_array():
    assertEqual(
        await parse(b'[1]'),
        ['ARRAY_OPEN', ('ARRAY_VALUE_NUMBER', b'1'), 'ARRAY_CLOSE']
    )

async def test_single_element_array_with_trailing_comma():
    assertEqual(
        await parse(b'[1]'),
        ['ARRAY_OPEN', ('ARRAY_VALUE_NUMBER', b'1'), 'ARRAY_CLOSE']
    )

###############################################################################
# Test Objects
###############################################################################

async def test_single_item_object():
    assertEqual(
        await parse(b'{"a": 0}'),
        [
            'OBJECT_OPEN',
            ('OBJECT_KEY', b'a'),
            'KV_SEP',
            ('OBJECT_VALUE_NUMBER', b'0'),
            'OBJECT_CLOSE'
        ]
    )

async def test_single_item_object_with_trailing_comma():
    assertEqual(
        await parse(b'{"a": 0,}'),
        [
            'OBJECT_OPEN',
            ('OBJECT_KEY', b'a'),
            'KV_SEP',
            ('OBJECT_VALUE_NUMBER', b'0'),
            'OBJECT_ITEM_SEP',
            'OBJECT_CLOSE'
        ]
    )

###############################################################################
# Test value conversions
###############################################################################

async def test_string_conversion():
    assertEqual(
        Parser(b'').convert('STRING', (b't', b'e', b's', b't')),
        'test'
    )

async def test_single_digit_conversion():
    v = Parser(b'').convert('NUMBER', (b'0',))
    assertIsInt(v)
    assertEqual(v, 0)

async def test_double_digit_conversion():
    v = Parser(b'').convert('NUMBER', (b'13',))
    assertIsInt(v)
    assertEqual(v, 13)

async def test_negative_digit_conversion():
    v = Parser(b'').convert('NUMBER', (b'-3',))
    assertIsInt(v)
    assertEqual(v, -3)

async def test_float_conversion():
    v = Parser(b'').convert('NUMBER', (b'3.1415',))
    assertIsFloat(v)
    assertEqual(v, 3.1415)

async def test_negative_float_conversion():
    v = Parser(b'').convert('NUMBER', (b'-3.1415',))
    assertIsFloat(v)
    assertEqual(v, -3.1415)

async def test_null_conversion():
    assertEqual(Parser(b'').convert('NULL', None), None)

async def test_true_conversion():
    assertEqual(Parser(b'').convert('TRUE', None), True)

async def test_false_conversion():
    assertEqual(Parser(b'').convert('FALSE', None), False)


###############################################################################
# Test yield paths
###############################################################################

async def test_yield_paths():
    fh = open('test_data/api_weather_gov_points.json', 'rb')
    parser = Parser(fh)
    path = [
        'properties',
        'relativeLocation',
        'geometry',
        'coordinates',
        1
    ]
    paths_gen = parser.yield_paths((path,))
    assertEqual([x async for x in paths_gen], [(path, 41.50324)])

###############################################################################
# Test invalid things
###############################################################################

async def test_string_containing_control_code():
    # Check that characters 0x00 - 0x1f are not allowed.
    for x in range(32):
        char = chr(x).encode('utf-8')
        exc = await assertAsyncRaises(
            UnexpectedCharacter,
            parse,
            b'"' + char + b'"'
        )
        # Test the exception string to ensure that it was raised for the
        # expected reason.
        assertTrue(str(exc).endswith(f'got {repr(char)}'))
    # Check that characters the next character, 0x20, is allowed.
    assertEqual(
        await parse(f'"{chr(32)}"'.encode("utf-8")),
        [('STRING', b'\x20')]
    )

###############################################################################
# Test things you know are broken
###############################################################################

async def test_object_key_containing_double_quote_TODO():
    await parse(b'{"a_\\"good\\"_key": 0}')

async def test_escaped_unicode_chars_TODO():
    assertEqual(
        await parse(b'"1 \\u0032 \\u0033 4 \\u0035"'),
        [('STRING', '1 2 3 4 5')]
    )

async def test_string_containing_unicode_control_code_TODO():
    await assertAsyncRaises(UnexpectedCharacter, parse, b'"\\u0000"')

###############################################################################
# Test parity with built-in Python json.load()
###############################################################################

async def test_parity_with_builtin_json_load_github_repos():
    _open = lambda: open('test_data/api_github_com_users_github_repos.json',
                         'rb')
    assertEqual(
        json.load(_open()),
        await Parser(_open()).load()
    )

async def test_parity_with_builtin_json_load_weather_data():
    _open = lambda: open('test_data/api_weather_gov_points.json', 'rb')
    assertEqual(
        json.load(_open()),
        await Parser(_open()).load()
    )


if __name__ == '__main__':
    cli(globals())
