"""
Streaming UTF-8 Decoder
See: https://en.wikipedia.org/wiki/UTF-8#Encoding
"""

###############################################################################
# Constants
###############################################################################

REPLACEMENT_CHAR = '\ufffd'
STRICT, REPLACE, IGNORE = 0, 1, 2
MAX_CODEPOINT = 0x10ffff

###############################################################################
# Exceptions
###############################################################################

class InvalidUTF8Encoding(Exception):
    def __init__(self, byte_num):
        super().__init__(
            self,
            'Invalid UTF-8 encoding at byte number: {}'.format(byte_num)
        )

###############################################################################
# UTF8Decoder Class
###############################################################################

class UTF8Decoder:
    def __init__(self, stream, errors=STRICT, disallow_nonchars=True):
        self.stream = stream
        self.byte_num = 0
        self.first_read = True
        self.errors = errors
        self.num_pending_replacement = 0
        self.disallow_nonchars = disallow_nonchars

    def read_one(self):
        c = self.stream.read(1)
        self.byte_num += 1

        if self.first_read:
            if not isinstance(c, bytes):
                raise AssertionError('UTF8Decoder requires a bytes stream')
            self.first_read = False

        if c == b'':
            raise StopIteration
        return c

    def __iter__(self):
        return self

    def error(self, num_consumed_bytes=1):
        if self.errors == STRICT:
            raise InvalidUTF8Encoding(self.byte_num)
        elif self.errors == REPLACE:
            self.num_pending_replacement += num_consumed_bytes - 1
            return REPLACEMENT_CHAR
        else:
            return next(self)

    def __next__(self):
        # If there are pending replacement chars, return one of those.
        if self.num_pending_replacement > 0:
            self.num_pending_replacement -= 1
            return REPLACEMENT_CHAR

        # Read the next char.
        leading_byte = ord(self.read_one())
        # If the high bit is clear, return the single-byte char.
        if leading_byte & 0b10000000 == 0:
            return chr(leading_byte)
        # The high bit is set so char comprises multiple bytes.
        # Determine the number of bytes and init the codepoint with
        # the first byte.
        if leading_byte & 0b11100000 == 0b11000000:
            # 2-byte char.
            num_bytes = 2
            codepoint = (leading_byte & 0b00011111) << 6
        elif leading_byte & 0b11110000 == 0b11100000:
            # 3-byte char.
            num_bytes = 3
            codepoint = (leading_byte & 0b00001111) << 12
        elif leading_byte & 0b11111000 == 0b11110000:
            # 4-byte char.
            num_bytes = 4
            codepoint = (leading_byte & 0b00000111) << 18
        elif leading_byte & 0b11111100 == 0b11111000:
            # 5-byte char.
            num_bytes = 5
            codepoint = (leading_byte & 0b00000011) << 24
        elif leading_byte & 0b11111110 == 0b11111100:
            # 6-byte char.
            num_bytes = 6
            codepoint = (leading_byte & 0b00000001) << 30
        elif leading_byte & 0b11000000 == 0b10000000:
            # Unexpected continuation.
            return self.error(1)
        else:
            # Some other unexpected condition.
            return self.error(1)

        # Check whether the leading byte is 0xed which is reserved for
        # UTF-16 surrogate halves - whatever those are.
        if leading_byte == 0xed:
            return self.error(1)

        # Read the remaining bytes, asserting that they're valid,
        # then shifting and ORing them with the codepoint.
        bytes_remaining = num_bytes - 1
        while bytes_remaining:
            try:
                byte = ord(self.read_one())
            except StopIteration:
                # Stream exhausted in the middle of a multi-byte char.
                return self.error(num_bytes - bytes_remaining)
            # Check that this is a continuation byte.
            if byte & 0b11000000 != 0b10000000:
                return self.error(num_bytes - bytes_remaining + 1)
            codepoint |= ((byte & 0b00111111) << ((bytes_remaining - 1) * 6))
            # Check whether the codepoint exceeds the unicode max.
            if num_bytes >= 4 and codepoint > MAX_CODEPOINT:
                return self.error(num_bytes - bytes_remaining + 1)
            bytes_remaining -= 1

        # Disallow overlong encodings.
        if (num_bytes == 2 and codepoint < 0x80
            or num_bytes == 3 and codepoint < 0x800
            or num_bytes == 4 and codepoint < 0x10000
            or num_bytes == 5 and codepoint < 0x200000
            or num_bytes == 6 and codepoint < 0x4000000):
            return self.error(num_bytes)

        # Check for other invalid values. See the Codepage Layout at:
        # https://en.wikipedia.org/wiki/UTF-8#Encoding
        if (leading_byte == 0xe0 and codepoint < 0x0800
            or leading_byte == 0xf0 and codepoint < 0x10000):
            return self.error(num_bytes)

        # Maybe disallow noncharacters.
        # https://www.unicode.org/versions/corrigendum9.html
        if (self.disallow_nonchars
            and (codepoint >= 0xfffe or 0xfdd0 <= codepoint <= 0xfdef)):
            # Replace disallowed non-chars with a single byte.
            return self.error(1)

        return chr(codepoint)

    def read(self, num_bytes):
        return ''.join(next(self) for _ in range(num_bytes))
