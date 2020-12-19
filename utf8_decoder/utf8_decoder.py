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
        self.errors = errors
        self.disallow_nonchars = disallow_nonchars
        self.byte_num = 0
        self.first_read = True
        self.num_pending_replacement = 0
        self.stuffed_byte = None

    def __iter__(self):
        return self

    def stuff_byte(self, b):
        """Assert that self.stuffed_byte is empty and write a byte to it.
        """
        if self.stuffed_byte is not None:
            raise AssertionError
        self.stuffed_byte = b

    def read_one(self):
        """Return either a stuffed_byte or next byte from the stream.
        """
        # If self.stuffed_byte is non-None, pop and return it.
        if self.stuffed_byte is not None:
            b = self.stuffed_byte
            self.stuffed_byte = None
            return b
        # Read one byte from the stream and increment the byte counter.
        c = self.stream.read(1)
        self.byte_num += 1
        # On the first read, assert that the stream yields bytes-type values.
        if self.first_read:
            if not isinstance(c, bytes):
                raise AssertionError('UTF8Decoder requires a bytes stream')
            self.first_read = False
        # Raise StopIteration when the stream is exhausted.
        if c == b'':
            raise StopIteration
        return c

    def error(self, num_consumed_bytes=1):
        """Handle a decoding error as determined by the value of self.errors.
        """
        if self.errors == REPLACE:
            # Replace each byte in an invalid sequence with a REPLACEMENT_CHAR.
            self.num_pending_replacement += num_consumed_bytes - 1
            return REPLACEMENT_CHAR
        if self.errors == IGNORE:
            # Ignore the invalid sequence bytes and return the next character
            # in the stream.
            return next(self)
        # Assume errors = STRICT
        # Raise an exception in STRICT mode.
        raise InvalidUTF8Encoding(self.byte_num)

    def __next__(self):
        """Return the next decoded unicode character from the stream.
        """
        # If there are pending replacement chars, return one of those.
        if self.num_pending_replacement > 0:
            self.num_pending_replacement -= 1
            return REPLACEMENT_CHAR

        # Read the next, leading byte from the stream and convert it to an int.
        leading_byte = ord(self.read_one())
        # If the high bit is clear, return the single-byte char.
        if leading_byte & 0b10000000 == 0:
            return chr(leading_byte)
        # The high bit is set so the character comprises multiple bytes.
        # Determine the number of bytes and init the codepoint with the
        # leading byte payload.
        if leading_byte & 0b11100000 == 0b11000000:
            num_bytes = 2
            codepoint = (leading_byte & 0b00011111) << 6
        elif leading_byte & 0b11110000 == 0b11100000:
            num_bytes = 3
            codepoint = (leading_byte & 0b00001111) << 12
        elif leading_byte & 0b11111000 == 0b11110000:
            num_bytes = 4
            codepoint = (leading_byte & 0b00000111) << 18
        elif leading_byte & 0b11111100 == 0b11111000:
            num_bytes = 5
            codepoint = (leading_byte & 0b00000011) << 24
        elif leading_byte & 0b11111110 == 0b11111100:
            num_bytes = 6
            codepoint = (leading_byte & 0b00000001) << 30
        elif leading_byte & 0b11000000 == 0b10000000:
            # ERROR - unexpected continuation byte
            return self.error(1)
        elif leading_byte >= 0xfe:
            # ERROR - impossible leading byte
            return self.error(1)
        else:
            raise AssertionError

        # Check whether the leading byte is 0xed which is reserved for
        # UTF-16 surrogate halves - whatever those are.
        if leading_byte == 0xed:
            # ERROR - reserved leading byte
            return self.error(1)

        # Read the remaining bytes, asserting that they're valid,
        # then shifting and ORing them with codepoint to construct the final
        # value.
        bytes_remaining = num_bytes - 1
        while bytes_remaining:
            try:
                # Read the next byte from the stream and convert it to an int.
                byte = ord(self.read_one())
            except StopIteration:
                # ERROR - stream exhausted / missing continuation byte
                return self.error(num_bytes - bytes_remaining)
            # Check that this is a continuation byte.
            if byte & 0b11000000 != 0b10000000:
                # ERROR - not a continuation byte
                # Stuff the byte so that we can try it again on next read.
                self.stuff_byte(chr(byte))
                return self.error(num_bytes - bytes_remaining + 1)
            codepoint |= ((byte & 0b00111111) << ((bytes_remaining - 1) * 6))
            # Check whether the codepoint exceeds the unicode max.
            if num_bytes >= 4 and codepoint > MAX_CODEPOINT:
                # ERROR = codepoint value exceeds max
                return self.error(num_bytes - bytes_remaining + 1)
            bytes_remaining -= 1

        # Disallow overlong encodings.
        if (num_bytes == 2 and codepoint < 0x80
            or num_bytes == 3 and codepoint < 0x800
            or num_bytes == 4 and codepoint < 0x10000
            or num_bytes == 5 and codepoint < 0x200000
            or num_bytes == 6 and codepoint < 0x4000000):
            # ERROR - codepoint should have been encoded using fewer bytes
            return self.error(num_bytes)

        # Check for other invalid values. See the Codepage Layout at:
        # https://en.wikipedia.org/wiki/UTF-8#Encoding
        if (leading_byte == 0xe0 and codepoint < 0x0800
            or leading_byte == 0xf0 and codepoint < 0x10000):
            # ERROR - invalid leading byte
            return self.error(num_bytes)

        # Maybe disallow noncharacters.
        # https://www.unicode.org/versions/corrigendum9.html
        if (self.disallow_nonchars
            and (codepoint >= 0xfffe or 0xfdd0 <= codepoint <= 0xfdef)):
            # ERROR - disallowed character
            return self.error(1)

        # Return the unicode character that corresponds to the codepoint.
        return chr(codepoint)

    def read(self, num_bytes):
        return ''.join(next(self) for _ in range(num_bytes))
