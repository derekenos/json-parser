
###############################################################################
# Exceptions
###############################################################################

class UnexpectedCharacter(Exception):
    def __init__(self, char, idx, matcher):
        super().__init__(
            'Expected {} at position {} but got {}'.format(
                getattr(matcher, '__name__', matcher), idx, char)
        )

###############################################################################
# Constants
###############################################################################

PERIOD = b'.'

# Define the Parser.container_value_context_stack values.
ARRAY_VALUE_CONTEXT = 'ARRAY_VALUE_CONTEXT'
OBJECT_VALUE_CONTEXT = 'OBJECT_VALUE_CONTEXT'

###############################################################################
# Matchers
#
# Matchers are character strings or predicate functions that are used to both
# test whether a character is as expected and serve as an indicator of to which
# class a character belongs.
###############################################################################
class Matchers:
    ARRAY_CLOSE = b']'
    ARRAY_OPEN = b'['
    EOF = b''
    FALSE_START = b'f'
    IS_NUMBER_START = lambda c: c == b'-' or c.isdigit()
    ITEM_SEP = b','
    KV_SEP = b':'
    NULL_START = b'n'
    OBJECT_CLOSE = b'}'
    OBJECT_OPEN = b'{'
    STRING_START = b'"'
    STRING_TERMINATOR = b'"'
    TRUE_START = b't'

# Set derived matchers.
# Create separate scalar / object / array matchers that use the same logic but
# exist as uniquely identifiable values.
def IS_OBJECT_KEY_START(c):
    return c == Matchers.STRING_START
Matchers.IS_OBJECT_KEY_START = IS_OBJECT_KEY_START

def IS_VALUE_START(c):
    return (
        c == Matchers.OBJECT_OPEN
        or c == Matchers.ARRAY_OPEN
        or c == Matchers.STRING_START
        or Matchers.IS_NUMBER_START(c)
        or c == Matchers.NULL_START
        or c == Matchers.TRUE_START
        or c == Matchers.FALSE_START
    )
Matchers.IS_VALUE_START = IS_VALUE_START

def IS_ARRAY_VALUE_START(c):
    return IS_VALUE_START(c)
Matchers.IS_ARRAY_VALUE_START = IS_ARRAY_VALUE_START

def IS_OBJECT_VALUE_START(c):
    return IS_VALUE_START(c)
Matchers.IS_OBJECT_VALUE_START = IS_OBJECT_VALUE_START

def IS_ARRAY_ITEM_SEP(c):
    return c == Matchers.ITEM_SEP
Matchers.IS_ARRAY_ITEM_SEP = IS_ARRAY_ITEM_SEP

def IS_OBJECT_ITEM_SEP(c):
    return c == Matchers.ITEM_SEP
Matchers.IS_OBJECT_ITEM_SEP = IS_OBJECT_ITEM_SEP

###############################################################################
# Events
#
# Events represent things that we expect to encounter, and want to act in
# response to, while parsing a JSON string.
###############################################################################

class Events:
    ARRAY_CLOSE = 'ARRAY_CLOSE'
    ARRAY_OPEN = 'ARRAY_OPEN'
    ARRAY_VALUE_FALSE = 'ARRAY_VALUE_FALSE'
    ARRAY_VALUE_NULL = 'ARRAY_VALUE_NULL'
    ARRAY_VALUE_NUMBER = 'ARRAY_VALUE_NUMBER'
    ARRAY_VALUE_STRING = 'ARRAY_VALUE_STRING'
    ARRAY_VALUE_TRUE = 'ARRAY_VALUE_TRUE'
    EOF = 'END_OF_FILE'
    FALSE = 'FALSE'
    NULL = 'NULL'
    NUMBER = 'NUMBER'
    OBJECT_CLOSE = 'OBJECT_CLOSE'
    OBJECT_KEY = 'OBJECT_KEY'
    OBJECT_OPEN = 'OBJECT_OPEN'
    OBJECT_VALUE_FALSE = 'OBJECT_VALUE_FALSE'
    OBJECT_VALUE_NULL = 'OBJECT_VALUE_NULL'
    OBJECT_VALUE_NUMBER = 'OBJECT_VALUE_NUMBER'
    OBJECT_VALUE_STRING = 'OBJECT_VALUE_STRING'
    OBJECT_VALUE_TRUE = 'OBJECT_VALUE_TRUE'
    STRING = 'STRING'
    TRUE = 'TRUE'

