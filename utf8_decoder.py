
###############################################################################
# Streaming UTF-8 Decoder
###############################################################################

class InvalidUTF8Encoding(Exception):
    def __init__(self, byte_num):
        super().__init__(
            self,
            'Invalid UTF-8 encoding at char: {}'.format(char_num)
        )

class UTF8Decoder:
    def __init__(self, stream):
        self.stream = stream
        self.byte_num = 0
        self.checked_type = False

    def read_one(self):
        self.byte_num += 1
        c = self.stream.read(1)
        if not self.checked_type:
            if not isinstance(c, bytes):
                raise AssertionError('UTF8Decoder requires a bytes stream')
        if c == b'':
            raise StopIteration
        return c

    def __iter__(self):
        return self

    def __next__(self):
        # See: https://en.wikipedia.org/wiki/UTF-8#Encoding
        # Read the next char.
        byte = ord(self.read_one())
        # If the high bit is clear, return the single-byte char.
        if byte & 0x80 == 0:
            return chr(byte)
        # The high bit is set so char comprises multiple bytes.
        # Determine the number of bytes and do the read.
        if byte & 0x11100000 == 0x11000000:
            # 2-byte char.
            bytes_remaining = 1
        elif byte & 0x11110000 == 0x11100000:
            # 3-byte char.
            bytes_remaining = 2
        else:
            bytes_remaining = 3
        # Init the code point value with the appropriately shifted
        # first byte.
        codepoint = (byte & 0x00011111) << (6 * bytes_remaining)
        # Read the remaining bytes, asserting that they're valid,
        # then shifting and ORing them with the codepoint.
        while bytes_remaining:
            byte = self.read_one()
            if byte & 0b11000000 != 0b10000000:
                raise InvalidUTF8Encoding(self.char_num)
            codepoint |= (byte & 0b00111111) << (bytes_remaining - 1)
            bytes_remaining -= 1
        return chr(codepoint)
