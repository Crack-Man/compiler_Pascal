from parser_expr_stmt.stmt_node.stmt_node import StmtNode
from parser_expr_stmt.node import Node

class AssignStmtNode(StmtNode):
    def __init__(self, identifier, value):
        self.identifier = identifier
        self.value = value

    def print(self, priority=1):
        tab = super().getTab()
        value = self.value.print(priority=priority+1)
        return f"{self.identifier.getValue()} :=\n{tab*priority}{value}"

    def getValue(self):
        pass