###############################################################################
# Helpers
###############################################################################

is_digit = lambda c: c.isdigit()
is_not_string_terminator = lambda c: c != Matchers.STRING_TERMINATOR
split_event_value = lambda x: (x if isinstance(x, tuple) else (x, None))

###############################################################################
# Parser
###############################################################################

class Parser:
    def __init__(self, stream):
        self.stream = stream
        # Store the current stream char number for reporting the position of
        # unexpected characters.
        self.char_num = 0
        # Store a place to stuff a character that we read from the stream but
        # need to put back for the next read. next_char() will pop this value
        # before reading again from the stream, thus providing a sort of 1-byte
        # lookahead mechanism.
        self.stuffed_char = None
        # Define a stack to store the Matcher that we expect to match the next
        # character from next_nonspace_char(). A single matcher element is
        # considered to be manadatory and parsing will fail if the matcher
        # fails. A 2-element tuple can be provided with the first element as an
        # optional matcher and the second as a mandatory:
        #   i.e. ( <optional-match>, <mandatory-matcher> )
        self.expect_stack = [ Matchers.EOF, Matchers.IS_VALUE_START ]

        # Define a stack for storing the context of the current container-type
        # (i.e. object value or array value) that we're currently parsing. This
        # is used in order to yield the appropriate event on array/object close.
        self.container_value_context_stack = []

    def next_char(self):
        # If there's a stuffed nonspace char, return that and do not increment
        # char_num.
        if self.stuffed_char is not None:
            c = self.stuffed_char
            self.stuffed_char = None
            return c
        # Return the next byte from the stream and increment char_num.
        c = self.stream.read(1)
        self.char_num += 1
        return c

    def next_nonspace_char(self):
        # Advance the stream past the next non-whitespace character and return
        # the character, or Matchers.EOF if the stream has been exhausted.
        while True:
            c = self.next_char()
            if c == Matchers.EOF:
                return Matchers.EOF
            if not c.isspace():
                return c

    def stuff_char(self, c):
        # Assert that stuffed_char is empty and write the character to it.
        if self.stuffed_char is not None:
            raise AssertionError
        self.stuffed_char = c

    def expect(self, matcher):
        # Assert that the next non-whitespace charater is as expected and
        # return both the character and the matcher that matched it.
        c = self.next_nonspace_char()
        # The expect_stack contains elements that are either a single matcher
        # or a tuple of matches in the format:
        #  ( <optional-matcher>, <mandatory-matcher> )
        # Iterate through all tuple-type matchers.
        while isinstance(matcher, tuple):
            optional, matcher = matcher
            # If the matcher doesn't look like a string (i.e. no 'decode'),
            # assume it's a function and call it, other test again the string.
            if ((not hasattr(optional, 'decode') and optional(c))
                or c == optional):
                # An optional matcher matched, so push the mandatory one back
                # onto the expect_stack.
                self.expect_stack.append(matcher)
                # Return the character and matched optional matcher.
                return c, optional
        # Either no optional matches were specified or none matched, so attempt
        # to match against the mandatory matcher.
        if (not hasattr(matcher, 'decode') and matcher(c)) or c == matcher:
            # Return the character and matched mandatory matcher.
            return c, matcher
        # The mandatory matcher failed, so raise UnexpectedCharacter.
        raise UnexpectedCharacter(c, self.char_num, matcher)

    def yield_while(self, pred):
        # Yield characters from the stream until testing them against the
        # specified predicate function returns False.
        while True:
            # Read the next character from the stream.
            c = self.next_char()
            # Check whether the character satisfies the predicate.
            if not pred(c):
                # The predicate has not been satisfied so stuff the last-read
                # character back and return.
                self.stuff_char(c)
                return
            # Yield the character.
            yield c

    def with_drain(self, event, gen):
        # Yield the specified (event, gen) pair and afterward, if necessary,
        # consume the generator to ensure that the stream read pointer is
        # advanced as expected.
        yield event, gen
        if gen is not None:
            for _ in gen:
                pass

    def parse_string(self):
        # Yield characters from the stream up until the next string terminator
        # (i.e. '"') character.
        yield from self.yield_while(is_not_string_terminator)
        # Expect a string terminator to follow.
        self.expect(Matchers.STRING_TERMINATOR)

    def parse_number(self):
        # Yield characters from the stream up until the next non-number char.
        # Expect the first character to be a negative sign or digit.
        yield self.expect(lambda c: c == b'-' or c.isdigit())[0]
        # Expect one or more digits.
        yield from self.yield_while(is_digit)
        # Check to see if the next char is a decimal point.
        c = self.next_char()
        if c != PERIOD:
            # Not a decimal point so stuff it back and return.
            self.stuff_char(c)
            return
        # It is a decimal point.
        yield c
        # Expect the next character to be a digit.
        yield self.expect(is_digit)[0]
        # Yield any remaining digits.
        yield from self.yield_while(is_digit)

    def parse(self):
        while True:
            for event_value in self.parse_next():
                if event_value is None:
                    return
                yield event_value

    def parse_next(self):
        c, match = self.expect(self.expect_stack.pop())

        if match == Matchers.EOF:
            # Char is an empty string which indicates that the input stream has
            # been exhausted.
            # Yield None to indicate that end-of-file has been reached.
            yield None
            return

        if c == Matchers.ARRAY_OPEN:
            # Char is an array initiator (i.e. '[')
            yield Events.ARRAY_OPEN
            # Expect an array value, item separator, or array terminator to
            # follow.
            self.expect_stack.append(
                (Matchers.IS_ARRAY_VALUE_START, Matchers.ARRAY_CLOSE)
            )
            # If the context is array or object, push the appropriate value
            # onto the container_value_context_stack.
            if match == Matchers.IS_ARRAY_VALUE_START:
                self.container_value_context_stack.append(ARRAY_VALUE_CONTEXT)
            elif match == Matchers.IS_OBJECT_VALUE_START:
                self.container_value_context_stack.append(OBJECT_VALUE_CONTEXT)
            return

        if c == Matchers.OBJECT_OPEN:
            # Char is an object initiator (i.e. '{')
            yield Events.OBJECT_OPEN
            # Expect an object key, item separator, or object terminator to
            # follow.
            self.expect_stack.append(
                (Matchers.IS_OBJECT_KEY_START, Matchers.OBJECT_CLOSE)
            )
            # If the context is array or object, push the appropriate value
            # onto the container_value_context_stack.
            if match == Matchers.IS_ARRAY_VALUE_START:
                self.container_value_context_stack.append(ARRAY_VALUE_CONTEXT)
            elif match == Matchers.IS_OBJECT_VALUE_START:
                self.container_value_context_stack.append(OBJECT_VALUE_CONTEXT)
            return

        if match == Matchers.ARRAY_CLOSE:
            # Char is an array terminator (i.e. ']')
            yield Events.ARRAY_CLOSE
            # If container_value_context_stack is non-empty, pop the last
            # context.
            if self.container_value_context_stack:
                context = self.container_value_context_stack.pop()
                # Expect whatever's appropriate for the context.
                item_sep_matcher = (
                    Matchers.IS_ARRAY_ITEM_SEP if context == ARRAY_VALUE_CONTEXT
                    else Matchers.IS_OBJECT_ITEM_SEP
                )
                self.expect_stack.append(
                    (item_sep_matcher, self.expect_stack.pop())
                )
            return

        if match == Matchers.OBJECT_CLOSE:
            # Char is an object terminator (i.e. '}').
            yield Events.OBJECT_CLOSE
            # If container_value_context_stack is non-empty, pop the last
            # context.
            if self.container_value_context_stack:
                context = self.container_value_context_stack.pop()
                # Expect whatever's appropriate for the context.
                item_sep_matcher = (
                    Matchers.IS_ARRAY_ITEM_SEP if context == ARRAY_VALUE_CONTEXT
                    else Matchers.IS_OBJECT_ITEM_SEP
                )
                self.expect_stack.append(
                    (item_sep_matcher, self.expect_stack.pop())
                )
            return

        if match == Matchers.IS_OBJECT_KEY_START:
            # Char is the expected object key's opening double-qoute.
            # Yield the object key string.
            yield from self.with_drain(Events.OBJECT_KEY, self.parse_string())
            # Expect a object key/value separator (i.e. ':') to follow.
            self.expect_stack.append(Matchers.KV_SEP)
            return

        if match == Matchers.KV_SEP:
            # Char is an object key / value separator (i.e. ':')
            # Expect an object value (e.g. string, number, null) to follow.
            self.expect_stack.append(Matchers.IS_OBJECT_VALUE_START)
            return

        if match == Matchers.IS_OBJECT_ITEM_SEP:
            # Char is an item separator (i.e. ',') in a post-object-value
            # context.
            # Expect an object value, item separator (thus accomodating
            # unlimited trailing commas), or object terminator to follow.
            self.expect_stack.append(
                (Matchers.IS_OBJECT_KEY_START, self.expect_stack.pop())
            )
            return

        if match == Matchers.IS_ARRAY_ITEM_SEP:
            # Char is an item separator (i.e. ',') in a post-array-value
            # context.
            # Expect an array value, item separator (thus accomodating
            # unlimited trailing commas), or array terminator to follow.
            self.expect_stack.append(
                (Matchers.IS_ARRAY_VALUE_START, self.expect_stack.pop())
            )
            return

        # Having exhausted the above clauses, we find ourselves dealing with a
        # new scalar value, either as a standalone value or in the context of an
        # array or object value. Assert that this is so.
        if match not in (
                Matchers.IS_VALUE_START,
                Matchers.IS_OBJECT_VALUE_START,
                Matchers.IS_ARRAY_VALUE_START
            ):
            raise AssertionError(c, match, self.char_num)

        if c == Matchers.STRING_START:
            # Char is a string initiator (i.e. '"')
            # Yield the event along with a string value parser/generator.
            if match == Matchers.IS_OBJECT_VALUE_START:
                event = Events.OBJECT_VALUE_STRING
            elif match == Matchers.IS_ARRAY_VALUE_START:
                event = Events.ARRAY_VALUE_STRING
            else:
                event = Events.STRING
            yield from self.with_drain(event, self.parse_string())

        elif Matchers.IS_NUMBER_START(c):
            # Char is a number initiator (i.e. '-' or a digit)
            # Yield the event along with a number value parser/generator.
            if match == Matchers.IS_OBJECT_VALUE_START:
                event = Events.OBJECT_VALUE_NUMBER
            elif match == Matchers.IS_ARRAY_VALUE_START:
                event = Events.ARRAY_VALUE_NUMBER
            else:
                event = Events.NUMBER
            # parse_number() is going to need this first character, so stuff it
            # back in.
            self.stuff_char(c)
            yield from self.with_drain(event, self.parse_number())

        elif c == Matchers.NULL_START:
            # Char is a null initiator (i.e. 'n')
            # Expect the next 3 chars to be 'ull' and yield the event.
            self.expect(b'u')
            self.expect(b'l')
            self.expect(b'l')
            if match == Matchers.IS_OBJECT_VALUE_START:
                yield Events.OBJECT_VALUE_NULL
            elif match == Matchers.IS_ARRAY_VALUE_START:
                yield Events.ARRAY_VALUE_NULL
            else:
                yield Events.NULL

        elif c == Matchers.TRUE_START:
            # Char is a true initiator (i.e. 't')
            # Expect the next 3 chars to be 'rue' and yield the event.
            self.expect(b'r')
            self.expect(b'u')
            self.expect(b'e')
            if match == Matchers.IS_OBJECT_VALUE_START:
                yield Events.OBJECT_VALUE_TRUE
            elif match == Matchers.IS_ARRAY_VALUE_START:
                yield Events.ARRAY_VALUE_TRUE
            else:
                yield Events.TRUE

        elif c == Matchers.FALSE_START:
            # Char is a false initiator (i.e. 'f')
            # Expect the next 4 chars to be 'alse' and yield the event.
            self.expect(b'a')
            self.expect(b'l')
            self.expect(b's')
            self.expect(b'e')
            if match == Matchers.IS_OBJECT_VALUE_START:
                yield Events.OBJECT_VALUE_FALSE
            elif match == Matchers.IS_ARRAY_VALUE_START:
                yield Events.ARRAY_VALUE_FALSE
            else:
                yield Events.FALSE

        else:
            raise NotImplementedError(c)

        if match == Matchers.IS_ARRAY_VALUE_START:
            # We just yielded an array value.
            # Expect an array item separator or array terminator to follow.
            self.expect_stack.append(
                (Matchers.IS_ARRAY_ITEM_SEP, self.expect_stack.pop())
            )
        elif match == Matchers.IS_OBJECT_VALUE_START:
            # We just yielded an object value.
            # Expect an object item separator or object terminator to follow.
            self.expect_stack.append(
                (Matchers.IS_OBJECT_ITEM_SEP, self.expect_stack.pop())
            )

    def convert(self, event, value):
        # Convert a parsed value to a Python type.
        if (event == Events.ARRAY_VALUE_NULL
            or event == Events.OBJECT_VALUE_NULL
            or event == Events.NULL):
            return None
        if (event == Events.ARRAY_VALUE_TRUE
            or event == Events.OBJECT_VALUE_TRUE
            or event == Events.TRUE):
            return True
        if (event == Events.ARRAY_VALUE_FALSE
            or event == Events.OBJECT_VALUE_FALSE
            or event == Events.FALSE):
            return False
        if (event == Events.ARRAY_VALUE_STRING
            or event == Events.OBJECT_VALUE_STRING
            or event == Events.STRING
            or event == Events.OBJECT_KEY):
            return b''.join(value)
        if (event == Events.ARRAY_VALUE_NUMBER
            or event == Events.OBJECT_VALUE_NUMBER
            or event == Events.NUMBER):
            s = b''.join(value)
            # Cast to either float or int based on presence of a decimal place.
            return float(s) if PERIOD in s else int(s)
        raise NotImplementedError(event, value)

    def yield_paths(self, paths):
        # Yield ( <path>, <value-generator> ) tuples for all specified paths
        # that exist in the data.
        #
        # paths must be an iterable of lists of byte strings and integers in
        # the format:
        #   [ b'<object-key>', <array-index>, ... ]
        # Example:
        #   [ b'people', 0, b'first_name' ]
        #
        # Track the indexes of the paths in paths to be yielded so that we can
        # abort as soon as all requested paths have been yielded.
        unyielded_path_idxs = set(range(len(paths)))
        # Define the current path stack.
        path = []
        parse_gen = self.parse()
        for event_value in parse_gen:
            event, value = split_event_value(event_value)
            if event == Events.OBJECT_OPEN:
                # An object has opened.
                # If the current path node is an array index, increment it.
                if path and isinstance(path[-1], int):
                    path[-1] += 1
                # For each unyielded path, attempt to match it against the
                # current path. If it matches, yield the event and remove the
                # path index from the unyielded set.
                yielded = False
                for i in unyielded_path_idxs:
                    if path == paths[i]:
                        # Reset the parser state such that the next call will
                        # re-yield this same OBJECT_OPEN to make load() work.
                        yield path, self.load(parse_gen)
                        unyielded_path_idxs.remove(i)
                        yielded = True
                        break
                if not yielded:
                    # If this container was not already load()ed and yielded,
                    # Append an empty object indicator to the current path, to
                    # be overwritten by the next parsed key.
                    path.append(PERIOD)
                continue

            elif event == Events.OBJECT_CLOSE:
                # The object has closed.
                # Pop it from the current path.
                path.pop()
                continue

            elif event == Events.ARRAY_OPEN:
                # An array has opened.
                # If the current path node is an array index, increment it.
                if path and isinstance(path[-1], int):
                    path[-1] += 1
                # For each unyielded path, attempt to match it against the
                # current path. If it matches, yield the event and remove the
                # path index from the unyielded set.
                yielded = False
                for i in unyielded_path_idxs:
                    if path == paths[i]:
                        # Reset the parser state such that the next call will
                        # re-yield this same ARRAY_OPEN to make load() work.
                        yield path, self.load(parse_gen)
                        unyielded_path_idxs.remove(i)
                        yielded = True
                        break
                if not yielded:
                    # If this container was not already load()ed and yielded,
                    # Append an array index of -1 to the current path, to be
                    # increment on the next parsed array value.
                    path.append(-1)
                continue

            elif event == Events.ARRAY_CLOSE:
                # The array has closed.
                # Pop it from the current path.
                path.pop()
                continue

            elif event == Events.OBJECT_KEY:
                # We parsed an object key.
                # Overwrite the current path node with the key value.
                path[-1] = self.convert(Events.OBJECT_KEY, value)

            elif (event == Events.ARRAY_VALUE_STRING
                  or event == Events.ARRAY_VALUE_NUMBER
                  or event == Events.ARRAY_VALUE_NULL
                  or event == Events.ARRAY_VALUE_TRUE
                  or event == Events.ARRAY_VALUE_FALSE):
                # We parsed an array value.
                # Increment the current path node array index.
                path[-1] += 1
                # For each unyielded path, attempt to match it against the
                # current path. If it matches, yield the event and remove the
                # path index from the unyielded set.
                for i in unyielded_path_idxs:
                    if path == paths[i]:
                        yield path, self.convert(event, value)
                        unyielded_path_idxs.remove(i)
                        break

            elif (event == Events.OBJECT_VALUE_STRING
                  or event == Events.OBJECT_VALUE_NUMBER
                  or event == Events.OBJECT_VALUE_NULL
                  or event == Events.OBJECT_VALUE_TRUE
                  or event == Events.OBJECT_VALUE_FALSE):
                # We parsed an object value.
                # For each unyielded path, attempt to match it against the
                # current path. If it matches, yield the event and remove the
                # path index from the unyielded set.
                for i in unyielded_path_idxs:
                    if path == paths[i]:
                        yield path, self.convert(event, value)
                        unyielded_path_idxs.remove(i)
                        break

            # Abort if all of the requested paths have been yielded.
            if len(unyielded_path_idxs) == 0:
                return

    def load(self, parse_gen=None):
        # If parse_gen is specified, parse the single next value in the stream,
        # otherwise parse the entire stream, and return a single Python object,
        # similar to the built-in json.load() / json.loads() behavior.
        if parse_gen is None:
            parse_gen = self.parse()

        # Initialize the value based on the first read.
        event, value = split_event_value(next(parse_gen))

        # If it's a single scalar value, convert and return it.
        if (event == Events.STRING
            or event == Events.NUMBER
            or event == Events.NULL
            or event == Events.TRUE
            or event == Events.FALSE):
            return self.convert(event, value)

        # Create an initial, root object to represent the initial container.
        if (event == Events.OBJECT_OPEN or event == Events.OBJECT_KEY):
            root = {}
        elif (event == Events.ARRAY_OPEN or event.startswith('ARRAY_VALUE_')):
            root = []
        else:
            raise NotImplementedError(event)

        # Create a stack to store the hierarchy of open container objects.
        container_stack = []
        # Define the current container object. Building the final object will
        # entail in-place mutation of whatever object 'container' points to.
        container = root
        # Define a place to store the last-parsed object key.
        key = None

        def open_container(_container):
            nonlocal container
            # Attach the new container to the one that's currently open.
            if type(container) is list:
                container.append(_container)
            else:
                container[key] = _container
            # Push the currently-open container onto the stack.
            container_stack.append(container)
            # Set the new container as the current.
            container = _container

        def close_container():
            # Close the current container object and reopen the last one.
            nonlocal container
            container = container_stack.pop()

        # If we're already in the context of an array or object item, use
        # it to init the container state.
        if event.startswith('ARRAY_VALUE_'):
            container.append(self.convert(event, value))
        elif event == Events.OBJECT_KEY:
            key = self.convert(event, value)

        # Start parsing.
        for event_value in parse_gen:
            event, value = split_event_value(event_value)
            if event == Events.ARRAY_OPEN:
                # An array just opened so open a new list container.
                open_container([])
            elif event == Events.OBJECT_OPEN:
                # An array just opened so open a new object container.
                open_container({})
            elif event == Events.ARRAY_CLOSE or event == Events.OBJECT_CLOSE:
                # The current array or object container just closed.
                # If there are no open containers, stop parsing.
                if len(container_stack) == 0:
                    break
                # Close the current container and reopen the last one.
                close_container()
            elif (event == Events.ARRAY_VALUE_STRING
                  or event == Events.ARRAY_VALUE_NUMBER
                  or event == Events.ARRAY_VALUE_NULL
                  or event == Events.ARRAY_VALUE_TRUE
                  or event == Events.ARRAY_VALUE_FALSE):
                # We just parsed an array value.
                # Append it to the current list container.
                container.append(self.convert(event, value))
            elif event == Events.OBJECT_KEY:
                # We just parsed an object key. Record it.
                key = self.convert(event, value)
            elif (event == Events.OBJECT_VALUE_STRING
                  or event == Events.OBJECT_VALUE_NUMBER
                  or event == Events.OBJECT_VALUE_NULL
                  or event == Events.OBJECT_VALUE_TRUE
                  or event == Events.OBJECT_VALUE_FALSE):
                # We just parsed an object value.
                # Use the last-parsed object key to create an item in the
                # current object container.
                container[key] = self.convert(event, value)

        # Return the mutated root object.
        return root

