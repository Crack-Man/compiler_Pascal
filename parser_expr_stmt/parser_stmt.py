from lexer.token_list import TokenList
from parser_expr_stmt.parser_expr import ParserExpr
from compiler_exception import CompilerException
from enum import Enum
from parser_expr_stmt.expr_node.str_node import StrNode

from parser_expr_stmt.stmt_node.block_stmt_node import BlockStmtNode
from parser_expr_stmt.stmt_node.func_stmt_node import FuncStmtNode
from parser_expr_stmt.stmt_node.while_stmt_node import WhileStmtNode
from parser_expr_stmt.stmt_node.repeat_stmt_node import UntilStmtNode
from parser_expr_stmt.stmt_node.for_stmt_node import ForStmtNode
from parser_expr_stmt.stmt_node.if_stmt_node import IfStmtNode
from parser_expr_stmt.stmt_node.assign_stmt_node import AssignStmtNode
from parser_expr_stmt.stmt_node.arr_stmt_node import ArrStmtNode
from parser_expr_stmt.stmt_node.var_stmt_node import VarStmtNode
from parser_expr_stmt.expr_node.params_node import ParamsNode
from parser_expr_stmt.stmt_node.read_stmt_node import ReadStmtNode
from parser_expr_stmt.stmt_node.write_stmt_node import WriteStmtNode
from parser_expr_stmt.stmt_node.null_stmt_node import NullStmtNode


from parser_expr_stmt.expr_node.arr_index_node import ArrIndexNode
from parser_expr_stmt.expr_node.idnt_node import IdntNode
from parser_expr_stmt.expr_node.func_exec_node import FuncExecNode


class Statements(Enum):
    begin = "begin"
    end = "end"
    var = "var"

    cycle_while = "while"
    cycle_do = "do"
    cycle_repeat = "repeat"
    cycle_until = "until"
    cycle_for = "for"
    cycle_to = "to"
    cycle_downto = "downto"

    cond_if = "if"
    cond_then = "then"
    cond_else = "else"
    semicolon = ";"
    colon = ":"
    comma = ","
    assignment = ":="

    function = "function"
    procedure = "procedure"
    l_bracket = "("
    r_bracket = ")"
    func_return = "return"

    l_square_bracket = "["
    r_square_bracket = "]"
    two_dots = ".."
    of = "of"

    stmt_data_types = {"integer", "real", "string"}

    read = "read"
    readln = "readln"
    write = "write"
    writeln = "writeln"


