
###############################################################################
# Streaming UTF-8 Decoder
###############################################################################

class InvalidUTF8Encoding(Exception):
    def __init__(self, byte_num):
        super().__init__(
            self,
            'Invalid UTF-8 encoding at byte number: {}'.format(byte_num)
        )

class UTF8Decoder:
    def __init__(self, stream):
        self.stream = stream
        self.byte_num = 0
        self.first_read = True

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

    def __next__(self):
        # See: https://en.wikipedia.org/wiki/UTF-8#Encoding
        # Read the next char.
        byte = ord(self.read_one())
        # If the high bit is clear, return the single-byte char.
        if byte & 0b10000000 == 0:
            return chr(byte)
        # The high bit is set so char comprises multiple bytes.
        # Determine the number of bytes and init the codepoint with
        # the first byte.
        if byte & 0b11100000 == 0b11000000:
            # 2-byte char.
            bytes_remaining = 1
            codepoint = (byte & 0b00011111) << 6
        elif byte & 0b11110000 == 0b11100000:
            # 3-byte char.
            bytes_remaining = 2
            codepoint = (byte & 0b00001111) << 12
        elif byte & 0b11111000 == 0b11110000:
            # 4-byte char.
            bytes_remaining = 3
            codepoint = (byte & 0b00000111) << 18
        elif byte & 0b11111100 == 0b11111000:
            # 5-byte char.
            bytes_remaining = 4
            codepoint = (byte & 0b00000011) << 24
        elif byte & 0b11111110 == 0b11111100:
            # 6-byte char.
            bytes_remaining = 5
            codepoint = (byte & 0b00000001) << 30
        else:
            raise InvalidUTF8Encoding(self.byte_num)

        # Read the remaining bytes, asserting that they're valid,
        # then shifting and ORing them with the codepoint.
        while bytes_remaining:
            try:
                byte = ord(self.read_one())
            except StopIteration:
                # Stream exhausted in the middle of a multi-byte char.
                raise InvalidUTF8Encoding(self.byte_num)
            if byte & 0b11000000 != 0b10000000:
                raise InvalidUTF8Encoding(self.byte_num)
            codepoint |= ((byte & 0b00111111) << ((bytes_remaining - 1) * 6))
            bytes_remaining -= 1
        return chr(codepoint)