###############################################################################
# CLI
###############################################################################

def convert_dot_path_to_yield_path(path):
    # Convert the dot-delimited --path argument to a path list required by
    # Parser.yield_paths().
    final_path = []
    i = 0
    splits = [int(seg) if seg.isdigit() else seg.encode('utf-8')
              for seg in path.split('.')]
    splits_len = len(splits)
    while i < splits_len:
        seg = splits[i]
        if seg != b'':
            final_path.append(seg)
        else:
            # An empty seg indicates the presence of a double-dot which is used
            # to indicate an escaped segment value dot.
            if final_path:
                final_path[-1] += b'.' + splits[i + 1]
            else:
                final_path.append(b'.' + splits[i + 1])
            i += 1
        i += 1
    return final_path

def convert_yielded_key_to_dot_path(key):
    return '.'.join(str(seg) if isinstance(seg, int)
                    else seg.decode('utf-8') for seg in key)

if __name__ == '__main__':
    import argparse
    from io import BytesIO
    from json import dumps
    from pprint import pprint

    arg_parser = argparse.ArgumentParser()

    g = arg_parser.add_mutually_exclusive_group()
    g.add_argument('--file', type=argparse.FileType('rb'))
    g.add_argument('--string', type=str)

    arg_parser.add_argument('--action', choices=('load', 'parse'),
                            default="load")
    arg_parser.add_argument('--path', type=str, action='append',
                            help='Dot-delimited path specifier with dots in keys escaped as a double-dot')

    args = arg_parser.parse_args()

    if args.string:
        args.file = BytesIO(args.string.encode('utf-8'))

    if args.path and args.action != 'load':
        arg_parser.error('Please specify --action=load when using --path')

    parser = Parser(args.file)

    if args.action == 'load':
        if not args.path:
            # Load it all and pretty-print the result.
            pprint(parser.load())
        else:
            # Load only the specified paths.
            result = {}
            # Convert the dot-delimited paths to path segments lists as
            # required by Parser.yield_paths().
            paths = list(map(convert_dot_path_to_yield_path, args.path))
            for key, value in parser.yield_paths(paths):
                # Conver the yielded key back to a dot path.
                key = convert_yielded_key_to_dot_path(key)
                if isinstance(value, bytes):
                    result[key] = value.decode('utf-8')
                else:
                    result[key] = value
            # Print the result as JSON.
            print(dumps(result, indent=2))

    elif args.action == 'parse':
        for event_value in parser.parse():
            event, value = split_event_value(event_value)
            if value is not None:
                value = parser.convert(event, value)
            print(event, value)
