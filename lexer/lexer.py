from lexer.token import Token
from lexer.token_list import TokenList
from compiler_exception import CompilerException

class Lexer:
    def __init__(self, path):
        self.path = path
        self.file = open(self.path, "r", encoding="utf-8")
        self.symbol = self.file.read(1)

        self.reserved = {"array", "asm", "begin", "case", "const", "constructor", "destructor", "do",
                         "downto", "else", "end", "exports", "file", "for", "function", "goto", "if", "implementation",
                         "in", "inherited", "inline", "interface", "label", "library", "nil", "object",
                         "of", "packed", "procedure", "program", "record", "repeat", "set", "shl", "shr",
                         "string", "then", "to", "type", "unit", "until", "uses", "var", "while", "with", "xor"}
        # predefined - предописанные слова
        self.predefined = {"abs", "arctan", "boolean", "char", "cos", "dispose", "eof", "eoln", "exp",
                           "false", "get", "input", "integer", "ln", "maxint", "new", "output",
                           "pack", "page", "pred", "put", "read", "readln", "real", "reset", "rewrite",
                           "sin", "sqr", "sqrt", "succ", "text", "true", "unpack", "write", "writeln"}
        self.base_of_numbers = {16: '$', 8: '&', 2: '%'}
        self.space_symbols = {'', ' ', '\n', '\t', '\0', '\r'}
        self.operations = {'+', '-', '*', '/', '=', '<', '>', "div", "mod", "not", "and", "or", "ord", "chr", "sizeof", "pi",
                           "int", "trunc", "round", "frac", "odd"}
        self.operations_arr = {'+', '-', '*', '/'}
        self.operations_bool = {'>', '<'}
        self.assignments = {":=", "+=", "-=", "*=", "/="}
        self.separators = {'.', ',', ':', ';', '(', ')', '[', ']', ".."}

        self.state = TokenList.any
        self.line, self.col = 1, 1
        self.buf, self.unget, self.coordinates = "", "", ""

    def getNextLexem(self):
        self.clearBuf()
        while self.symbol or self.buf:
            if self.state == TokenList.any:
                if self.symbol in self.space_symbols:
                    if self.symbol == "\n":
                        self.newLine()
                    self.getSymbol()
                elif self.symbol.isalpha():
                    self.keepSymbol(state=TokenList.identifier, keep_coordinates=True)
                elif self.symbol.isdigit():
                    self.keepSymbol(state=TokenList.integer, keep_coordinates=True)
                elif self.symbol == '$':
                    self.keepSymbol(state=TokenList.integer_16, keep_coordinates=True)
                elif self.symbol == '&':
                    self.keepSymbol(state=TokenList.integer_8, keep_coordinates=True)
                elif self.symbol == '%':
                    self.keepSymbol(state=TokenList.integer_2, keep_coordinates=True)
                elif self.symbol == "'":
                    self.keepSymbol(state=TokenList.string, keep_coordinates=True)
                elif self.symbol in self.operations:
                    self.keepSymbol(state=TokenList.operation, keep_coordinates=True)
                elif self.symbol == '{':
                    self.keepSymbol(state=TokenList.comment, keep_coordinates=True)
                elif self.symbol in self.separators:
                    self.keepSymbol(state=TokenList.separator, keep_coordinates=True)
                else:
                    self.keepSymbol(state=TokenList.error, keep_coordinates=True)

            elif self.state == TokenList.identifier:
                if self.symbol.isdigit() or self.symbol.isalpha() or self.symbol == "_":
                    self.keepSymbol()
                else:
                    self.state = TokenList.any
                    type_lexem = TokenList.identifier.value
                    if self.buf.lower() in self.reserved:
                        type_lexem = TokenList.reserved.value
                    elif self.buf.lower() in self.predefined:
                        type_lexem = TokenList.predefined.value
                    elif self.buf.lower() in self.operations:
                        type_lexem = TokenList.operation.value
                    return self.returnedToken(self.coordinates, type_lexem, self.buf, self.buf)

            elif self.state == TokenList.integer:
                if self.symbol.isdigit():
                    self.keepSymbol()
                elif self.symbol == ".":
                    self.state = TokenList.real
                    self.keepSymbol()
                elif self.symbol.lower() == "e":
                    self.state = TokenList.real_e
                    self.keepSymbol()
                elif self.symbol.isalpha():
                    self.state = TokenList.error
                    self.keepSymbol()
                else:
                    self.state = TokenList.any
                    if int(self.buf) <= 2147483647:
                        return self.returnedToken(self.coordinates, TokenList.integer.value, self.buf, int(self.buf))
                    else:
                        self.informError(f"Range check error while evaluating constants: {self.buf}")

            elif self.state == TokenList.integer_16:
                if self.symbol.isdigit():
                    self.keepSymbol()
                elif self.symbol.isalpha():
                    if 'a' <= self.symbol.lower() <= 'f':
                        self.keepSymbol()
                    else:
                        self.state = TokenList.error
                        self.keepSymbol()
                else:
                    return self.tokenIntOtherFormats()

            elif self.state == TokenList.integer_8:
                if self.symbol.isdigit():
                    if int(self.symbol) <= 7:
                        self.keepSymbol()
                    else:
                        self.state = TokenList.error
                        self.keepSymbol()
                else:
                    return self.tokenIntOtherFormats()

            elif self.state == TokenList.integer_2:
                if self.symbol.isdigit():
                    if int(self.symbol) <= 1:
                        self.keepSymbol()
                    else:
                        self.state = TokenList.error
                        self.keepSymbol()
                else:
                    return self.tokenIntOtherFormats()

            elif self.state == TokenList.real:
                if self.symbol.isdigit():
                    self.keepSymbol()
                elif self.symbol.lower() == "e":
                    if self.buf[len(self.buf) - 1] != '.':
                        self.state = TokenList.real_e
                        self.keepSymbol()
                    else:
                        self.state = TokenList.error
                        self.keepSymbol()
                elif self.buf[len(self.buf) - 1] == '.' and self.symbol == '.':
                    self.state = TokenList.any
                    self.buf = self.buf[:len(self.buf) - 1]
                    self.setUnget(".")
                    return self.returnedToken(self.coordinates, TokenList.integer.value, self.buf, int(self.buf))
                else:
                    if self.buf[len(self.buf) - 1] != '.':
                        self.state = TokenList.any
                        if 2.9e-39 <= float(self.buf) <= 1.7e38:
                            return self.returnedToken(self.coordinates, TokenList.real.value, self.buf, float(self.buf))
                        self.informError(f"Range check error while evaluating constants: {self.buf}")
                    self.state = TokenList.error
                    self.keepSymbol()

            elif self.state == TokenList.real_e:
                if self.symbol == '+' or self.symbol == '-' or self.symbol.isdigit():
                    self.state = TokenList.real_degree if self.symbol.isdigit() \
                        else TokenList.real_plus_minus
                    self.keepSymbol()
                else:
                    self.state = TokenList.error
                    self.keepSymbol()

            elif self.state == TokenList.real_plus_minus:
                if self.symbol.isdigit():
                    self.state = TokenList.real_degree
                    self.addBuf()
                    self.getSymbol()
                else:
                    self.state = TokenList.error
                    self.keepSymbol()

            elif self.state == TokenList.real_degree:
                if self.symbol.isdigit():
                    self.keepSymbol()
                else:
                    self.state = TokenList.any
                    if 2.9e-39 <= float(self.buf) <= 1.7e38:
                        return self.returnedToken(self.coordinates, TokenList.real.value, self.buf, float(self.buf))
                    else:
                        self.informError(f"Range check error while evaluating constants ({self.buf})")

            elif self.state == TokenList.string:
                if self.symbol == '' or self.symbol == '\n':
                    end_of = "file" if self.symbol == '' else "line"
                    self.informError(f'End of {end_of} was encountered, but "\'" was expected')
                elif self.symbol != "'":
                    self.keepSymbol()
                else:
                    self.state = TokenList.any
                    self.keepSymbol()
                    return self.returnedToken(self.coordinates, TokenList.string.value, self.buf, self.buf)

            elif self.state == TokenList.operation:
                if (self.buf in self.operations_arr or self.buf in self.operations_bool) and self.symbol == '=' \
                        or self.buf + self.symbol == "**":
                    self.keepSymbol()
                elif self.buf + self.symbol == "//":
                    self.keepSymbol()
                    self.state = TokenList.comment
                else:
                    self.state = TokenList.any
                    type_lexem = TokenList.assignment.value if self.buf in self.assignments else TokenList.operation.value
                    return self.returnedToken(self.coordinates, type_lexem, self.buf, self.buf)

            elif self.state == TokenList.separator:
                self.state = TokenList.any
                type_lexem = TokenList.separator.value
                if self.buf + self.symbol == ".." or self.buf + self.symbol == ":=":
                    self.addBuf()
                    if self.buf == ":=":
                        type_lexem = TokenList.assignment.value
                    self.getSymbol()
                    return self.returnedToken(self.coordinates, type_lexem, self.buf, self.buf)
                elif self.buf + self.symbol == "(*":
                    self.addBuf()
                    self.state = TokenList.comment
                elif self.buf == '.':
                    if self.symbol in self.space_symbols:
                        return self.returnedToken(self.coordinates, type_lexem, self.buf, self.buf)
                    else:
                        self.state = TokenList.error
                        self.keepSymbol()
                else:
                    return self.returnedToken(self.coordinates, type_lexem, self.buf, self.buf)

            elif self.state == TokenList.comment:
                if self.symbol == '$' and len(self.buf) == 1:
                    self.state = TokenList.directive
                    self.keepSymbol()
                elif self.buf[0] == '{' and self.symbol == '}' or self.buf[:2] == "(*" and \
                        self.buf[len(self.buf)-1] + self.symbol == "*)":
                    self.state = TokenList.any
                    self.clearBuf()
                    self.getSymbol()
                elif self.buf[:2] == "//" and (not self.symbol or self.symbol == "\n"):
                    self.state = TokenList.any
                    self.clearBuf()
                    self.newLine()
                    self.getSymbol()
                elif self.symbol == '\n':
                    self.addBuf()
                    self.newLine()
                    self.getSymbol()
                elif not self.symbol:
                    self.buf = self.buf.encode("unicode_escape").decode("utf-8")
                    self.col -= 1
                    self.keepCoordinates()
                    self.informError('End of file was encountered, but end of comment was expected')
                else:
                    self.keepSymbol()

            elif self.state == TokenList.directive:
                if self.symbol == "\n":
                    self.addBuf()
                    self.newLine()
                    self.getSymbol()
                elif self.symbol == "}":
                    self.state = TokenList.any
                    self.keepSymbol()
                    return self.returnedToken(self.coordinates, TokenList.directive.value, self.buf, self.buf)
                else:
                    self.keepSymbol()

            elif self.state == TokenList.error:
                if self.symbol in self.space_symbols or self.symbol in self.separators:
                    self.informError(f'Syntax error: "{self.buf}"')
                self.keepSymbol()
        return self.returnedToken(f"{self.line}:{self.col}", "EOF", "End of file", "End of file")


    def getCurrentLexem(self):
        return self.token

    def informError(self, text):
        text = f'{self.coordinates}        ' + text
        raise CompilerException(text)

    def keepSymbol(self, state=None, keep_coordinates=False):
        if state:
            self.state = state
        if keep_coordinates:
            self.keepCoordinates()
        self.addBuf()
        self.getSymbol()

    def keepCoordinates(self):
        self.coordinates = f"{self.line}:{self.col}"

    def getSymbol(self):
        if self.unget:
            self.symbol = self.unget
            self.unget = ""
        else:
            self.symbol = self.file.read(1)
        self.col += 1

    def newLine(self):
        self.line += 1
        self.col = 0

    def setUnget(self, value):
        self.unget = value
        self.col -= 1

    def clearBuf(self):
        self.buf = ""

    def addBuf(self):
        self.buf += self.symbol

    def returnedToken(self, coordinates, type, code, value):
        self.token = Token(coordinates, type, code, value)
        return self.token

    def stringToNumber(self, s):
        if len(s) == 1:
            self.informError("Syntax error")
        if s[0] in self.base_of_numbers.values():
            base = self.getKey(self.base_of_numbers, s[0])
            s = s[1:]
        return int(s, base)

    def getKey(self, d, value):
        for k, v in d.items():
            if v == value:
                return k

    def tokenIntOtherFormats(self):
        self.state = TokenList.any
        value = self.stringToNumber(self.buf)
        if -2147483648 <= value <= 2147483647:
            return self.returnedToken(self.coordinates, TokenList.integer.value, self.buf, value)
        else:
            self.informError(f"Range check error while evaluating constants: {self.buf}")