class ParserStmt:
    def __init__(self, lexer):
        self.lexer = lexer

    def requireValue(self, stmt):
        token = self.lexer.getCurrentLexem()
        for s in stmt:
            there_is = self.optional(s)
            if there_is:
                break
        if not there_is:
            raise CompilerException(f"{token.getCoordinates()}        '{stmt[0].value}' was expected")

    def requireType(self, stmt, next=True):
        token = self.lexer.getCurrentLexem()
        if token.getType() != stmt.value:
            raise CompilerException(f"{token.getCoordinates()}        {stmt.value} was expected")
        if next:
            self.lexer.getNextLexem()

    def optional(self, stmt):
        token = self.lexer.getCurrentLexem()
        if token.getValue() != stmt.value:
            return False
        self.lexer.getNextLexem()
        return True

    def parseBlock(self):
        self.requireValue([Statements.begin])
        body = []
        while self.lexer.getCurrentLexem().getValue() != Statements.end.value:
            body.append(self.parse())
        self.requireValue([Statements.end])
        self.requireValue([Statements.semicolon])
        return BlockStmtNode(body)

    def parseVar(self, separator=False):
        vars = dict()
        if not separator:
            self.requireValue([Statements.var])
        identifier = self.lexer.getCurrentLexem()
        self.requireType(TokenList.identifier, next=False)
        while identifier.getType() == TokenList.identifier.value:
            self.lexer.getNextLexem()
            self.requireValue([Statements.colon])
            data_type = self.lexer.getCurrentLexem()
            if data_type.getValue() == "array":
                self.lexer.getNextLexem()
                self.requireValue([Statements.l_square_bracket])
                range = []
                range.append(self.lexer.getCurrentLexem())
                self.requireType(TokenList.integer)
                self.requireValue([Statements.two_dots])
                range.append(self.lexer.getCurrentLexem())
                self.requireType(TokenList.integer)
                self.requireValue([Statements.r_square_bracket])
                self.requireValue([Statements.of])
                data_type_array = self.lexer.getCurrentLexem()
                if data_type_array.getValue() not in Statements.stmt_data_types.value:
                    raise CompilerException(f"{data_type_array.getCoordinates()}        Unexpected {data_type_array.getValue()}")
                data_type = ArrStmtNode(range, data_type_array)
            elif data_type.getValue() not in Statements.stmt_data_types.value:
                raise CompilerException(f"{data_type.getCoordinates()}        Unexpected {data_type.getValue()}")
            self.lexer.getNextLexem()
            if separator:
                if not self.optional(Statements.comma):
                    vars[identifier] = data_type
                    break
            else:
                self.requireValue([Statements.semicolon])
            vars[identifier] = data_type
            identifier = self.lexer.getCurrentLexem()
            if separator:
                self.optional(Statements.var)
        return VarStmtNode(vars, "params" if separator else "var")

    def parseAssign(self, separator=True):
        coords = self.lexer.getCurrentLexem().getCoordinates()
        identifier = ParserExpr(self.lexer).parseExpr()
        if not isinstance(identifier, IdntNode) and not isinstance(identifier, FuncExecNode):
            raise CompilerException(f"{coords}        Identifier was expected")
        token = self.lexer.getCurrentLexem()
        if self.optional(Statements.assignment):
            try:
                value = self.lexer.getCurrentLexem()
                self.requireType(TokenList.string)
                value = StrNode(value)
            except CompilerException:
                value = ParserExpr(self.lexer).parseExpr()
            if separator:
                self.requireValue([Statements.semicolon])
            return AssignStmtNode(identifier, value)
        else:
            if isinstance(identifier, FuncExecNode):
                self.requireValue([Statements.semicolon])
                return AssignStmtNode(identifier, NullStmtNode())
            raise CompilerException(f"{token.getCoordinates()}        ':=' was expected")

    def parseWhile(self):
        self.requireValue([Statements.cycle_while])
        cond = ParserExpr(self.lexer).parseExpr()
        self.requireValue([Statements.cycle_do])
        body = self.parse()
        return WhileStmtNode(cond, body)

    def parseRepeat(self):
        self.requireValue([Statements.cycle_repeat])
        body = []
        while self.lexer.getCurrentLexem().getValue() != Statements.cycle_until.value:
            body.append(self.parse())
        self.requireValue([Statements.cycle_until])
        cond = ParserExpr(self.lexer).parseExpr()
        self.requireValue([Statements.semicolon])
        return UntilStmtNode(cond, body)

    def parseFor(self):
        self.requireValue([Statements.cycle_for])
        start = self.parseAssign(separator=False)
        step = self.lexer.getCurrentLexem()
        self.requireValue([Statements.cycle_to, Statements.cycle_downto])
        end = ParserExpr(self.lexer).parseExpr()
        self.requireValue([Statements.cycle_do])
        body = self.parse()
        return ForStmtNode(start, end, step, body)

    def parseIf(self):
        self.requireValue([Statements.cond_if])
        cond = ParserExpr(self.lexer).parseExpr()
        self.requireValue([Statements.cond_then])
        body = self.parse()
        body_else = self.parse() if self.optional(Statements.cond_else) else NullStmtNode()
        return IfStmtNode(cond, body, body_else)

    def parseFunction(self):
        func_type = self.lexer.getCurrentLexem()
        self.requireValue([Statements.function, Statements.procedure])
        name = self.lexer.getCurrentLexem()
        self.requireType(TokenList.identifier)
        self.requireValue([Statements.l_bracket])
        try:
            params = self.parseVar(1)
        except CompilerException:
            params = NullStmtNode()
        self.requireValue([Statements.r_bracket])
        if func_type.getValue() == Statements.function.value:
            self.requireValue([Statements.colon])
            return_type = self.lexer.getCurrentLexem()
            if return_type.getValue() not in Statements.stmt_data_types.value:
                raise CompilerException("Data type was expected")
            self.lexer.getNextLexem()
        else:
            return_type = NullStmtNode()
        self.requireValue([Statements.semicolon])
        try:
            var = self.parseVar()
        except CompilerException:
            var = NullStmtNode()
        body = self.parseBlock()
        return FuncStmtNode(func_type, name, params, return_type, var, body)


    def parseRead(self):
        type_read = self.lexer.getCurrentLexem()
        self.requireValue([Statements.read, Statements.readln])
        self.requireValue([Statements.l_bracket])
        identifier = self.lexer.getCurrentLexem()
        try:
            self.requireType(TokenList.identifier)
        finally:
            self.requireValue([Statements.r_bracket])
        self.requireValue([Statements.semicolon])
        return ReadStmtNode(type_read, identifier)

    def parseWrite(self):
        type_read = self.lexer.getCurrentLexem()
        self.requireValue([Statements.write, Statements.writeln])
        self.requireValue([Statements.l_bracket])
        value = ParserExpr(self.lexer).parseExpr()
        self.requireValue([Statements.r_bracket])
        self.requireValue([Statements.semicolon])
        return WriteStmtNode(type_read, value)


    def parse(self):
        token = self.lexer.getCurrentLexem()
        if token.getValue() == Statements.begin.value:
            return self.parseBlock()
        if token.getValue() in {Statements.function.value, Statements.procedure.value}:
            return self.parseFunction()
        if token.getValue() == Statements.cycle_while.value:
            return self.parseWhile()
        if token.getValue() == Statements.cycle_repeat.value:
            return self.parseRepeat()
        if token.getValue() == Statements.cycle_for.value:
            return self.parseFor()
        if token.getValue() == Statements.cond_if.value:
            return self.parseIf()
        if token.getType() == TokenList.identifier.value:
            return self.parseAssign()
        if token.getValue() == Statements.var.value:
            return self.parseVar()
        if token.getValue() in {Statements.read.value, Statements.readln.value}:
            return self.parseRead()
        if token.getValue() in {Statements.write.value, Statements.writeln.value}:
            return self.parseWrite()
        raise CompilerException(f"{token.getCoordinates()}        Unexpected {token.getValue()}")