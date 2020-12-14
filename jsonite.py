
from collections import deque

class UnexpectedCharacter(Exception):
    def __init__(self, c, i):
        super().__init__(
            'Unexpected character "{}" at position {}'.format(c, i)
        )

is_value_open = lambda c: \
    c == '{' or c == '[' or c == '"' or c.isdigit() or c == '-' or c == 'n'

class Parser:
    def __init__(self, stream):
        self.stream = stream
        self.char_num = 0

    def parse(self):
        for event, gen in self.parse_value():
            print(event, tuple(gen or ()))

    def next_char(self):
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

    def expect(self, expected):
        # Assert that the next non-whitespace char is as expected and return
        # it.
        c = self.next_nonspace_char()
        if ((hasattr(expected, '__call__') and expected(c))
            or c == expected):
            return c
        raise UnexpectedCharacter(c, self.char_num)

    def yield_while(self, pred):
        escaped = 0
        while True:
            c = self.next_char()
            if c == '\\':
                escaped ^= 1
            elif escaped == 0 and not pred(c):
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
        yield from self.yield_while(lambda c: c != '"')

    def parse_key(self):
        self.expect('"')
        yield from self.yield_while(lambda c: c != '"')

    def parse_key_value(self):
        yield from self.with_drain('KEY', self.parse_key())
        self.expect(':')
        yield from self.with_drain('VALUE', self.parse_value())

    def parse_key_values(self):
        yield from self.parse_key_value()
        c = self.next_nonspace_char()
        while c == ',':
            yield from self.parse_key_value()
            c = self.next_nonspace_char()
        if c != '}':
            raise UnexpectedCharacter(c, self.char_num)

    def parse_object(self):
        yield 'OBJ_OPEN', None
        yield from self.parse_key_values()
        yield 'OBJ_CLOSE', None

    def parse_array_item(self):
        yield from self.with_drain('ARR_ITEM', self.parse_value())

    def parse_array_items(self):
        yield from self.parse_array_item()
        c = self.next_nonspace_char()
        while c == ',':
            yield from self.parse_array_item()
            c = self.next_nonspace_char()
        if c != ']':
            raise UnexpectedCharacter(c, self.char_num)

    def parse_array(self):
        yield 'ARR_OPEN', None
        yield from self.parse_array_items()
        yield 'ARR_CLOSE', None

    def parse_number(self):
        yield from self.yield_while(lambda c: c.isdigit() or c == '.')

    def parse_value(self, c=None):
        c = self.expect(is_value_open)
        if c == '{':
            yield from self.parse_object()
        elif c == '[':
            yield from self.parse_array()
        elif c == '"':
            yield from self.parse_string()
        elif c.isdigit() or c == '-':
            yield c
            yield from self.parse_number()

# TEST
if __name__ == '__main__':
    fh = open("test_inputs/api_weather_gov_points.json", "r", encoding="utf-8")
    Parser(fh).parse()
