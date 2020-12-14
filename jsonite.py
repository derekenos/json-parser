
from collections import deque

class UnexpectedCharacter(Exception):
    def __init__(self, c, i):
        super().__init__(
            'Unexpected character "{}" at position {}'.format(c, i)
        )

OBJECT_OPEN = '{'
ARRAY_OPEN = '['
STRING_START = '"'
STRING_TERMINATOR = '"'
NULL_START = 'n'
IS_NUMBER_START = lambda c: c == '-' or c.isdigit()
OBJECT_KEY_START = STRING_START
OBJECT_CLOSE = '}'
ARRAY_CLOSE = ']'
KV_SEP = ':'
ITEM_SEP = ','
EOF = None
IS_NO_MATCH = lambda c: False

IS_VALUE_START = lambda c: (
    c == OBJECT_OPEN
    or c == ARRAY_OPEN
    or c == STRING_START
    or IS_NUMBER_START(c)
    or c == NULL_START
)

IS_OBJECT_VALUE_START = lambda c: (
    c == OBJECT_OPEN
    or c == ARRAY_OPEN
    or c == STRING_START
    or IS_NUMBER_START(c)
    or c == NULL_START
)

IS_ARRAY_VALUE_START = lambda c: (
    c == OBJECT_OPEN
    or c == ARRAY_OPEN
    or c == STRING_START
    or IS_NUMBER_START(c)
    or c == NULL_START
)

IS_NEXT_OBJECT_KEY_START = lambda c: c == ITEM_SEP or c == OBJECT_KEY_START
IS_NEXT_ARRAY_VALUE_START = lambda c: c == ITEM_SEP or IS_ARRAY_VALUE_START(c)

is_not_string_terminator = lambda c: c != STRING_TERMINATOR
is_number_char = lambda c: c.isdigit() or c == '.'

class Parser:
    def __init__(self, stream):
        self.stream = stream
        self.char_num = 0
        self.stuffed_char = None

    def next_char(self):
        # If there's a stuffed nonspace char, return that.
        if self.stuffed_char is not None:
            c = self.stuffed_char
            self.stuffed_char = None
            return c
        # Return the next byte from the stream.
        c = self.stream.read(1)
        # Increment the char counter.
        self.char_num += 1
        return c

    def next_nonspace_char(self):
        # Advance the stream past the next non-whitespace character and return
        # the character, or None if the stream has been exhausted.
        while True:
            c = self.next_char()
            if c == '':
                # End of stream has been reached, return None.
                return None
            if not c.isspace():
                return c

    def stuff_char(self, c):
        if self.stuffed_char is not None:
            raise AssertionError
        self.stuffed_char = c

    def expect(self, expected):
        # Assert that the next non-whitespace char is as expected and return
        # it.
        c = self.next_nonspace_char()
        while isinstance(expected, tuple):
            optional, expected = expected
            if ((hasattr(optional, '__call__') and optional(c))
                or c == optional):
                self.expect_stack.append(expected)
                return c, optional
        if ((hasattr(expected, '__call__') and expected(c))
            or c == expected):
            return c, expected
        raise UnexpectedCharacter(c, self.char_num)

    def yield_while(self, pred):
        escaped = 0
        while True:
            c = self.next_char()
            if c == '\\':
                escaped ^= 1
            elif escaped == 0 and not pred(c):
                self.stuff_char(c)
                return
            yield c

    def with_drain(self, event, gen):
        # Yield the specified (event, gen) pair and afterward, if gen is an
        # unconsumed generator, drain it.
        char_num = self.char_num
        yield event, gen
        if self.char_num == char_num and gen is not None:
            # The generator was not consumed, so drain it.
            for _ in gen:
                pass

    def parse_string(self):
        yield from self.yield_while(is_not_string_terminator)
        self.expect(STRING_TERMINATOR)

    def parse_number(self, first_char):
        yield first_char
        yield from self.yield_while(is_number_char)

    def parse(self):
        self.expect_stack = deque(( EOF, IS_VALUE_START, ), 32)
        while True:
            for x in self.parse_next():
                if x is None:
                    return
                if isinstance(x, tuple):
                    t, v = x
                    if t == 'OBJECT_KEY' or t.endswith('STRING'):
                        v = ''.join(v)
                    print(t, '"{}"'.format(v))
                else:
                    print(x)

    def parse_next(self):
        c, match = self.expect(self.expect_stack.pop())

        if match == EOF:
            yield None
            return

        if match == OBJECT_CLOSE:
            yield 'OBJECT_CLOSE'
            return

        if match == OBJECT_KEY_START:
            yield from self.with_drain('OBJECT_KEY', self.parse_string())
            self.expect_stack.append(KV_SEP)
            return

        if match == KV_SEP:
            self.expect_stack.append(IS_OBJECT_VALUE_START)
            return

        if match == ARRAY_CLOSE:
            yield 'ARRAY_CLOSE'
            return

        if match == IS_NEXT_OBJECT_KEY_START:
            self.expect_stack.append(
                (
                    OBJECT_KEY_START,
                    (IS_NEXT_OBJECT_KEY_START, self.expect_stack.pop())
                )
            )
            return

        if match == IS_NEXT_ARRAY_VALUE_START:
            self.expect_stack.append(
                (
                    IS_ARRAY_VALUE_START,
                    (IS_NEXT_ARRAY_VALUE_START, self.expect_stack.pop())
                )
            )
            return

        # Assert that this is some sort of value match.
        if match not in (IS_VALUE_START, IS_OBJECT_VALUE_START,
                         IS_ARRAY_VALUE_START):
            raise AssertionError(c, match, self.char_num)

        if c == OBJECT_OPEN:
            yield 'OBJECT_OPEN'
            self.expect_stack.append(
                (
                    OBJECT_KEY_START,
                    (IS_NEXT_OBJECT_KEY_START, OBJECT_CLOSE)
                )
            )
            return

        if c == ARRAY_OPEN:
            yield 'ARRAY_OPEN'
            self.expect_stack.append(
                (
                    IS_ARRAY_VALUE_START,
                    (IS_NEXT_ARRAY_VALUE_START, ARRAY_CLOSE)
                )
            )
            return

        value_context = ''
        if match == IS_OBJECT_VALUE_START:
            value_context = 'OBJECT_VALUE_'
        elif match == IS_ARRAY_VALUE_START:
            value_context = 'ARRAY_VALUE_'

        if c == STRING_START:
            yield from self.with_drain(
                '{}STRING'.format(value_context), self.parse_string()
            )
        elif IS_NUMBER_START(c):
            yield from self.with_drain(
                '{}NUMBER'.format(value_context), self.parse_number(c)
            )
        else:
            raise NotImplementedError(c)

        if match == IS_ARRAY_VALUE_START:
            self.expect_stack.append(
                (IS_NEXT_ARRAY_VALUE_START, self.expect_stack.pop())
            )
        elif match == IS_OBJECT_VALUE_START:
            self.expect_stack.append(
                (IS_NEXT_OBJECT_KEY_START, self.expect_stack.pop())
            )


# TEST
if __name__ == '__main__':
    fh = open("test_inputs/api_weather_gov_points.json", "r", encoding="utf-8")
    Parser(fh).parse()
